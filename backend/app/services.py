from __future__ import annotations

import hashlib
import io
import json
import math
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import recordlinkage
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import BackgroundJob, ColumnMapping, ComputedMetric, DuplicateCandidate, DuplicateFeedback, IdentityMapping, MetricDefinition, MetricSuggestion, RawRecord, RawUpload, ShareLink
from .repositories import AuditRepository, DuplicateRepository, IdentityRepository, JobRepository, MappingRepository, MetricRepository, RecordRepository, ShareRepository, UploadRepository
from .schemas import FormulaSpec, MetricCreate
from .security import encrypt_identity, identity_hash, pseudonym_for


CANONICAL_FIELDS = ["beneficiary_id", "beneficiary_name", "program_name", "activity_date", "attendance_status", "session_id", "location", "amount"]
SENSITIVE_FIELDS = {"beneficiary_id", "beneficiary_name", "email", "phone", "address"}
ALLOWED_OPERATIONS = {"count", "count_distinct", "sum", "avg", "average", "min", "max"}


class AIUnavailableError(RuntimeError):
    pass


class InvalidSuggestionError(ValueError):
    pass


def _clean(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value.item() if hasattr(value, "item") else value


def read_tabular(filename: str, content: bytes) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    stream = io.BytesIO(content)
    if suffix == ".csv":
        return pd.read_csv(stream, dtype=object)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(stream, dtype=object)
    if suffix == ".json":
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = parsed.get("records", [parsed])
        return pd.DataFrame(parsed)
    raise ValueError("Only CSV, XLSX, XLS, and JSON files are supported")


def ingest(db: Session, filename: str, content_type: str, content: bytes) -> RawUpload:
    frame = read_tabular(filename, content)
    uploads = UploadRepository(db)
    records = RecordRepository(db)
    audit = AuditRepository(db)
    upload = uploads.add(RawUpload(filename=Path(filename).name, content_type=content_type or "application/octet-stream", sha256=hashlib.sha256(content).hexdigest(), columns_json=json.dumps([str(column) for column in frame.columns])))
    raw_rows = []
    for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
        untouched = {str(key): _clean(value) for key, value in row.items()}
        raw_rows.append(RawRecord(upload_id=upload.id, source_row_number=row_number, raw_data_json=json.dumps(untouched, default=str)))
    records.add_many(raw_rows)
    audit.append("upload_ingested", "raw_upload", upload.id, {"filename": upload.filename, "rows": len(raw_rows), "sha256": upload.sha256})
    db.commit()
    return upload


def rename_upload(db: Session, upload_id: str, display_name: str, actor: str) -> tuple[RawUpload, str]:
    uploads = UploadRepository(db)
    upload = uploads.get_active(upload_id)
    if not upload:
        raise LookupError("Active upload not found")
    cleaned_name = Path(display_name.strip()).name
    if not cleaned_name or cleaned_name in {".", ".."}:
        raise ValueError("Enter a valid display name")
    previous_name = uploads.display_name(upload)
    if cleaned_name != previous_name:
        AuditRepository(db).append("upload_label_changed", "raw_upload", upload.id, {"previous_display_name": previous_name, "display_name": cleaned_name, "original_filename": upload.filename}, actor)
        db.commit()
    return upload, cleaned_name


def archive_upload(db: Session, upload_id: str, actor: str) -> tuple[RawUpload, int]:
    uploads = UploadRepository(db)
    upload = uploads.get_active(upload_id)
    if not upload:
        raise LookupError("Active upload not found")
    retained_records = len(RecordRepository(db).for_upload(upload.id))
    AuditRepository(db).append("upload_archived", "raw_upload", upload.id, {"display_name": uploads.display_name(upload), "original_filename": upload.filename, "raw_records_retained": retained_records}, actor)
    db.commit()
    return upload, retained_records


def create_job(db: Session, kind: str) -> BackgroundJob:
    job = JobRepository(db).add(BackgroundJob(kind=kind))
    db.commit()
    return job


def run_ingest_job(job_id: str, filename: str, content_type: str, content: bytes) -> None:
    with SessionLocal() as db:
        jobs = JobRepository(db)
        job = jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        job.progress = 10
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            upload = ingest(db, filename, content_type, content)
            suggest_mappings(db, upload)
            job = jobs.get(job_id)
            job.status = "completed"
            job.progress = 100
            job.result_json = json.dumps({"upload_id": upload.id, "filename": upload.filename})
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as error:
            db.rollback()
            job = jobs.get(job_id)
            job.status = "failed"
            job.error = str(error)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()


def suggest_mappings(db: Session, upload: RawUpload) -> list[ColumnMapping]:
    mappings = MappingRepository(db)
    existing = mappings.for_upload(upload.id)
    if existing:
        return existing
    suggestions = []
    for raw_column in json.loads(upload.columns_json):
        canonical, score, _ = process.extractOne(raw_column.replace(" ", "_"), CANONICAL_FIELDS, scorer=fuzz.WRatio)
        suggestions.append(ColumnMapping(upload_id=upload.id, raw_column=raw_column, canonical_field=canonical, confidence=score / 100))
    mappings.add_many(suggestions)
    AuditRepository(db).append("mapping_suggested", "raw_upload", upload.id, {"suggestions": [{"raw": item.raw_column, "canonical": item.canonical_field, "confidence": item.confidence} for item in suggestions]})
    db.commit()
    return suggestions


def confirm_mapping(db: Session, mapping_id: str, canonical_field: str, actor: str) -> ColumnMapping:
    mapping = MappingRepository(db).get(mapping_id)
    if not mapping:
        raise LookupError("Mapping not found")
    previous = {"canonical_field": mapping.canonical_field, "status": mapping.status}
    mapping.canonical_field = canonical_field
    mapping.status = "confirmed"
    mapping.confirmed_at = datetime.now(timezone.utc)
    AuditRepository(db).append("mapping_confirmed", "column_mapping", mapping.id, {"previous": previous, "confirmed": {"canonical_field": canonical_field}}, actor)
    db.commit()
    return mapping


def confirmed_map(db: Session, upload_id: str) -> dict[str, str]:
    return {mapping.canonical_field: mapping.raw_column for mapping in MappingRepository(db).for_upload(upload_id, "confirmed")}


def canonical_record(db: Session, record: RawRecord) -> dict[str, Any]:
    raw = json.loads(record.raw_data_json)
    mapping = confirmed_map(db, record.upload_id)
    return {canonical: raw.get(source) for canonical, source in mapping.items()}


def ensure_identity(db: Session, canonical: dict[str, Any]) -> str:
    raw_identity = str(canonical.get("beneficiary_id") or canonical.get("beneficiary_name") or "Unknown beneficiary")
    digest = identity_hash(raw_identity)
    identities = IdentityRepository(db)
    found = identities.by_hash(digest)
    if found:
        return found.pseudonym
    return identities.add(IdentityMapping(identity_hash=digest, pseudonym=pseudonym_for(raw_identity), encrypted_identity=encrypt_identity(raw_identity))).pseudonym


def _record_frame(db: Session) -> pd.DataFrame:
    rows = []
    for record in RecordRepository(db).list():
        canonical = canonical_record(db, record)
        rows.append({"record_id": record.id, "beneficiary_name": str(canonical.get("beneficiary_name") or ""), "activity_date": str(canonical.get("activity_date") or ""), "program_name": str(canonical.get("program_name") or ""), "amount": canonical.get("amount")})
    if not rows:
        return pd.DataFrame(columns=["beneficiary_name", "activity_date", "program_name", "amount"])
    frame = pd.DataFrame(rows).set_index("record_id")
    return frame[frame["beneficiary_name"].str.strip() != ""]


def _feedback_threshold(db: Session) -> float:
    feedback = DuplicateRepository(db).feedback()
    if not feedback:
        return 0.65
    confirmed = sum(item.outcome == "confirmed_duplicate" for item in feedback)
    rejected = sum(item.outcome == "not_duplicate" for item in feedback)
    adjustment = (rejected - confirmed) / max(len(feedback), 1) * 0.08
    return min(0.82, max(0.52, 0.65 + adjustment))


def _field_breakdown(left: pd.Series, right: pd.Series) -> dict[str, float]:
    name = fuzz.token_sort_ratio(str(left["beneficiary_name"]), str(right["beneficiary_name"])) / 100
    date = 1.0 if left["activity_date"] and left["activity_date"] == right["activity_date"] else 0.0
    program = fuzz.token_sort_ratio(str(left["program_name"]), str(right["program_name"])) / 100 if left["program_name"] and right["program_name"] else 0.0
    try:
        amount_left = float(left["amount"])
        amount_right = float(right["amount"])
        amount = max(0.0, 1 - abs(amount_left - amount_right) / max(abs(amount_left), abs(amount_right), 1))
    except (TypeError, ValueError):
        amount = 0.0
    return {"name": round(name, 4), "date": date, "program": round(program, 4), "amount": round(amount, 4)}


def scan_duplicates(db: Session) -> list[DuplicateCandidate]:
    frame = _record_frame(db)
    if len(frame) < 2:
        AuditRepository(db).append("duplicate_scan_completed", "dataset", "all", {"candidates_created": 0, "model": "fellegi-sunter-ecm-v1"})
        db.commit()
        return []
    indexer = recordlinkage.Index()
    if len(frame) < 3:
        indexer.full()
    else:
        window = min(7, len(frame) if len(frame) % 2 else len(frame) - 1)
        indexer.sortedneighbourhood("beneficiary_name", window=window)
    candidate_links = indexer.index(frame)
    comparer = recordlinkage.Compare()
    comparer.string("beneficiary_name", "beneficiary_name", method="jarowinkler", threshold=0.82, label="name")
    comparer.exact("activity_date", "activity_date", label="date")
    comparer.string("program_name", "program_name", method="jarowinkler", threshold=0.85, label="program")
    features = comparer.compute(candidate_links, frame)
    threshold = _feedback_threshold(db)
    algorithm = "fellegi-sunter-ecm"
    try:
        classifier = recordlinkage.ECMClassifier(init="jaro", max_iter=100)
        classifier.fit(features)
        probabilities = classifier.prob(features)
    except Exception:
        algorithm = "fellegi-sunter-prior-fallback"
        probabilities = features["name"] * 0.55 + features["date"] * 0.25 + features["program"] * 0.20
    fallback_probabilities = features["name"] * 0.55 + features["date"] * 0.25 + features["program"] * 0.20
    finite_probabilities = probabilities.map(lambda value: math.isfinite(float(value)))
    if not finite_probabilities.all():
        algorithm = "fellegi-sunter-ecm-with-prior-fallback"
        probabilities = probabilities.where(finite_probabilities, fallback_probabilities)
    duplicates = DuplicateRepository(db)
    existing_pairs = duplicates.pairs()
    created = []
    for pair, probability in probabilities.items():
        left_id, right_id = str(pair[0]), str(pair[1])
        normalized_pair = tuple(sorted((left_id, right_id)))
        probability_value = float(probability)
        if not math.isfinite(probability_value) or probability_value < threshold or normalized_pair in existing_pairs:
            continue
        breakdown = _field_breakdown(frame.loc[left_id], frame.loc[right_id])
        reasons = {"algorithm": algorithm, "threshold": threshold, "probability": round(probability_value, 4), "field_similarities": breakdown}
        created.append(DuplicateCandidate(left_record_id=normalized_pair[0], right_record_id=normalized_pair[1], score=probability_value, reasons_json=json.dumps(reasons), model_version="fellegi-sunter-ecm-v1"))
    duplicates.add_many(created)
    AuditRepository(db).append("duplicate_scan_completed", "dataset", "all", {"candidates_created": len(created), "threshold": threshold, "model": algorithm})
    db.commit()
    return created


def run_duplicate_job(job_id: str) -> None:
    with SessionLocal() as db:
        jobs = JobRepository(db)
        job = jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        job.progress = 15
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            candidates = scan_duplicates(db)
            job = jobs.get(job_id)
            job.status = "completed"
            job.progress = 100
            job.result_json = json.dumps({"created": len(candidates)})
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as error:
            db.rollback()
            job = jobs.get(job_id)
            job.status = "failed"
            job.error = str(error)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()


def decide_duplicate(db: Session, candidate_id: str, decision: str, actor: str) -> DuplicateCandidate:
    duplicates = DuplicateRepository(db)
    candidate = duplicates.get(candidate_id)
    if not candidate:
        raise LookupError("Duplicate candidate not found")
    previous = candidate.status
    candidate.status = "pending" if decision == "unresolved" else decision
    candidate.reviewed_at = datetime.now(timezone.utc)
    duplicates.add_feedback(DuplicateFeedback(candidate_id=candidate.id, outcome=decision, features_json=candidate.reasons_json, actor=actor))
    AuditRepository(db).append("duplicate_reviewed", "duplicate_candidate", candidate.id, {"previous": previous, "decision": decision, "model_version": candidate.model_version}, actor)
    db.commit()
    return candidate


def _passes(record: dict[str, Any], formula: FormulaSpec) -> bool:
    for condition in formula.filters:
        actual = record.get(condition.field)
        if condition.operator == "eq" and str(actual).casefold() != str(condition.value).casefold():
            return False
        if condition.operator == "neq" and str(actual).casefold() == str(condition.value).casefold():
            return False
        if condition.operator == "not_empty" and actual in (None, ""):
            return False
        if condition.operator == "contains" and str(condition.value).casefold() not in str(actual).casefold():
            return False
        if condition.operator == "gte" and str(actual) < str(condition.value):
            return False
        if condition.operator == "lte" and str(actual) > str(condition.value):
            return False
    return True


def validate_formula(db: Session, formula: FormulaSpec) -> FormulaSpec:
    schema = set(MappingRepository(db).live_schema())
    if formula.operation not in ALLOWED_OPERATIONS:
        raise ValueError("Unsupported metric operation")
    referenced = {formula.field, *(item.field for item in formula.filters)}
    invalid = sorted(referenced - schema)
    if invalid:
        raise ValueError(f"Formula references unconfirmed fields: {', '.join(invalid)}")
    return formula


def create_metric_definition(db: Session, payload: MetricCreate, actor: str = "reviewer") -> MetricDefinition:
    formula = validate_formula(db, payload.formula)
    metrics = MetricRepository(db)
    origin = "manual"
    suggestion = None
    if payload.suggestion_id:
        suggestion = metrics.get_suggestion(payload.suggestion_id)
        if not suggestion or suggestion.status != "suggested":
            raise ValueError("Metric suggestion is unavailable or already resolved")
        suggested_formula = json.loads(suggestion.formula_json) if suggestion.formula_json else None
        origin = "ai_suggested_confirmed" if suggested_formula == formula.model_dump() else "ai_suggested_edited"
        suggestion.status = "confirmed"
    definition = metrics.add_definition(MetricDefinition(name=payload.name, description=payload.description, formula_json=formula.model_dump_json(), origin=origin, suggestion_id=suggestion.id if suggestion else None))
    AuditRepository(db).append("metric_defined", "metric_definition", definition.id, {"origin": origin, "suggestion_id": payload.suggestion_id, "formula": formula.model_dump()}, actor)
    db.commit()
    return definition


def compute_metric(db: Session, definition: MetricDefinition) -> ComputedMetric:
    formula = validate_formula(db, FormulaSpec.model_validate_json(definition.formula_json))
    included = []
    excluded_unmapped = 0
    for row in RecordRepository(db).list():
        canonical = canonical_record(db, row)
        if formula.field not in canonical:
            excluded_unmapped += 1
            continue
        if _passes(canonical, formula):
            included.append((row, canonical))
    contributing = [(row, canonical) for row, canonical in included if canonical.get(formula.field) not in (None, "")]
    values = [canonical.get(formula.field) for _, canonical in contributing]
    missing_values = len(included) - len(contributing)
    operation = "avg" if formula.operation == "average" else formula.operation
    if operation == "count":
        value: float | int = len(values)
    elif operation == "count_distinct":
        value = len({str(item).strip().casefold() for item in values})
    else:
        numbers = [float(item) for item in values]
        if operation == "sum":
            value = sum(numbers)
        elif operation == "avg":
            value = sum(numbers) / len(numbers) if numbers else 0
        elif operation == "min":
            value = min(numbers) if numbers else 0
        else:
            value = max(numbers) if numbers else 0
    unresolved = DuplicateRepository(db).list("pending")
    caveats = []
    if unresolved:
        caveats.append(f"{len(unresolved)} possible duplicates remain unresolved")
    if excluded_unmapped:
        caveats.append(f"{excluded_unmapped} records excluded because required fields are not confirmed")
    if missing_values:
        caveats.append(f"{missing_values} matching records excluded because {formula.field} is missing")
    source_record_ids = [row.id for row, _ in contributing]
    result = MetricRepository(db).add_computation(ComputedMetric(metric_definition_id=definition.id, value_json=json.dumps(value), source_record_ids_json=json.dumps(source_record_ids), caveats_json=json.dumps(caveats)))
    AuditRepository(db).append("metric_computed", "computed_metric", result.id, {"definition_id": definition.id, "formula": formula.model_dump(), "source_record_ids": source_record_ids, "caveats": caveats})
    db.commit()
    return result


def _extract_ai_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(cleaned)


def suggest_metric_definition(db: Session, description: str) -> MetricSuggestion:
    schema = MappingRepository(db).live_schema()
    if not schema:
        raise InvalidSuggestionError("Confirm at least one column mapping before requesting an AI suggestion")
    if not settings.anthropic_api_key:
        raise AIUnavailableError("AI suggestions are unavailable because ANTHROPIC_API_KEY is not configured")
    system = f'''You translate nonprofit reporting requests into a strict auditable metric formula. Available fields: {json.dumps(schema)}. Allowed operations: {json.dumps(sorted(ALLOWED_OPERATIONS))}. Return JSON only with keys formula_spec, restatement, clarification_needed. formula_spec must use operation, field, filters. Each filter must use field, operator, value. Use only available fields and allowed operations. Never invent a field. If the request cannot be mapped cleanly, set formula_spec to null and put a concise question in clarification_needed. Do not include prose or markdown fences.'''
    payload = {"model": settings.anthropic_model, "max_tokens": 700, "temperature": 0, "system": system, "messages": [{"role": "user", "content": description}]}
    headers = {"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    try:
        response = httpx.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=settings.anthropic_timeout)
        response.raise_for_status()
        parsed = _extract_ai_json(response.json()["content"][0]["text"])
    except Exception as error:
        raise AIUnavailableError("The AI suggestion service timed out or failed. Use the manual metric builder.") from error
    formula_data = parsed.get("formula_spec")
    clarification = parsed.get("clarification_needed")
    formula = None
    if formula_data:
        try:
            formula = validate_formula(db, FormulaSpec.model_validate(formula_data))
        except Exception as error:
            raise InvalidSuggestionError(f"The model returned an invalid formula: {error}") from error
    if not formula and not clarification:
        raise InvalidSuggestionError("The model response contained neither a valid formula nor a clarification request")
    suggestion = MetricRepository(db).add_suggestion(MetricSuggestion(description=description, formula_json=formula.model_dump_json() if formula else None, restatement=parsed.get("restatement"), clarification_needed=clarification, schema_json=json.dumps(schema)))
    AuditRepository(db).append("metric_ai_suggested", "metric_suggestion", suggestion.id, {"description": description, "schema": schema, "clarification_needed": clarification, "formula": formula.model_dump() if formula else None})
    db.commit()
    return suggestion


def data_gaps(db: Session) -> list[dict[str, Any]]:
    pending_duplicates = len(DuplicateRepository(db).list("pending"))
    unmapped = 0
    missing_dates = 0
    uploads = UploadRepository(db)
    records = RecordRepository(db)
    for upload in uploads.list():
        confirmed = confirmed_map(db, upload.id)
        unmapped += len(set(json.loads(upload.columns_json)) - set(confirmed.values()))
        for record in records.for_upload(upload.id):
            canonical = canonical_record(db, record)
            if "activity_date" in confirmed and not canonical.get("activity_date"):
                missing_dates += 1
    return [{"type": "unresolved_duplicates", "label": "Unresolved duplicates", "count": pending_duplicates, "severity": "warning"}, {"type": "missing_dates", "label": "Missing dates", "count": missing_dates, "severity": "warning"}, {"type": "unmapped_columns", "label": "Unmapped columns", "count": unmapped, "severity": "info"}]


def _suppress_small_segments(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], set[str]] = {}
    for item in records:
        key = (str(item["values"].get("program_name") or ""), str(item["values"].get("location") or ""))
        counts.setdefault(key, set()).add(item["pseudonym"])
    for item in records:
        key = (str(item["values"].get("program_name") or ""), str(item["values"].get("location") or ""))
        if key[1] and len(counts[key]) < settings.k_anonymity_threshold:
            item["values"]["location"] = f"Suppressed (<{settings.k_anonymity_threshold})"
    return records


