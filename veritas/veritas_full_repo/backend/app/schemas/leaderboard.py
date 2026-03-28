from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import DataResponse, ORMModel


class LeaderboardEntryRead(ORMModel):
    id: int
    rank: int | None = None
    overall_rank: int | None = None
    pipeline: str
    dataset: str
    disease_group: str | None = None
    biomarker_group: str | None = None
    score: float
    metric_label: str
    published_at: datetime | None = None
    consented: bool = True


class LeaderboardPushRequest(BaseModel):
    consented: bool = True


class LeaderboardPushResponse(DataResponse[LeaderboardEntryRead]):
    pass


class LeaderboardListResponse(DataResponse[list[LeaderboardEntryRead]]):
    pass
