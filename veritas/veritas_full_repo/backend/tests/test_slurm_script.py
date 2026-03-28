from __future__ import annotations

from app.schemas.hpc import SlurmResourcesConfig
from app.services.slurm_service import SlurmService


def test_execution_script_includes_runtime_engine_and_prologue():
    config = SlurmResourcesConfig(
        job_name="j1",
        partition="gpu",
        gpus=1,
        cpus=4,
        memory_gb=32,
        wall_time="01:00:00",
        constraint="",
        sbatch_overrides="",
    )
    script = SlurmService.build_execution_script(
        config=config,
        runtime_command="apptainer run docker://x",
        runtime_manifest_path="/tmp/m.json",
        remote_workdir="/work",
        stdout_path="/work/o.log",
        stderr_path="/work/e.log",
        runtime_engine="apptainer",
        prologue_sh="module load apptainer\nexport FOO=1",
    )
    assert "# Veritas runtime_engine=apptainer" in script
    assert "module load apptainer" in script
    assert "export FOO=1" in script
    assert "apptainer run docker://x" in script