def lineage_graph(db: Session) -> dict[str, Any]:
    nodes = []
    edges = []
    uploads = UploadRepository(db)
    mappings = MappingRepository(db)
    metrics = MetricRepository(db)
    for upload in uploads.list():
        nodes.append({"id": f"upload:{upload.id}", "type": "upload", "label": upload.filename})
        for mapping in mappings.for_upload(upload.id, "confirmed"):
            mapping_id = f"mapping:{mapping.id}"
            nodes.append({"id": mapping_id, "type": "mapping", "label": f"{mapping.raw_column} → {mapping.canonical_field}"})
            edges.append({"source": f"upload:{upload.id}", "target": mapping_id, "record_ids": []})
            edges.append({"source": mapping_id, "target": "dataset:reviewed", "record_ids": []})
    nodes.append({"id": "dataset:reviewed", "type": "record_set", "label": "Reviewed record set"})
    latest_by_definition = {}
    for computed in metrics.computations():
        latest_by_definition.setdefault(computed.metric_definition_id, computed)
    for definition_id, computed in latest_by_definition.items():
        definition = metrics.get_definition(definition_id)
        record_ids = json.loads(computed.source_record_ids_json)
        node_id = f"metric:{computed.id}"
        nodes.append({"id": node_id, "type": "metric", "label": definition.name, "value": json.loads(computed.value_json), "source_record_ids": record_ids})
        edges.append({"source": "dataset:reviewed", "target": node_id, "record_count": len(record_ids)})
    return {"nodes": nodes, "edges": edges}


