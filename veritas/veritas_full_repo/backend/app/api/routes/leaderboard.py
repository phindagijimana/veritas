from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.leaderboard import LeaderboardListResponse, LeaderboardPushRequest, LeaderboardPushResponse
from app.services.leaderboard_service import LeaderboardService
from app.services.request_service import InvalidPhaseTransitionError

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardListResponse)
def list_leaderboard(
    disease_group: str | None = Query(default=None),
    biomarker_group: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return {"data": LeaderboardService.list_entries(db, disease_group=disease_group, biomarker_group=biomarker_group)}


@router.post("/push/{request_id}", response_model=LeaderboardPushResponse)
def push_to_leaderboard(request_id: str, payload: LeaderboardPushRequest | None = None, db: Session = Depends(get_db)):
    try:
        consented = payload.consented if payload else True
        return {"data": LeaderboardService.push_request(db, request_id, consented=consented)}
    except InvalidPhaseTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
