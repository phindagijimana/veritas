from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.hpc_connection import HPCConnection
from app.schemas.hpc import HPCConnectionConfig, HPCSummary
from app.core.config import get_settings
from app.services.hpc_adapter import get_hpc_adapter
from app.services.ssh_service import SSHService


class HPCConnectionService:
    @staticmethod
    def connect(db: Session, config: HPCConnectionConfig, persist: bool = True) -> HPCConnection:
        """
        Validate SSH with Paramiko (real connection), then optionally persist as active HPC.
        Does not use the mock Slurm adapter — you get a true SSH check even when HPC_MODE=mock.
        """
        key_ref = config.ssh_key_reference or config.key_path
        item = HPCConnection(
            hostname=config.hostname,
            username=config.username,
            port=config.port,
            ssh_key_reference=key_ref,
            notes=config.notes,
            status="pending",
            is_active=True,
        )
        ssh = SSHService()
        ssh.validate_connection(item)
        item.status = "connected"
        if not persist:
            return item
        active_connections = db.scalars(select(HPCConnection).where(HPCConnection.is_active.is_(True)))
        for connection in active_connections:
            connection.is_active = False
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def test_connection(db: Session, config: HPCConnectionConfig) -> HPCConnection:
        return HPCConnectionService.connect(db, config, persist=False)

    @staticmethod
    def get_active_connection(db: Session) -> HPCConnection | None:
        return db.scalar(select(HPCConnection).where(HPCConnection.is_active.is_(True)).order_by(desc(HPCConnection.created_at)).limit(1))

    @staticmethod
    def list_connections(db: Session) -> list[HPCConnection]:
        return list(db.scalars(select(HPCConnection).order_by(desc(HPCConnection.created_at))))

    @staticmethod
    def summary(db: Session) -> HPCSummary:
        active = HPCConnectionService.get_active_connection(db)
        adapter = get_hpc_adapter()
        result = adapter.summary(active)
        settings = get_settings()
        return HPCSummary(
            status="Connected" if active and active.status == "connected" else "Unknown",
            queued=result.queue_count,
            running=result.running_count,
            gpu_free=result.gpu_free,
            active_connection=active,
            hpc_mode=settings.hpc_mode,
        )
