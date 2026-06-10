from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.report import DownloadLinkResponse, ReportDetailResponse, ReportItemResponse, ReportListResponse
from app.services.report_service import ReportService
from app.services.request_service import InvalidPhaseTransitionError, RequestService

router = APIRouter(prefix="/reports", tags=["reports"])

_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "json": "application/json",
    "csv": "text/csv",
    "html": "text/html",
    "log": "text/plain",
    "txt": "text/plain",
}


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
def download_report(
    request_id: str,
    format: str = Query(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    try:
        return {"data": {"url": ReportService.download_link(db, request_id, format), "artifact_type": format.upper(), "status": "ready"}}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{request_id}/download/{fmt}/file")
def download_report_file(
    request_id: str,
    fmt: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Stream the actual report artifact with auth applied.

    Browsers can't attach a Bearer header to a plain anchor download, so the UI
    fetches this endpoint as a blob (with the JWT/PAT) and triggers a save
    locally. Unlike the `/static` mount, every request to this path is
    authenticated and the user must be logged in.
    """
    try:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        _, report = ReportService._ensure_report(db, request.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    fmt_lower = fmt.lower()
    artifact = next(
        (a for a in report.artifacts if a.artifact_type.lower() == fmt_lower),
        None,
    )
    if artifact is None or not artifact.storage_path:
        raise HTTPException(status_code=404, detail=f"{fmt.upper()} artifact not available.")
    path = Path(artifact.storage_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=410, detail=f"{fmt.upper()} artifact has gone missing on disk.")

    code = getattr(request, "request_code", None) or str(request_id)
    filename = f"{code}-report.{fmt_lower}"
    return FileResponse(
        path=str(path),
        media_type=_MEDIA_TYPES.get(fmt_lower, "application/octet-stream"),
        filename=filename,
    )
