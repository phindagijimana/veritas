from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.leaderboard_entry import LeaderboardEntry
from app.models.report import Report
from app.schemas.leaderboard import LeaderboardEntryRead
from app.services.metrics_parser import MetricsParserService
from app.services.report_service import ReportService
from app.services.request_service import RequestService


class LeaderboardService:
    PRIORITY_METRICS = ["overall_score", "auc", "dice", "accuracy", "f1_score", "precision", "recall", "sensitivity", "specificity", "jaccard_index"]
    COMPOSITE_METRICS = ["dice", "auc", "accuracy", "f1_score", "precision", "recall", "sensitivity", "specificity", "jaccard_index"]

    @staticmethod
    def _flatten_metrics(payload: dict[str, Any], prefix: str = "") -> dict[str, float]:
        flattened: dict[str, float] = {}
        for key, value in (payload or {}).items():
            flat_key = f"{prefix}{key}" if not prefix else f"{prefix}_{key}"
            if isinstance(value, (int, float)):
                flattened[flat_key.lower()] = float(value)
            elif isinstance(value, dict):
                flattened.update(LeaderboardService._flatten_metrics(value, flat_key))
        return flattened

    @classmethod
    def _report_metrics(cls, report: Report) -> dict[str, float]:
        candidates: list[dict[str, Any]] = []
        if report.metrics_summary_json:
            try:
                payload = json.loads(report.metrics_summary_json)
                if isinstance(payload, dict):
                    candidates.append(payload)
                    if isinstance(payload.get("metrics"), dict):
                        candidates.append(payload["metrics"])
            except json.JSONDecodeError:
                pass
        if report.json_path and Path(report.json_path).exists():
            try:
                payload = json.loads(Path(report.json_path).read_text())
                if isinstance(payload, dict):
                    candidates.append(payload)
                    if isinstance(payload.get("metrics"), dict):
                        candidates.append(payload["metrics"])
            except Exception:
                pass
        flattened: dict[str, float] = {}
        for candidate in candidates:
            flattened.update(cls._flatten_metrics(candidate))
        if not flattened:
            metrics_path = None
            for artifact in getattr(report, "artifacts", []) or []:
                if getattr(artifact, "artifact_type", "").lower() == "json" and artifact.storage_path:
                    metrics_path = artifact.storage_path
                    break
            fallback = MetricsParserService.parse_metrics_file(metrics_path)
            flattened.update(cls._flatten_metrics(fallback))
        if "metrics_dice" in flattened and "dice" not in flattened:
            flattened["dice"] = flattened["metrics_dice"]
        if "metrics_auc" in flattened and "auc" not in flattened:
            flattened["auc"] = flattened["metrics_auc"]
        if "metrics_accuracy" in flattened and "accuracy" not in flattened:
            flattened["accuracy"] = flattened["metrics_accuracy"]
        if "overall_score" not in flattened:
            composite = [flattened[key] for key in cls.COMPOSITE_METRICS if key in flattened]
            if composite:
                flattened["overall_score"] = round(sum(composite) / len(composite), 4)
        return flattened

    @classmethod
    def _primary_metric(cls, report: Report) -> tuple[str, float]:
        metrics = cls._report_metrics(report)
        for key in cls.PRIORITY_METRICS:
            value = metrics.get(key)
            if isinstance(value, (int, float)):
                return key, float(value)
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                return key, float(value)
        return "overall_score", 0.0

    @staticmethod
    def _group_key(entry: LeaderboardEntry) -> tuple[str, str]:
        return ((entry.biomarker_group or "General").strip() or "General", (entry.disease_group or "General").strip() or "General")

    @classmethod
    def _to_read(cls, entry: LeaderboardEntry, rank: int | None = None, overall_rank: int | None = None) -> LeaderboardEntryRead:
        return LeaderboardEntryRead(
            id=entry.id,
            rank=rank,
            overall_rank=overall_rank,
            pipeline=entry.pipeline_name,
            dataset=entry.dataset_name,
            disease_group=entry.disease_group,
            biomarker_group=entry.biomarker_group,
            score=float(entry.score or 0),
            metric_label=entry.primary_metric.replace("_", " ").title(),
            published_at=entry.published_at,
            consented=entry.consented,
        )

    @classmethod
    def list_entries(cls, db: Session, disease_group: str | None = None, biomarker_group: str | None = None) -> list[LeaderboardEntryRead]:
        stmt = select(LeaderboardEntry).where(LeaderboardEntry.consented.is_(True))
        if disease_group:
            stmt = stmt.where(LeaderboardEntry.disease_group == disease_group)
        if biomarker_group:
            stmt = stmt.where(LeaderboardEntry.biomarker_group == biomarker_group)
        rows = list(db.scalars(stmt.order_by(desc(LeaderboardEntry.score), desc(LeaderboardEntry.published_at))))
        if disease_group or biomarker_group:
            return [cls._to_read(entry, rank=i + 1, overall_rank=i + 1) for i, entry in enumerate(rows)]

        grouped: dict[tuple[str, str], list[LeaderboardEntry]] = {}
        for entry in rows:
            grouped.setdefault(cls._group_key(entry), []).append(entry)
        ordered_keys = sorted(grouped.keys(), key=lambda item: (item[1], item[0]))
        ranked: list[LeaderboardEntryRead] = []
        overall = 1
        for key in ordered_keys:
            group_rows = sorted(grouped[key], key=lambda item: (float(item.score or 0), item.published_at), reverse=True)
            for idx, entry in enumerate(group_rows, start=1):
                ranked.append(cls._to_read(entry, rank=idx, overall_rank=overall))
                overall += 1
        return ranked

    @classmethod
    def push_request(cls, db: Session, request_id: int | str, consented: bool = True) -> LeaderboardEntryRead:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        report = ReportService.publish_for_request(db, request.id)
        metric, score = cls._primary_metric(report)
        entry = db.scalar(select(LeaderboardEntry).where(LeaderboardEntry.request_id == request.id).limit(1))
        pipeline_name = request.pipeline.title or request.pipeline.name
        dataset_name = request.dataset.name
        disease_group = request.dataset.disease_group
        biomarker_group = request.dataset.code or request.dataset.collection_name
        if not entry:
            entry = LeaderboardEntry(
                request_id=request.id,
                report_id=report.id,
                pipeline_name=pipeline_name,
                dataset_name=dataset_name,
                disease_group=disease_group,
                biomarker_group=biomarker_group,
                primary_metric=metric,
                score=Decimal(str(score)),
                consented=consented,
            )
            db.add(entry)
        else:
            entry.report_id = report.id
            entry.pipeline_name = pipeline_name
            entry.dataset_name = dataset_name
            entry.disease_group = disease_group
            entry.biomarker_group = biomarker_group
            entry.primary_metric = metric
            entry.score = Decimal(str(score))
            entry.consented = consented
        db.commit()
        db.refresh(entry)
        ranked = cls.list_entries(db, disease_group=disease_group, biomarker_group=biomarker_group)
        for item in ranked:
            if item.id == entry.id:
                return item
        return cls._to_read(entry)
