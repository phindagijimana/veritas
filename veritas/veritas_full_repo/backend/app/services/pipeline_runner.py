from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.hpc import SlurmJobSubmitRequest


def _meld_subject_ids_from_payload(job_payload: SlurmJobSubmitRequest | None) -> list[str]:
    if not job_payload:
        return []
    batch = [str(x).strip() for x in (job_payload.meld_subject_ids or []) if x is not None and str(x).strip()]
    if batch:
        return batch
    if (job_payload.meld_subject_id or "").strip():
        return [job_payload.meld_subject_id.strip()]
    return []
from app.services.artifact_storage import ArtifactStorageService
from app.services.container_runtime import ContainerRuntimeService
from app.services.meld_pipeline_plugin import MeldPluginConfig, parse_meld_plugin_config


@dataclass
class RuntimePlan:
    runtime_command: str
    manifest: dict[str, Any]
    local_run_dir: str
    runtime_manifest_path: str
    metrics_path: str
    results_csv_path: str
    report_path: str
    report_json_path: str
    report_html_path: str


class PipelineRunnerService:
    def __init__(self) -> None:
        self.storage = ArtifactStorageService()
        self.runtime = ContainerRuntimeService()

    def build_plan(
        self,
        request_code: str,
        job_name: str,
        pipeline: str,
        dataset: str,
        job_payload: SlurmJobSubmitRequest | None = None,
        pipeline_yaml: str | None = None,
    ) -> RuntimePlan:
        layout = self.storage.job_layout(request_code=request_code, job_name=job_name)
        settings = get_settings()
        profile = (job_payload.runtime_profile if job_payload else "generic") or "generic"
        meld_cfg: MeldPluginConfig | None = None

        if profile.strip().lower() == "meld_graph":
            meld_ids = _meld_subject_ids_from_payload(job_payload)
            if not meld_ids:
                raise ValueError("meld_subject_id or meld_subject_ids is required when runtime_profile=meld_graph")
            meld_data_dir = str(Path(layout["local_run_dir"]) / "meld_docker_data")
            meld_cfg = parse_meld_plugin_config(pipeline_yaml)
            runtime_command = self.runtime.build_meld_graph_runtime_script(
                image=pipeline,
                meld_data_dir=meld_data_dir,
                meld_subject_ids=meld_ids,
                meld_session=job_payload.meld_session if job_payload else None,
                staged_dataset_path=job_payload.staged_dataset_path if job_payload else None,
                default_ideas_staging=settings.meld_ideas_default_staging_path,
                meld_plugin=meld_cfg,
            )
        else:
            runtime_command = self.runtime.build_command(
                image=pipeline, dataset_path=f"/datasets/{dataset}", output_dir=layout["local_run_dir"]
            )

        manifest = {
            "request_code": request_code,
            "job_name": job_name,
            "pipeline": pipeline,
            "dataset": dataset,
            "runtime_profile": profile,
            "runtime_command": runtime_command,
            "artifacts": {
                "metrics": layout["metrics_path"],
                "results_csv": layout["results_csv_path"],
                "report": layout["report_path"],
            },
        }
        if job_payload:
            mids = _meld_subject_ids_from_payload(job_payload)
            manifest["meld_subject_ids"] = mids
            manifest["meld_subject_id"] = mids[0] if mids else None
            manifest["meld_session"] = job_payload.meld_session
            manifest["staged_dataset_path"] = job_payload.staged_dataset_path
        if meld_cfg is not None:
            manifest["meld_plugin"] = {
                "freesurfer_license_file": meld_cfg.freesurfer_license_file,
                "meld_license_file": meld_cfg.meld_license_file,
                "fs_license_container": meld_cfg.fs_license_container,
                "meld_license_container": meld_cfg.meld_license_container,
                "freesurfer_image": meld_cfg.freesurfer_image,
                "meld_image": meld_cfg.meld_image,
            }
        self.storage.write_json(layout["runtime_manifest_path"], manifest)
        return RuntimePlan(runtime_command=runtime_command, manifest=manifest, **layout)
