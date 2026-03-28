from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate


class DatasetService:
    @staticmethod
    def list(db: Session, disease: str | None = None, benchmark_only: bool | None = None) -> list[Dataset]:
        stmt = select(Dataset).order_by(Dataset.disease_group.asc(), Dataset.name.asc(), Dataset.version.desc())
        if disease:
            stmt = stmt.where(func.lower(Dataset.disease_group) == disease.lower())
        if benchmark_only is not None:
            stmt = stmt.where(Dataset.benchmark_enabled.is_(benchmark_only))
        return list(db.scalars(stmt))

    @staticmethod
    def detail(db: Session, dataset_ref: str) -> Dataset | None:
        if dataset_ref.isdigit():
            stmt = select(Dataset).where(Dataset.id == int(dataset_ref))
        else:
            stmt = select(Dataset).where((Dataset.code == dataset_ref) | (Dataset.name == dataset_ref))
        return db.scalar(stmt)

    @staticmethod
    def create(db: Session, payload: DatasetCreate) -> Dataset:
        dataset = Dataset(**payload.model_dump())
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return dataset

    @staticmethod
    def list_diseases(db: Session) -> list[dict]:
        stmt = (
            select(
                Dataset.disease_group,
                func.count(Dataset.id).label("dataset_count"),
                func.sum(sa.case((Dataset.is_active.is_(True), 1), else_=0)).label("active_dataset_count"),
            )
            .group_by(Dataset.disease_group)
            .order_by(Dataset.disease_group.asc())
        )
        rows = db.execute(stmt).all()
        return [
            {
                "disease_group": row.disease_group,
                "dataset_count": int(row.dataset_count or 0),
                "active_dataset_count": int(row.active_dataset_count or 0),
            }
            for row in rows
        ]
