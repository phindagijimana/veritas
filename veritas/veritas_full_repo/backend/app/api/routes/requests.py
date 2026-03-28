from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.request import (
    EvaluationRequestCreate,
    EvaluationRequestItemResponse,
    EvaluationRequestListResponse,
    EvaluationRequestStatusUpdate,
)
from app.services.request_service import InvalidPhaseTransitionError, RequestService

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=EvaluationRequestListResponse)
def list_requests(db: Session = Depends(get_db)):
    return {"data": RequestService.list(db)}


@router.get("/{request_id}", response_model=EvaluationRequestItemResponse)
def get_request(request_id: str, db: Session = Depends(get_db)):
    item = RequestService.detail(db, request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"data": item}


@router.post("", response_model=EvaluationRequestItemResponse)
def create_request(payload: EvaluationRequestCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    created = RequestService.create(db, payload)
    data = created if isinstance(created, dict) else created
    if isinstance(data, dict):
        data.setdefault("submitted_by", getattr(user, "email", "unknown"))
    return {"data": data}


@router.patch("/{request_id}/status", response_model=EvaluationRequestItemResponse)
def update_request_status(request_id: str, payload: EvaluationRequestStatusUpdate, db: Session = Depends(get_db)):
    try:
        item = RequestService.update_status(db, request_id, payload)
    except InvalidPhaseTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"data": item}
