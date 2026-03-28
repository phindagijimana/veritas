from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.artifact_storage import ArtifactStorageService
from app.services.container_runtime import ContainerRuntimeService


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

    def build_plan(self, request_code: str, job_name: str, pipeline: str, dataset: str) -> RuntimePlan:
        layout = self.storage.job_layout(request_code=request_code, job_name=job_name)
        runtime_command = self.runtime.build_command(image=pipeline, dataset_path=f"/datasets/{dataset}", output_dir=layout["local_run_dir"])
        manifest = {
            "request_code": request_code,
            "job_name": job_name,
            "pipeline": pipeline,
            "dataset": dataset,
            "runtime_command": runtime_command,
            "artifacts": {
                "metrics": layout["metrics_path"],
                "results_csv": layout["results_csv_path"],
                "report": layout["report_path"],
            },
        }
        self.storage.write_json(layout["runtime_manifest_path"], manifest)
        return RuntimePlan(runtime_command=runtime_command, manifest=manifest, **layout)
