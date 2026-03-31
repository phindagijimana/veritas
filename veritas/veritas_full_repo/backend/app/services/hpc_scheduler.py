from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.models.hpc_connection import HPCConnection
from app.schemas.hpc import SlurmJobSubmitRequest, SlurmResourcesConfig
from app.services.hpc_adapter import get_hpc_adapter
from app.services.pipeline_runner import PipelineRunnerService
from app.services.slurm_service import SlurmService


@dataclass
class SchedulerJobBundle:
    scheduler_job_id: str
    status: str
    sbatch_script: str
    remote_workdir: str
    stdout_path: str
    stderr_path: str
    launch_command: str
    runtime_manifest_path: str
    metrics_path: str
    results_csv_path: str
    report_path: str
    runtime_engine: str
    # Inner runtime (e.g. MELD bash); set on preview for inspection.
    pipeline_runtime_script: str | None = None


class HPCSchedulerService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.adapter = get_hpc_adapter()
        self.runner = PipelineRunnerService()

    def submit(
        self,
        connection: HPCConnection | None,
        request_code: str,
        payload: SlurmJobSubmitRequest,
        *,
        pipeline_yaml: str | None = None,
    ) -> SchedulerJobBundle:
        runtime = SlurmService.build_runtime_layout(job_name=payload.job_name, request_code=request_code, remote_root=self.settings.slurm_remote_workdir)
        plan = self.runner.build_plan(
            request_code=request_code,
            job_name=payload.job_name,
            pipeline=payload.pipeline,
            dataset=payload.dataset,
            job_payload=payload,
            pipeline_yaml=pipeline_yaml,
        )
        config = SlurmResourcesConfig(
            job_name=payload.job_name,
            partition=payload.partition,
            gpus=payload.resources.gpu,
            cpus=payload.resources.cpu,
            memory_gb=payload.resources.memory_gb,
            wall_time=payload.resources.wall_time,
            constraint=payload.resources.constraint,
            sbatch_overrides=payload.resources.sbatch_overrides,
        )
        script = SlurmService.build_execution_script(
            config=config,
            runtime_command=plan.runtime_command,
            runtime_manifest_path=plan.runtime_manifest_path,
            remote_workdir=runtime["remote_workdir"],
            stdout_path=runtime["stdout_path"],
            stderr_path=runtime["stderr_path"],
            runtime_engine=self.settings.runtime_engine,
            prologue_sh=self.settings.hpc_job_prologue_sh,
        )
        result = self.adapter.submit(connection, config=config, script=script, remote_workdir=runtime["remote_workdir"], script_name=runtime["script_name"])
        return SchedulerJobBundle(
            scheduler_job_id=result.scheduler_job_id,
            status=result.status,
            sbatch_script=result.script,
            remote_workdir=runtime["remote_workdir"],
            stdout_path=runtime["stdout_path"],
            stderr_path=runtime["stderr_path"],
            launch_command=result.launch_command,
            runtime_manifest_path=plan.runtime_manifest_path,
            metrics_path=plan.metrics_path,
            results_csv_path=plan.results_csv_path,
            report_path=plan.report_path,
            runtime_engine=self.settings.runtime_engine,
            pipeline_runtime_script=plan.runtime_command,
        )

    def preview(
        self,
        request_code: str,
        payload: SlurmJobSubmitRequest,
        *,
        pipeline_yaml: str | None = None,
    ) -> SchedulerJobBundle:
        """
        Build the same Slurm + runtime scripts as submit() without SSH/sbatch or DB writes.
        Use to validate MELD/Apptainer commands before running on HPC.
        """
        runtime = SlurmService.build_runtime_layout(job_name=payload.job_name, request_code=request_code, remote_root=self.settings.slurm_remote_workdir)
        plan = self.runner.build_plan(
            request_code=request_code,
            job_name=payload.job_name,
            pipeline=payload.pipeline,
            dataset=payload.dataset,
            job_payload=payload,
            pipeline_yaml=pipeline_yaml,
        )
        config = SlurmResourcesConfig(
            job_name=payload.job_name,
            partition=payload.partition,
            gpus=payload.resources.gpu,
            cpus=payload.resources.cpu,
            memory_gb=payload.resources.memory_gb,
            wall_time=payload.resources.wall_time,
            constraint=payload.resources.constraint,
            sbatch_overrides=payload.resources.sbatch_overrides,
        )
        script = SlurmService.build_execution_script(
            config=config,
            runtime_command=plan.runtime_command,
            runtime_manifest_path=plan.runtime_manifest_path,
            remote_workdir=runtime["remote_workdir"],
            stdout_path=runtime["stdout_path"],
            stderr_path=runtime["stderr_path"],
            runtime_engine=self.settings.runtime_engine,
            prologue_sh=self.settings.hpc_job_prologue_sh,
        )
        return SchedulerJobBundle(
            scheduler_job_id="",
            status="preview",
            sbatch_script=script,
            remote_workdir=runtime["remote_workdir"],
            stdout_path=runtime["stdout_path"],
            stderr_path=runtime["stderr_path"],
            launch_command=f"sbatch {runtime['remote_workdir']}/{runtime['script_name']}  # not executed in preview",
            runtime_manifest_path=plan.runtime_manifest_path,
            metrics_path=plan.metrics_path,
            results_csv_path=plan.results_csv_path,
            report_path=plan.report_path,
            runtime_engine=self.settings.runtime_engine,
            pipeline_runtime_script=plan.runtime_command,
        )
