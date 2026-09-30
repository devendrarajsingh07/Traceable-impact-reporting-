import io
import json
import math
from types import SimpleNamespace

import pandas as pd
import pytest
import recordlinkage
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ColumnMapping, DuplicateFeedback, RawRecord, RawUpload, TransformLog
from app import services


client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def upload_sample():
    content = b"Participant Name,Event Date,Program,Status,Amount,Location\nAsha Rao,2026-01-14,Nutrition,Present,10,East\nAsha Roa,2026-01-14,Nutrition,Present,10,East\nDev Patel,,Workshop,Present,20,West\nRavi Bose,2026-01-15,Food Support,Present,42.75,West\nNina Paul,2026-01-16,Food Support,Present,,West\n"
    accepted = client.post("/api/uploads", files={"file": ("attendance.csv", io.BytesIO(content), "text/csv")})
    assert accepted.status_code == 202
    job = client.get(accepted.json()["poll_url"]).json()
    assert job["status"] == "completed"
    upload_id = job["result"]["upload_id"]
    mappings = client.post(f"/api/uploads/{upload_id}/mapping-suggestions").json()
    targets = {"Participant Name": "beneficiary_name", "Event Date": "activity_date", "Program": "program_name", "Status": "attendance_status", "Amount": "amount", "Location": "location"}
    for mapping in mappings:
        response = client.post(f'/api/mappings/{mapping["id"]}/confirm', json={"canonical_field": targets[mapping["raw_column"]], "actor": "test"})
        assert response.status_code == 200
    return upload_id


def admin_token():
    response = client.post("/api/auth/token", json={"username": "admin", "password": "test-admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_raw_records_and_audit_log_are_immutable():
    upload_sample()
    with SessionLocal() as db:
        record = db.scalar(select(RawRecord))
        record.raw_data_json = json.dumps({"changed": True})
        with pytest.raises(ValueError):
            db.commit()
        db.rollback()
        log = db.scalar(select(TransformLog))
        log.action = "changed"
        with pytest.raises(ValueError):
            db.commit()


def test_mapping_requires_confirmation_and_appends_audit_entry():
    upload_sample()
    with SessionLocal() as db:
        confirmed = db.scalar(select(func.count()).select_from(ColumnMapping).where(ColumnMapping.status == "confirmed"))
        logs = db.scalar(select(func.count()).select_from(TransformLog).where(TransformLog.action == "mapping_confirmed"))
        assert confirmed == 6
        assert logs == 6


def test_upload_label_and_removal_are_audited_without_mutating_raw_data():
    upload_id = upload_sample()
    renamed = client.patch(f"/api/uploads/{upload_id}", json={"display_name": "Q3 attendance.csv", "actor": "test"})
    assert renamed.status_code == 200
    assert renamed.json()["filename"] == "Q3 attendance.csv"
    listed = client.get("/api/uploads").json()
    assert listed[0]["filename"] == "Q3 attendance.csv"
    assert listed[0]["original_filename"] == "attendance.csv"
    removed = client.delete(f"/api/uploads/{upload_id}", params={"actor": "test"})
    assert removed.status_code == 200
    assert removed.json()["raw_records_retained"] == 5
    assert client.get("/api/uploads").json() == []
    with SessionLocal() as db:
        assert db.get(RawUpload, upload_id).filename == "attendance.csv"
        assert db.scalar(select(func.count()).select_from(RawRecord).where(RawRecord.upload_id == upload_id)) == 5
        actions = set(db.scalars(select(TransformLog.action).where(TransformLog.entity_id == upload_id)).all())
        assert {"upload_ingested", "mapping_suggested", "upload_label_changed", "upload_archived"}.issubset(actions)


def test_record_linkage_explains_candidates_and_stores_feedback(monkeypatch):
    upload_sample()
    monkeypatch.setattr(recordlinkage.ECMClassifier, "prob", lambda _self, features: pd.Series(float("nan"), index=features.index))
    accepted = client.post("/api/duplicates/scan")
    job = client.get(accepted.json()["poll_url"]).json()
    assert job["status"] == "completed"
    candidates = client.get("/api/duplicates").json()
    assert candidates
    assert all(math.isfinite(item["score"]) for item in candidates)
    assert set(candidates[0]["reasons"]["field_similarities"]) == {"name", "date", "program", "amount"}
    response = client.post(f'/api/duplicates/{candidates[0]["id"]}/decision', json={"decision": "confirmed_duplicate", "actor": "test"})
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DuplicateFeedback)) == 1


