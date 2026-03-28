
from __future__ import annotations

import csv
import json
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.dataset import Dataset


class DatasetValidationService:
    LABEL_HINTS = {"labels", "masks", "annotations", "derivatives"}
    METADATA_FILENAMES = ("dataset_description.json", "metadata.json", "dataset.yaml")

    @staticmethod
    def _add_check(checks: list[dict], name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    @staticmethod
    def _resolve_path(raw: str | None) -> Path | None:
        if not raw:
            return None
        p = Path(raw).expanduser()
        if p.is_absolute():
            return p
        base = Path(get_settings().dataset_root_dir).expanduser()
        return p if p.exists() else base / p

    @staticmethod
    def _subject_dirs(root: Path) -> list[Path]:
        if not root.exists() or not root.is_dir():
            return []
        sub_dirs = [p for p in root.iterdir() if p.is_dir() and p.name.lower().startswith('sub-')]
        if sub_dirs:
            return sub_dirs
        subjects_root = root / 'subjects'
        if subjects_root.exists() and subjects_root.is_dir():
            return [p for p in subjects_root.iterdir() if p.is_dir()]
        return [p for p in root.iterdir() if p.is_dir() and p.name.lower().startswith(('subject', 'patient'))]

    @staticmethod
    def _find_metadata_file(root: Path) -> Path | None:
        for filename in DatasetValidationService.METADATA_FILENAMES:
            candidate = root / filename
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _find_label_dirs(root: Path) -> list[Path]:
        matches: list[Path] = []
        for child in root.iterdir() if root.exists() else []:
            if child.is_dir() and child.name.lower() in DatasetValidationService.LABEL_HINTS:
                matches.append(child)
        derivatives = root / 'derivatives'
        if derivatives.exists() and derivatives.is_dir():
            matches.extend([p for p in derivatives.iterdir() if p.is_dir()])
        return matches

    @staticmethod
    def _load_manifest(manifest_path: Path) -> tuple[bool, str, int]:
        try:
            if manifest_path.suffix.lower() == '.json':
                payload = json.loads(manifest_path.read_text())
                if isinstance(payload, list):
                    return True, 'JSON manifest loaded', len(payload)
                if isinstance(payload, dict):
                    for key in ('subjects', 'items', 'data'):
                        if isinstance(payload.get(key), list):
                            return True, f'JSON manifest loaded from {key}', len(payload[key])
                    return True, 'JSON manifest loaded', 1
            if manifest_path.suffix.lower() == '.csv':
                with manifest_path.open(newline='') as handle:
                    rows = list(csv.DictReader(handle))
                return True, 'CSV manifest loaded', len(rows)
        except Exception as exc:  # pragma: no cover
            return False, f'Manifest could not be parsed: {exc}', 0
        return False, 'Unsupported manifest format', 0

    @classmethod
    def validate(cls, dataset: Dataset) -> dict:
        checks: list[dict] = []
        root = cls._resolve_path(dataset.hpc_root_path)
        manifest = cls._resolve_path(dataset.manifest_path)

        cls._add_check(checks, 'benchmark_enabled', bool(dataset.benchmark_enabled), 'Dataset is enabled for benchmarking' if dataset.benchmark_enabled else 'Dataset is not benchmark-enabled')
        cls._add_check(checks, 'active', bool(dataset.is_active), 'Dataset is active' if dataset.is_active else 'Dataset is inactive')
        cls._add_check(checks, 'disease_group', bool(dataset.disease_group), f'Disease group: {dataset.disease_group}' if dataset.disease_group else 'Disease group missing')
        cls._add_check(checks, 'modality', bool(dataset.modality), f'Modality: {dataset.modality}' if dataset.modality else 'Modality missing')
        cls._add_check(checks, 'label_schema', bool(dataset.label_schema), f'Label schema: {dataset.label_schema}' if dataset.label_schema else 'Label schema missing')
        qc_ok = dataset.qc_status.lower() in {'validated', 'curated', 'approved', 'ready'}
        cls._add_check(checks, 'qc_status', qc_ok, f'QC status: {dataset.qc_status}')

        root_exists = bool(root and root.exists() and root.is_dir())
        cls._add_check(checks, 'hpc_root_path', root_exists, f'Found root path: {root}' if root_exists else f'Missing or unavailable root path: {dataset.hpc_root_path}')

        manifest_exists = bool(manifest and manifest.exists() and manifest.is_file())
        cls._add_check(checks, 'manifest_path', manifest_exists, f'Found manifest: {manifest}' if manifest_exists else f'Missing or unavailable manifest: {dataset.manifest_path}')

        subject_dirs = cls._subject_dirs(root) if root_exists else []
        cls._add_check(checks, 'subject_directories', len(subject_dirs) > 0, f'Discovered {len(subject_dirs)} subject directories')

        metadata_file = cls._find_metadata_file(root) if root_exists else None
        cls._add_check(checks, 'metadata_file', metadata_file is not None, f'Metadata file found: {metadata_file.name}' if metadata_file else 'Metadata file missing')
        metadata_ok = False
        metadata_detail = 'Metadata file not available'
        if metadata_file:
            try:
                _ = metadata_file.read_text()
                metadata_ok = True
                metadata_detail = f'Metadata file readable: {metadata_file.name}'
            except Exception as exc:  # pragma: no cover
                metadata_detail = f'Metadata file unreadable: {exc}'
        cls._add_check(checks, 'metadata_readable', metadata_ok, metadata_detail)

        label_dirs = cls._find_label_dirs(root) if root_exists else []
        label_ok = len(label_dirs) > 0 if dataset.label_schema else True
        cls._add_check(checks, 'label_artifacts', label_ok, f'Found {len(label_dirs)} label-related directories' if label_ok else 'No label-related directory found')

        subject_count_found = len(subject_dirs)
        if dataset.subject_count:
            subject_match = subject_count_found == dataset.subject_count
            detail = f'Registry subject_count={dataset.subject_count}; discovered={subject_count_found}'
        else:
            subject_match = subject_count_found > 0
            detail = f'Discovered {subject_count_found} subject directories'
        cls._add_check(checks, 'subject_count_alignment', subject_match, detail)

        manifest_ok = False
        manifest_items = 0
        manifest_detail = 'Manifest unavailable'
        if manifest_exists:
            manifest_ok, manifest_detail, manifest_items = cls._load_manifest(manifest)
        cls._add_check(checks, 'manifest_parse', manifest_ok, manifest_detail)
        if manifest_ok and subject_count_found:
            cls._add_check(checks, 'manifest_subject_alignment', manifest_items == subject_count_found, f'Manifest rows={manifest_items}; discovered subjects={subject_count_found}')

        bids_ok = bool(root_exists and any((root / item).exists() for item in ('dataset_description.json', 'participants.tsv', 'sub-001')))
        cls._add_check(checks, 'dataset_structure_hint', bids_ok or subject_count_found > 0, 'BIDS-like structure or subject layout detected' if (bids_ok or subject_count_found > 0) else 'Dataset structure does not look like BIDS or subject-organized data')

        blocking_failures = {'benchmark_enabled', 'active', 'disease_group', 'modality', 'hpc_root_path', 'subject_directories', 'metadata_file', 'metadata_readable', 'subject_count_alignment', 'manifest_parse'}
        valid = all(item['ok'] for item in checks if item['name'] in blocking_failures)
        return {
            'dataset_id': dataset.id,
            'dataset_name': dataset.name,
            'dataset_code': dataset.code,
            'valid': valid,
            'summary': 'Dataset passed deep validation' if valid else 'Dataset deep validation requires attention',
            'checks': checks,
        }

    @staticmethod
    def validate_by_ref(db: Session, dataset_ref: str) -> dict | None:
        query = db.query(Dataset)
        dataset = query.filter(Dataset.id == int(dataset_ref)).first() if dataset_ref.isdigit() else query.filter((Dataset.code == dataset_ref) | (Dataset.name == dataset_ref)).first()
        if not dataset:
            return None
        return DatasetValidationService.validate(dataset)
