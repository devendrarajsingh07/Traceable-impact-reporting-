import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import IdentityMapping
from ..reporting import report_html, report_pdf
from ..repositories import IdentityRepository, RecordRepository
from ..security import UserContext, decrypt_identity, require_org_admin
from ..services import create_share_link, latest_report, lineage_graph, shared_report


router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/report")
def report(db: Session = Depends(get_db)):
    return latest_report(db)


@router.get("/lineage")
def lineage(db: Session = Depends(get_db)):
    return lineage_graph(db)


@router.get("/report.html")
def export_html(db: Session = Depends(get_db)):
    data = latest_report(db)
    return Response(report_html(data), media_type="text/html", headers={"Content-Disposition": "attachment; filename=impact-ledger-report.html"})


@router.get("/report.pdf")
def export_pdf(db: Session = Depends(get_db)):
    data = latest_report(db)
    return Response(report_pdf(data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=impact-ledger-report.pdf"})


@router.post("/share-links")
def create_link(user: UserContext = Depends(require_org_admin), db: Session = Depends(get_db)):
    return create_share_link(db, user.username)


@router.get("/public/reports/{token}")
def public_report(token: str, db: Session = Depends(get_db)):
    data = shared_report(db, token)
    if not data:
        raise HTTPException(404, "Shared report not found")
    return data


@router.get("/public/reports/{token}.html")
def public_report_html(token: str, db: Session = Depends(get_db)):
    data = shared_report(db, token)
    if not data:
        raise HTTPException(404, "Shared report not found")
    return Response(report_html(data, shared=True), media_type="text/html")


@router.get("/raw-records/{record_id}")
def raw_record(record_id: str, _user: UserContext = Depends(require_org_admin), db: Session = Depends(get_db)):
    record = RecordRepository(db).get(record_id)
    if not record:
        raise HTTPException(404, "Raw record not found")
    return {"id": record.id, "upload_id": record.upload_id, "source_row_number": record.source_row_number, "raw_data": json.loads(record.raw_data_json)}


@router.get("/identity-mappings/{mapping_id}")
def identity_mapping(mapping_id: str, _user: UserContext = Depends(require_org_admin), db: Session = Depends(get_db)):
    mapping: IdentityMapping | None = IdentityRepository(db).get(mapping_id)
    if not mapping:
        raise HTTPException(404, "Identity mapping not found")
    return {"id": mapping.id, "pseudonym": mapping.pseudonym, "identity": decrypt_identity(mapping.encrypted_identity)}
