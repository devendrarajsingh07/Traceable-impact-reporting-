import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import RecordRepository, UploadRepository
from ..schemas import UploadLabelChange
from ..services import archive_upload, create_job, rename_upload, run_ingest_job


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("", status_code=202)
async def create_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    if not content:
        raise HTTPException(400, "The uploaded file is empty")
    job = create_job(db, "file_ingestion")
    background_tasks.add_task(run_ingest_job, job.id, file.filename or "upload.csv", file.content_type or "application/octet-stream", content)
    return {"job_id": job.id, "status": job.status, "poll_url": f"/api/jobs/{job.id}"}


@router.get("")
def list_uploads(db: Session = Depends(get_db)):
    repository = UploadRepository(db)
    uploads = repository.list()
    records = RecordRepository(db)
    return [{"id": item.id, "filename": repository.display_name(item), "original_filename": item.filename, "sha256": item.sha256, "columns": json.loads(item.columns_json), "row_count": len(records.for_upload(item.id)), "created_at": item.created_at} for item in uploads]


@router.patch("/{upload_id}")
def change_upload_label(upload_id: str, payload: UploadLabelChange, db: Session = Depends(get_db)):
    try:
        upload, display_name = rename_upload(db, upload_id, payload.display_name, payload.actor)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return {"id": upload.id, "filename": display_name, "original_filename": upload.filename, "status": "stored"}


@router.delete("/{upload_id}")
def remove_upload(upload_id: str, actor: str = "ui-reviewer", db: Session = Depends(get_db)):
    try:
        upload, retained_records = archive_upload(db, upload_id, actor)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    return {"id": upload.id, "status": "archived", "raw_records_retained": retained_records}
