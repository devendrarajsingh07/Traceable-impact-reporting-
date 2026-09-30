from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import MappingRepository, UploadRepository
from ..schemas import MappingConfirmation
from ..services import confirm_mapping, suggest_mappings


router = APIRouter(prefix="/api", tags=["mappings"])


@router.post("/uploads/{upload_id}/mapping-suggestions")
def create_mapping_suggestions(upload_id: str, db: Session = Depends(get_db)):
    upload = UploadRepository(db).get(upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    mappings = suggest_mappings(db, upload)
    return [{"id": item.id, "raw_column": item.raw_column, "canonical_field": item.canonical_field, "confidence": item.confidence, "status": item.status} for item in mappings]


@router.get("/mappings")
def list_mappings(db: Session = Depends(get_db)):
    mappings = MappingRepository(db).list()
    return [{"id": item.id, "upload_id": item.upload_id, "raw_column": item.raw_column, "canonical_field": item.canonical_field, "confidence": item.confidence, "status": item.status} for item in mappings]


@router.post("/mappings/{mapping_id}/confirm")
def confirm(mapping_id: str, payload: MappingConfirmation, db: Session = Depends(get_db)):
    try:
        mapping = confirm_mapping(db, mapping_id, payload.canonical_field, payload.actor)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    return {"id": mapping.id, "status": mapping.status, "canonical_field": mapping.canonical_field}
