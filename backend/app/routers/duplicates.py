import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import DuplicateRepository
from ..schemas import DuplicateDecision
from ..services import create_job, decide_duplicate, run_duplicate_job


router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.post("/scan", status_code=202)
def create_duplicate_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = create_job(db, "duplicate_scan")
    background_tasks.add_task(run_duplicate_job, job.id)
    return {"job_id": job.id, "status": job.status, "poll_url": f"/api/jobs/{job.id}"}


@router.get("")
def list_duplicates(db: Session = Depends(get_db)):
    candidates = DuplicateRepository(db).list()
    return [{"id": item.id, "left_record_id": item.left_record_id, "right_record_id": item.right_record_id, "score": item.score, "reasons": json.loads(item.reasons_json), "status": item.status, "model_version": item.model_version} for item in candidates]


@router.post("/{candidate_id}/decision")
def decide(candidate_id: str, payload: DuplicateDecision, db: Session = Depends(get_db)):
    try:
        candidate = decide_duplicate(db, candidate_id, payload.decision, payload.actor)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    return {"id": candidate.id, "status": candidate.status}
