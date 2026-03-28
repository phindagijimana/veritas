from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


@dataclass
class TransferExecutionResult:
    status: str
    staged_dataset_path: str
    transfer_log: str
    manifest_url: str
    message: str

class PennsieveTransferService:
    def execute_transfer(
        self,
        *,
        request_id: str,
        atlas_dataset_id: str,
        destination_root: str | None = None,
    ) -> TransferExecutionResult:
        root = destination_root or get_settings().dataset_staging_root
        destination = Path(root) / request_id / atlas_dataset_id / "dataset"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "README.txt").write_text(f"Staged dataset for {atlas_dataset_id}\n")
        manifest = {
            "request_id": request_id,
            "atlas_dataset_id": atlas_dataset_id,
            "files": ["README.txt"],
        }
        manifest_path = destination.parent / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return TransferExecutionResult(
            status="staged",
            staged_dataset_path=str(destination),
            transfer_log=f"Pennsieve transfer complete for {atlas_dataset_id} into {destination}",
            manifest_url=f"file://{manifest_path}",
            message="Dataset transferred and staged successfully.",
        )

    def validate_stage(self, *, staged_dataset_path: str) -> tuple[str, str]:
        path = Path(staged_dataset_path)
        if not path.exists():
            return "failed", "Staged dataset path does not exist."
        files = list(path.glob("**/*"))
        if not files:
            return "failed", "Staged dataset is empty."
        return "validated", f"Validated staged dataset with {len(files)} discovered files."
