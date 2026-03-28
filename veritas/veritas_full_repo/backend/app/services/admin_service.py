from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.request import EvaluationRequest
from app.schemas.admin import AdminInboxItem


class AdminService:
    @staticmethod
    def inbox(db: Session) -> list[AdminInboxItem]:
        requests = db.scalars(select(EvaluationRequest).order_by(desc(EvaluationRequest.id)))
        items: list[AdminInboxItem] = []
        for req in requests:
            items.append(
                AdminInboxItem(
                    id=req.request_code,
                    request_id=req.id,
                    user=f"Researcher {req.id}",
                    datasets=[req.dataset.name] if req.dataset else [],
                    pipeline=req.pipeline.image if req.pipeline else "Unknown Pipeline",
                    status=req.status,
                    report_status=req.report_status,
                )
            )
        return items