def latest_report(db: Session) -> dict[str, Any]:
    metrics = MetricRepository(db)
    latest_by_definition = {}
    for computed in metrics.computations():
        latest_by_definition.setdefault(computed.metric_definition_id, computed)
    metric_rows = []
    all_source_ids = set()
    for definition_id, computed in latest_by_definition.items():
        definition = metrics.get_definition(definition_id)
        source_ids = json.loads(computed.source_record_ids_json)
        all_source_ids.update(source_ids)
        metric_rows.append({"id": computed.id, "name": definition.name, "description": definition.description, "formula": json.loads(definition.formula_json), "value": json.loads(computed.value_json), "source_record_ids": source_ids, "caveats": json.loads(computed.caveats_json), "origin": definition.origin, "computed_at": computed.computed_at.isoformat()})
    records = []
    uploads = UploadRepository(db)
    raw_records = RecordRepository(db)
    for record_id in sorted(all_source_ids):
        record = raw_records.get(record_id)
        if not record:
            continue
        canonical = canonical_record(db, record)
        upload = uploads.get(record.upload_id)
        pseudonym = ensure_identity(db, canonical)
        public_values = {key: value for key, value in canonical.items() if key not in SENSITIVE_FIELDS}
        records.append({"source_record_id": record.id, "pseudonym": pseudonym, "source": f"{upload.filename} · row {record.source_row_number}", "values": public_values})
    records = _suppress_small_segments(records)
    audit_rows = AuditRepository(db).latest()
    audit_trail = [{"id": row.id, "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "actor": row.actor, "details": json.loads(row.details_json), "created_at": row.created_at.isoformat()} for row in audit_rows]
    db.commit()
    return {"title": "Source-linked report", "generated_at": datetime.now(timezone.utc).isoformat(), "metrics": metric_rows, "contributing_records": records, "data_gaps": data_gaps(db), "audit_trail": audit_trail, "lineage": lineage_graph(db), "privacy_note": f"Beneficiary identities are pseudonymized. Segments below {settings.k_anonymity_threshold} beneficiaries are suppressed."}


def create_share_link(db: Session, actor: str) -> dict[str, str]:
    token = secrets.token_urlsafe(24)
    digest = hashlib.sha256(token.encode()).hexdigest()
    snapshot = latest_report(db)
    link = ShareRepository(db).add(ShareLink(token_hash=digest, report_snapshot_json=json.dumps(snapshot), created_by=actor))
    AuditRepository(db).append("report_share_created", "share_link", link.id, {"created_by": actor}, actor)
    db.commit()
    return {"token": token, "url": f"{settings.public_base_url}/shared/{token}"}


def shared_report(db: Session, token: str) -> dict[str, Any] | None:
    digest = hashlib.sha256(token.encode()).hexdigest()
    link = ShareRepository(db).by_hash(digest)
    return json.loads(link.report_snapshot_json) if link else None
