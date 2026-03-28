from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.hpc import SlurmJobSubmitRequest
from app.schemas.job import JobAdvanceResponse, JobItemResponse, JobListResponse
from app.services.job_service import JobService
from app.workers.job_worker import monitor_all_jobs
from app.workers.tasks import enqueue_job_monitor_sweep

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)):
    return {"data": JobService.list(db)}


@router.get("/{job_id}", response_model=JobItemResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    item = JobService.get(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/submit/{request_id}", response_model=JobItemResponse)
def submit_slurm_job(request_id: str, payload: SlurmJobSubmitRequest, db: Session = Depends(get_db)):
    try:
        return {"data": JobService.submit_slurm_job(db, request_id, payload)}
    except ValueError as exc:
        msg = str(exc)
        if msg == "Request not found":
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc


@router.post("/{job_id}/sync", response_model=JobItemResponse)
def sync_job(job_id: int, db: Session = Depends(get_db)):
    item = JobService.sync(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/{job_id}/cancel", response_model=JobItemResponse)
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    item = JobService.cancel(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/{job_id}/advance", response_model=JobAdvanceResponse)
def advance_job(job_id: int, db: Session = Depends(get_db)):
    item = JobService.advance(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/monitor/sweep")
def trigger_monitor_sweep():
    if get_settings().job_queue_enabled:
        return {"data": {"message": "job monitor sweep queued", "queue_job_id": enqueue_job_monitor_sweep()}}
    result = monitor_all_jobs()
    return {"data": {"message": "job monitor sweep completed inline (JOB_QUEUE_ENABLED=false)", "result": result}}
