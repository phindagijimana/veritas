from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import paramiko

from app.core.config import get_settings
from app.models.hpc_connection import HPCConnection


@dataclass
class SSHCommandResult:
    stdout: str
    stderr: str
    exit_code: int


class SSHService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_client(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        if self.settings.ssh_strict_host_key_checking:
            client.load_system_host_keys()
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    def _connect_client(self, client: paramiko.SSHClient, connection: HPCConnection) -> None:
        kwargs: dict = {
            "hostname": connection.hostname,
            "port": connection.port,
            "username": connection.username,
            "timeout": self.settings.ssh_connect_timeout_seconds,
        }
        key_ref = (connection.ssh_key_reference or "").strip()
        if key_ref:
            key_path = Path(key_ref).expanduser()
            if not key_path.is_file():
                raise ValueError(f"SSH key file not found: {key_path}")
            kwargs["key_filename"] = str(key_path)
        else:
            kwargs["allow_agent"] = True
            kwargs["look_for_keys"] = True
        client.connect(**kwargs)

    def validate_connection(self, connection: HPCConnection) -> None:
        """
        Verify SSH login and a trivial remote command.
        Raises ValueError with a user-facing message on failure.
        """
        if not (connection.hostname or "").strip():
            raise ValueError("hostname is required")
        if not (connection.username or "").strip():
            raise ValueError("username is required")
        client = self._build_client()
        try:
            self._connect_client(client, connection)
            result = self.run(connection, "echo veritas_hpc_ok", client=client)
            if result.exit_code != 0:
                raise ValueError(
                    f"SSH session failed (exit {result.exit_code}): {result.stderr or result.stdout or 'no output'}".strip()
                )
            if "veritas_hpc_ok" not in result.stdout:
                raise ValueError("Unexpected SSH shell output (expected veritas_hpc_ok)")
        except ValueError:
            raise
        except paramiko.AuthenticationException as e:
            raise ValueError(f"SSH authentication failed: {e}") from e
        except paramiko.SSHException as e:
            raise ValueError(f"SSH error: {e}") from e
        except OSError as e:
            raise ValueError(f"SSH connection error: {e}") from e
        finally:
            client.close()

    def ping(self, connection: HPCConnection) -> bool:
        try:
            self.validate_connection(connection)
            return True
        except ValueError:
            return False

    def run(self, connection: HPCConnection, command: str, client: paramiko.SSHClient | None = None) -> SSHCommandResult:
        owns_client = client is None
        ssh = client or self._build_client()
        try:
            if owns_client:
                self._connect_client(ssh, connection)
            _stdin, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            return SSHCommandResult(
                stdout=stdout.read().decode().strip(),
                stderr=stderr.read().decode().strip(),
                exit_code=exit_code,
            )
        finally:
            if owns_client:
                ssh.close()
