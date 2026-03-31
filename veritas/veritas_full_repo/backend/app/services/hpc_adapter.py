
from __future__ import annotations

from dataclasses import dataclass
import shlex
import textwrap

from app.core.config import get_settings
from app.models.hpc_connection import HPCConnection
from app.schemas.hpc import SlurmResourcesConfig
from app.services.slurm_service import SlurmService
from app.services.ssh_service import SSHService


@dataclass
class SubmitResult:
    scheduler_job_id: str
    status: str
    script: str
    launch_command: str


@dataclass
class QueueSummary:
    queue_count: int
    running_count: int
    gpu_free: int


def remote_path_for_shell(path: str) -> str:
    """
    Map ~/... to $HOME/... for remote shell commands.
    Single-quoted paths from shlex.quote do not expand ~; this fixes mkdir/cd on the cluster.
    """
    p = path.strip()
    if p.startswith("~/"):
        return "$HOME/" + p[2:]
    return p


def shell_double_quote(s: str) -> str:
    """Double-quote for remote bash so $HOME and spaces are handled."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


class MockHPCAdapter:
    def validate_connection(self, connection: HPCConnection | None) -> bool:
        return True

    def submit(
        self,
        connection: HPCConnection | None,
        config: SlurmResourcesConfig,
        script: str,
        remote_workdir: str,
        script_name: str,
    ) -> SubmitResult:
        result = SlurmService.mock_submit(config, script=script, remote_workdir=remote_workdir, script_name=script_name)
        return SubmitResult(**result)

    def summary(self, connection: HPCConnection | None) -> QueueSummary:
        return QueueSummary(queue_count=4, running_count=3, gpu_free=8)

    def status(self, connection: HPCConnection | None, scheduler_job_id: str) -> str:
        if scheduler_job_id.endswith("001"):
            return "RUNNING"
        return "COMPLETED"

    def cancel(self, connection: HPCConnection | None, scheduler_job_id: str) -> bool:
        return True


class SlurmHPCAdapter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.ssh = SSHService()

    def validate_connection(self, connection: HPCConnection | None) -> bool:
        if connection is None:
            return False
        return self.ssh.ping(connection)

    def submit(
        self,
        connection: HPCConnection | None,
        config: SlurmResourcesConfig,
        script: str,
        remote_workdir: str,
        script_name: str,
    ) -> SubmitResult:
        if connection is None:
            raise ValueError("No active HPC connection configured")
        rw = remote_path_for_shell(remote_workdir)
        script_path = f"{rw}/{script_name}"
        q_dir = shell_double_quote(rw)
        q_script = shell_double_quote(script_path)
        mkdir_cmd = f"mkdir -p {q_dir}"
        heredoc = textwrap.dedent(f"""
        cat > {q_script} <<'EOF'
        {script}
        EOF
        chmod +x {q_script}
        """).strip()
        submit_cmd = f"cd {q_dir} && sbatch {shlex.quote(script_name)}"
        self.ssh.run(connection, mkdir_cmd)
        self.ssh.run(connection, heredoc)
        result = self.ssh.run(connection, submit_cmd)
        scheduler_job_id = self._parse_job_id(result.stdout)
        return SubmitResult(
            scheduler_job_id=scheduler_job_id,
            status="queued" if scheduler_job_id else "failed",
            script=script,
            launch_command=submit_cmd,
        )

    def summary(self, connection: HPCConnection | None) -> QueueSummary:
        if not connection:
            return QueueSummary(queue_count=0, running_count=0, gpu_free=0)
        queue = self.ssh.run(connection, "squeue -h -t PENDING | wc -l")
        running = self.ssh.run(connection, "squeue -h -t RUNNING | wc -l")
        gpu_free = self.ssh.run(connection, "nvidia-smi --query-gpu=index --format=csv,noheader 2>/dev/null | wc -l")
        return QueueSummary(
            queue_count=int(queue.stdout or 0),
            running_count=int(running.stdout or 0),
            gpu_free=max(int(gpu_free.stdout or 0), 0),
        )

    def status(self, connection: HPCConnection | None, scheduler_job_id: str) -> str:
        if not connection:
            return "UNKNOWN"
        poll_command = self.settings.slurm_poll_command.format(job_id=shlex.quote(scheduler_job_id))
        result = self.ssh.run(connection, poll_command)
        state = (result.stdout.strip() or "COMPLETED").splitlines()[0].strip().upper()
        return state or "COMPLETED"

    def cancel(self, connection: HPCConnection | None, scheduler_job_id: str) -> bool:
        if not connection:
            return False
        command = self.settings.slurm_cancel_command.format(job_id=shlex.quote(scheduler_job_id))
        result = self.ssh.run(connection, command)
        return result.exit_code == 0

    @staticmethod
    def _parse_job_id(output: str) -> str:
        tokens = output.strip().split()
        return tokens[-1] if tokens and tokens[-1].isdigit() else ""


def get_hpc_adapter():
    settings = get_settings()
    return SlurmHPCAdapter() if settings.hpc_mode == "slurm" else MockHPCAdapter()