def test_metric_math_is_hand_checked_and_source_linked():
    upload_sample()
    created = client.post("/api/report/metric-definition", json={"name": "Nutrition spend", "description": "Sum of nutrition amounts", "formula": {"operation": "sum", "field": "amount", "filters": [{"field": "program_name", "operator": "eq", "value": "Nutrition"}]}})
    assert created.status_code == 201
    computed = client.post(f'/api/metrics/{created.json()["id"]}/compute').json()
    assert computed["value"] == 20
    assert len(computed["source_record_ids"]) == 2
    food = client.post("/api/report/metric-definition", json={"name": "Food spend", "description": "Sum of available Food Support amounts", "formula": {"operation": "sum", "field": "amount", "filters": [{"field": "program_name", "operator": "eq", "value": "Food Support"}]}})
    food_result = client.post(f'/api/metrics/{food.json()["id"]}/compute').json()
    assert food_result["value"] == 42.75
    assert len(food_result["source_record_ids"]) == 1
    assert any("amount is missing" in caveat for caveat in food_result["caveats"])


def test_report_anonymizes_exports_and_restricts_raw_records():
    upload_sample()
    created = client.post("/api/metrics", json={"name": "Attendances", "description": "Attendance records", "formula": {"operation": "count", "field": "beneficiary_name", "filters": []}})
    client.post(f'/api/metrics/{created.json()["id"]}/compute')
    report = client.get("/api/report").json()
    serialized = json.dumps(report)
    assert "Asha Rao" not in serialized
    assert report["metrics"][0]["source_record_ids"]
    record_id = report["metrics"][0]["source_record_ids"][0]
    assert client.get(f"/api/raw-records/{record_id}").status_code == 401
    allowed = client.get(f"/api/raw-records/{record_id}", headers={"Authorization": f"Bearer {admin_token()}"})
    assert allowed.status_code == 200
    html_response = client.get("/api/report.html")
    pdf_response = client.get("/api/report.pdf")
    assert "Asha Rao" not in html_response.text
    assert "Beneficiary " in html_response.text
    assert pdf_response.headers["content-type"] == "application/pdf"


def test_ai_unavailable_keeps_manual_path_and_share_snapshot_works():
    upload_sample()
    unavailable = client.post("/api/report/metric-definition/suggest", json={"description": "Unique nutrition beneficiaries"})
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["manual_fallback"] is True
    shared = client.post("/api/share-links", headers={"Authorization": f"Bearer {admin_token()}"})
    assert shared.status_code == 200
    public = client.get(f'/api/public/reports/{shared.json()["token"]}')
    assert public.status_code == 200
    assert public.json()["privacy_note"]


def test_ai_suggestion_is_validated_and_requires_confirmation(monkeypatch):
    upload_sample()
    configured = SimpleNamespace(**services.settings.__dict__)
    configured.anthropic_api_key = "test-key"
    monkeypatch.setattr(services, "settings", configured)

    class ProviderResponse:
        def raise_for_status(self):
            return None

        def json(self):
            content = {"formula_spec": {"operation": "count_distinct", "field": "beneficiary_name", "filters": [{"field": "program_name", "operator": "eq", "value": "Nutrition"}, {"field": "attendance_status", "operator": "eq", "value": "Present"}]}, "restatement": "Count each distinct beneficiary in Nutrition whose status is Present.", "clarification_needed": None}
            return {"content": [{"text": json.dumps(content)}]}

    monkeypatch.setattr(services.httpx, "post", lambda *_args, **_kwargs: ProviderResponse())
    suggested = client.post("/api/report/metric-definition/suggest", json={"description": "Distinct Nutrition beneficiaries marked Present"})
    assert suggested.status_code == 200
    draft = suggested.json()
    assert draft["formula_spec"]["field"] == "beneficiary_name"
    assert client.get("/api/metrics").json() == []
    confirmed = client.post("/api/report/metric-definition", json={"name": "Nutrition beneficiaries", "description": draft["restatement"], "formula": draft["formula_spec"], "suggestion_id": draft["suggestion_id"]})
    assert confirmed.status_code == 201
    assert confirmed.json()["origin"] == "ai_suggested_confirmed"
