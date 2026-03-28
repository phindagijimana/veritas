from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "item"


class ArtifactStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if self.settings.storage_backend == "s3":
            if not self.settings.s3_configured:
                raise ValueError(
                    "STORAGE_BACKEND=s3 requires S3_ENDPOINT_URL, S3_ACCESS_KEY, and S3_SECRET_KEY "
                    "(non-empty)."
                )
            import boto3

            self._s3 = boto3.client(
                "s3",
                endpoint_url=(self.settings.s3_endpoint_url or None),
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                region_name=self.settings.s3_region or "us-east-1",
            )
            self._bucket = self.settings.s3_bucket
        else:
            self._s3 = None
            self._bucket = ""
            self.root = Path(self.settings.artifact_root_dir).expanduser().resolve()
            self.root.mkdir(parents=True, exist_ok=True)

    def job_layout(self, request_code: str, job_name: str) -> dict[str, str]:
        if self._s3:
            base = f"artifacts/{request_code}/{_slug(job_name)}"
            return {
                "local_run_dir": base,
                "runtime_manifest_path": f"{base}/run_manifest.json",
                "metrics_path": f"{base}/metrics.json",
                "results_csv_path": f"{base}/results.csv",
                "report_path": f"{base}/report.pdf",
                "report_json_path": f"{base}/report.json",
                "report_html_path": f"{base}/report.html",
            }
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

    def _s3_key(self, path: str) -> str:
        return path.lstrip("/")

    def write_json(self, path: str, payload: dict[str, Any]) -> None:
        if self._s3:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self._s3.put_object(Bucket=self._bucket, Key=self._s3_key(path), Body=body)
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2))

    def write_text(self, path: str, text: str) -> None:
        if self._s3:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=self._s3_key(path),
                Body=text.encode("utf-8"),
            )
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def write_bytes(self, path: str, payload: bytes) -> None:
        if self._s3:
            self._s3.put_object(Bucket=self._bucket, Key=self._s3_key(path), Body=payload)
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def write_csv(self, path: str, header: list[str], rows: list[list[Any]]) -> None:
        lines = [",".join(header)] + [",".join(map(str, row)) for row in rows]
        self.write_text(path, "\n".join(lines) + "\n")

    def public_url(self, path: str | None) -> str | None:
        if not path:
            return None
        if self._s3:
            key = self._s3_key(path)
            return self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=3600,
            )
        try:
            rel = Path(path).resolve().relative_to(self.root)
        except Exception:
            rel = Path(path).name
        rel_s = str(rel).replace("\\", "/")
        return f"{self.settings.public_artifact_base_url}/{rel_s}"
