from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.schemas.atlas import AtlasStagingManifest, AtlasStagingResponse, DatasetStagingPlan


class DatasetStagingService:
    """
    Builds the execution-time staging plan for Atlas-governed Pennsieve datasets.
    The staging plan is consumed by the HPC/Slurm layer before pipeline execution.
    """

    def __init__(self, staging_root: Optional[str] = None) -> None:
        self.staging_root = Path(staging_root or get_settings().dataset_staging_root)

    def build_staging_plan(
        self,
        request_id: str,
        atlas_dataset_id: str,
        staging: AtlasStagingResponse,
        manifest: AtlasStagingManifest,
    ) -> DatasetStagingPlan:
        destination_root = self.staging_root / request_id / atlas_dataset_id
        staged_dataset_path = destination_root / "dataset"

        env = {
            "ATLAS_STAGING_ID": staging.atlas_staging_id,
            "ATLAS_DATASET_ID": atlas_dataset_id,
            "ATLAS_MANIFEST_URL": staging.manifest_url or "",
            "ATLAS_DATASET_SOURCE": staging.source,
            "VERITAS_STAGE_ROOT": str(destination_root),
            "VERITAS_STAGED_DATASET_PATH": str(staged_dataset_path),
        }
        if staging.token:
            env["ATLAS_STAGING_TOKEN"] = staging.token

        stage_script = self._build_stage_script(
            destination_root=destination_root,
            staged_dataset_path=staged_dataset_path,
            manifest_url=staging.manifest_url,
        )

        return DatasetStagingPlan(
            atlas_dataset_id=atlas_dataset_id,
            atlas_staging_id=staging.atlas_staging_id,
            request_id=request_id,
            destination_root=str(destination_root),
            manifest_url=staging.manifest_url,
            env=env,
            stage_script=stage_script,
            staged_dataset_path=str(staged_dataset_path),
        )

    def _build_stage_script(self, destination_root: Path, staged_dataset_path: Path, manifest_url: Optional[str]) -> str:
        manifest_line = f'echo "Using manifest: {manifest_url}"' if manifest_url else 'echo "No manifest URL provided"'
        return f"""#!/usr/bin/env bash
set -euo pipefail

mkdir -p "{destination_root}"
mkdir -p "{staged_dataset_path}"

{manifest_line}
echo "Preparing job-specific dataset staging root: {destination_root}"

# Atlas-issued token is expected in $ATLAS_STAGING_TOKEN
if [ -z "${{ATLAS_STAGING_TOKEN:-}}" ]; then
  echo "Missing ATLAS_STAGING_TOKEN" >&2
  exit 1
fi

# Pennsieve/Atlas fetch implementation placeholder:
# Replace this block with curl/pennsieve-agent/s3 sync as appropriate.
echo "Staging approved dataset into {staged_dataset_path}"
cat > "{destination_root}/stage_manifest.env" <<'EOF'
ATLAS_DATASET_ID=${{ATLAS_DATASET_ID:-}}
ATLAS_STAGING_ID=${{ATLAS_STAGING_ID:-}}
ATLAS_MANIFEST_URL=${{ATLAS_MANIFEST_URL:-}}
VERITAS_STAGED_DATASET_PATH=${{VERITAS_STAGED_DATASET_PATH:-}}
EOF

touch "{staged_dataset_path}/.staged_by_veritas"
echo "Dataset staged successfully"
"""

    def ensure_local_dirs(self, plan: DatasetStagingPlan) -> None:
        Path(plan.destination_root).mkdir(parents=True, exist_ok=True)
        Path(plan.staged_dataset_path).mkdir(parents=True, exist_ok=True)
