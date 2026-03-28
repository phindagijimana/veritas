from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pipeline import Pipeline
from app.schemas.pipeline import PipelineCreate


class PipelineService:
    @staticmethod
    def list(db: Session) -> list[Pipeline]:
        return list(db.scalars(select(Pipeline).order_by(Pipeline.id.desc())))

    @staticmethod
    def create(db: Session, payload: PipelineCreate) -> Pipeline:
        pipeline = Pipeline(**payload.model_dump())
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        return pipeline
