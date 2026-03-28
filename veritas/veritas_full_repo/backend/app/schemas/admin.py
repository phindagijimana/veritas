from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import DataResponse


class AdminInboxItem(BaseModel):
    id: str
    request_id: int
    user: str
    datasets: list[str]
    pipeline: str
    status: str
    report_status: str


AdminInboxResponse = DataResponse[list[AdminInboxItem]]
