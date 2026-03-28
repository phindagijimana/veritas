from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.report import DownloadLinkResponse, ReportDetailResponse, ReportItemResponse, ReportListResponse
from app.services.report_service import ReportService
from app.services.request_service import InvalidPhaseTransitionError

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportListResponse)
def list_reports(db: Session = Depends(get_db)):
    return {"data": ReportService.list(db)}


@router.get("/{request_id}", response_model=ReportDetailResponse)
def report_detail(request_id: str, db: Session = Depends(get_db)):
    try:
        return {"data": ReportService.detail_for_request(db, request_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generate/{request_id}", response_model=ReportItemResponse)
def generate_report(request_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    try:
        return {"data": ReportService.generate_for_request(db, request_id)}
    except InvalidPhaseTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/publish/{request_id}", response_model=ReportItemResponse)
def publish_report(request_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    try:
        return {"data": ReportService.publish_for_request(db, request_id)}
    except InvalidPhaseTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{request_id}/download", response_model=DownloadLinkResponse)
def download_report(request_id: str, format: str = Query(...), db: Session = Depends(get_db)):
    try:
        return {"data": {"url": ReportService.download_link(db, request_id, format), "artifact_type": format.upper(), "status": "ready"}}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
