from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from app.core.config import get_settings


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "item"


class ArtifactStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = Path(self.settings.artifact_root_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def job_layout(self, request_code: str, job_name: str) -> dict[str, str]:
        run_dir = self.root / request_code / _slug(job_name)
        run_dir.mkdir(parents=True, exist_ok=True)
        return {
            "local_run_dir": str(run_dir),
            "runtime_manifest_path": str(run_dir / "run_manifest.json"),
            "metrics_path": str(run_dir / "metrics.json"),
            "results_csv_path": str(run_dir / "results.csv"),
            "report_path": str(run_dir / "report.pdf"),
            "report_json_path": str(run_dir / "report.json"),
            "report_html_path": str(run_dir / "report.html"),
        }

    def write_json(self, path: str, payload: dict[str, Any]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2))

    def write_text(self, path: str, text: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def write_bytes(self, path: str, payload: bytes) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def write_csv(self, path: str, header: list[str], rows: list[list[Any]]) -> None:
        lines = [",".join(header)] + [",".join(map(str, row)) for row in rows]
        self.write_text(path, "\n".join(lines) + "\n")

    def public_url(self, path: str | None) -> str | None:
        if not path:
            return None
        try:
            rel = Path(path).resolve().relative_to(self.root)
        except Exception:
            rel = Path(path).name
        rel_s = str(rel).replace("\\", "/")
        return f"{self.settings.public_artifact_base_url}/{rel_s}"
