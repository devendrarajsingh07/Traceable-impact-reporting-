import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import JobRepository


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = JobRepository(db).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"id": job.id, "kind": job.kind, "status": job.status, "progress": job.progress, "result": json.loads(job.result_json) if job.result_json else None, "error": job.error}
