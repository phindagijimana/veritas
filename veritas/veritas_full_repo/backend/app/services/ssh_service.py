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

    def _connect(self, connection: HPCConnection) -> paramiko.SSHClient:
        client = self._build_client()
        kwargs = {
            "hostname": connection.hostname,
            "port": connection.port,
            "username": connection.username,
            "timeout": self.settings.ssh_connect_timeout_seconds,
        }
        if connection.ssh_key_reference:
            key_path = Path(connection.ssh_key_reference).expanduser()
            if key_path.exists():
                kwargs["key_filename"] = str(key_path)
        client.connect(**kwargs)
        return client

    def ping(self, connection: HPCConnection) -> bool:
        client = self._connect(connection)
        try:
            result = self.run(connection, "echo connected", client=client)
            return result.exit_code == 0 and "connected" in result.stdout
        finally:
            client.close()

    def run(self, connection: HPCConnection, command: str, client: paramiko.SSHClient | None = None) -> SSHCommandResult:
        owns_client = client is None
        ssh = client or self._connect(connection)
        try:
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            return SSHCommandResult(
                stdout=stdout.read().decode().strip(),
                stderr=stderr.read().decode().strip(),
                exit_code=exit_code,
            )
        finally:
            if owns_client:
                ssh.close()
