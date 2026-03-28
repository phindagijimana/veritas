from __future__ import annotations

import base64

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
    runtime_cmd = "apptainer run docker://x"
    script = SlurmService.build_execution_script(
        config=config,
        runtime_command=runtime_cmd,
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
    assert "base64" in script
    b64 = base64.b64encode(runtime_cmd.encode()).decode()
    assert b64 in script
    assert base64.b64decode(b64).decode() == runtime_cmd
