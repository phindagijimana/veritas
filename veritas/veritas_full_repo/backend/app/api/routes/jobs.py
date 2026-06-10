from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.models.job import Job
from app.schemas.hpc import SlurmJobSubmitRequest
from app.schemas.job import JobAdvanceResponse, JobItemResponse, JobListResponse, JobPreviewResponse
from app.services.job_service import JobService
from app.workers.job_worker import monitor_all_jobs
from app.workers.tasks import enqueue_job_monitor_sweep

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Cap the bytes a single /logs response returns so a runaway log can't OOM the API.
_LOGS_MAX_BYTES = 256 * 1024  # 256 KB tail


@router.get("", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)):
    return {"data": JobService.list(db)}


@router.post("/preview/{request_id}", response_model=JobPreviewResponse)
def preview_slurm_job(
    request_id: str,
    payload: SlurmJobSubmitRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    try:
        return {"data": JobService.preview_slurm_job(db, request_id, payload)}
    except ValueError as exc:
        msg = str(exc)
        if msg == "Request not found":
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc


@router.get("/{job_id}", response_model=JobItemResponse)
def get_job(
    job_id: int,
    include_script: bool = Query(False, description="Include full sbatch script body (can be large)."),
    db: Session = Depends(get_db),
):
    item = JobService.get(db, job_id, include_script=include_script)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/submit/{request_id}", response_model=JobItemResponse)
def submit_slurm_job(
    request_id: str,
    payload: SlurmJobSubmitRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    try:
        return {"data": JobService.submit_slurm_job(db, request_id, payload)}
    except ValueError as exc:
        msg = str(exc)
        if msg == "Request not found":
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc


@router.post("/{job_id}/sync", response_model=JobItemResponse)
def sync_job(job_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = JobService.sync(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/{job_id}/cancel", response_model=JobItemResponse)
def cancel_job(job_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    item = JobService.cancel(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.post("/{job_id}/advance", response_model=JobAdvanceResponse)
def advance_job(job_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    item = JobService.advance(db, job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": item}


@router.get("/{job_id}/logs")
def get_job_logs(
    job_id: int,
    stream: str = Query("stdout", pattern="^(stdout|stderr)$"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Return the last ~256 KB of stdout or stderr for a job, as plain text.

    Useful for the UI's "view logs" panel when debugging a failed Slurm job.
    The HPC stores logs on the cluster filesystem; in mock mode they're
    locally readable, and in slurm mode they're readable once the cluster
    has rsynced them back via the artifact-fetch step.
    """
    row = db.query(Job).filter(Job.id == job_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    path_str = row.stdout_path if stream == "stdout" else row.stderr_path
    if not path_str:
        return {
            "data": {
                "job_id": job_id,
                "stream": stream,
                "available": False,
                "path": None,
                "truncated": False,
                "content": "",
                "message": f"No {stream} path recorded for this job yet.",
            }
        }
    p = Path(path_str)
    if not p.exists() or not p.is_file():
        return {
            "data": {
                "job_id": job_id,
                "stream": stream,
                "available": False,
                "path": str(p),
                "truncated": False,
                "content": "",
                "message": (
                    f"{stream} file at {p} is not readable from the API host. "
                    "On a real cluster, logs are fetched after the job finishes."
                ),
            }
        }
    size = p.stat().st_size
    truncated = size > _LOGS_MAX_BYTES
    with p.open("rb") as fh:
        if truncated:
            fh.seek(-_LOGS_MAX_BYTES, 2)
        data = fh.read()
    try:
        content = data.decode("utf-8", errors="replace")
    except Exception:
        content = repr(data)
    return {
        "data": {
            "job_id": job_id,
            "stream": stream,
            "available": True,
            "path": str(p),
            "size": size,
            "truncated": truncated,
            "content": content,
        }
    }


@router.post("/monitor/sweep")
def trigger_monitor_sweep(_=Depends(require_admin)):
    if get_settings().job_queue_enabled:
        return {"data": {"message": "job monitor sweep queued", "queue_job_id": enqueue_job_monitor_sweep()}}
    result = monitor_all_jobs()
    return {"data": {"message": "job monitor sweep completed inline (JOB_QUEUE_ENABLED=false)", "result": result}}
