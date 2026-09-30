from __future__ import annotations

import json
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    BackgroundJob,
    ColumnMapping,
    ComputedMetric,
    DuplicateCandidate,
    DuplicateFeedback,
    IdentityMapping,
    MetricDefinition,
    MetricSuggestion,
    RawRecord,
    RawUpload,
    ShareLink,
    TransformLog,
)


class UploadRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, upload: RawUpload) -> RawUpload:
        self.db.add(upload)
        self.db.flush()
        return upload

    def get(self, upload_id: str) -> RawUpload | None:
        return self.db.get(RawUpload, upload_id)

    def get_active(self, upload_id: str) -> RawUpload | None:
        upload = self.get(upload_id)
        return None if not upload or self.is_archived(upload_id) else upload

    def list(self) -> list[RawUpload]:
        archived = select(TransformLog.entity_id).where(TransformLog.entity_type == "raw_upload", TransformLog.action == "upload_archived")
        statement = select(RawUpload).where(RawUpload.id.not_in(archived)).order_by(RawUpload.created_at.desc())
        return list(self.db.scalars(statement).all())

    def is_archived(self, upload_id: str) -> bool:
        statement = select(TransformLog.id).where(TransformLog.entity_type == "raw_upload", TransformLog.entity_id == upload_id, TransformLog.action == "upload_archived").limit(1)
        return self.db.scalar(statement) is not None

    def display_name(self, upload: RawUpload) -> str:
        statement = select(TransformLog).where(TransformLog.entity_type == "raw_upload", TransformLog.entity_id == upload.id, TransformLog.action == "upload_label_changed").order_by(TransformLog.created_at.desc()).limit(1)
        decision = self.db.scalar(statement)
        return str(json.loads(decision.details_json)["display_name"]) if decision else upload.filename


class RecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_many(self, records: Iterable[RawRecord]) -> None:
        self.db.add_all(list(records))

    def get(self, record_id: str) -> RawRecord | None:
        return self.db.get(RawRecord, record_id)

    def list(self) -> list[RawRecord]:
        archived = select(TransformLog.entity_id).where(TransformLog.entity_type == "raw_upload", TransformLog.action == "upload_archived")
        statement = select(RawRecord).where(RawRecord.upload_id.not_in(archived)).order_by(RawRecord.created_at)
        return list(self.db.scalars(statement).all())

    def for_upload(self, upload_id: str) -> list[RawRecord]:
        return list(self.db.scalars(select(RawRecord).where(RawRecord.upload_id == upload_id).order_by(RawRecord.source_row_number)).all())


class MappingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_many(self, mappings: Iterable[ColumnMapping]) -> None:
        self.db.add_all(list(mappings))
        self.db.flush()

    def get(self, mapping_id: str) -> ColumnMapping | None:
        return self.db.get(ColumnMapping, mapping_id)

    def for_upload(self, upload_id: str, status: str | None = None) -> list[ColumnMapping]:
        statement = select(ColumnMapping).where(ColumnMapping.upload_id == upload_id)
        if status:
            statement = statement.where(ColumnMapping.status == status)
        return list(self.db.scalars(statement.order_by(ColumnMapping.created_at)).all())

    def list(self) -> list[ColumnMapping]:
        archived = select(TransformLog.entity_id).where(TransformLog.entity_type == "raw_upload", TransformLog.action == "upload_archived")
        statement = select(ColumnMapping).where(ColumnMapping.upload_id.not_in(archived)).order_by(ColumnMapping.created_at)
        return list(self.db.scalars(statement).all())

    def live_schema(self) -> list[str]:
        archived = select(TransformLog.entity_id).where(TransformLog.entity_type == "raw_upload", TransformLog.action == "upload_archived")
        rows = self.db.scalars(select(ColumnMapping.canonical_field).where(ColumnMapping.status == "confirmed", ColumnMapping.upload_id.not_in(archived)).distinct()).all()
        return sorted({str(row) for row in rows})


class DuplicateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, candidate_id: str) -> DuplicateCandidate | None:
        return self.db.get(DuplicateCandidate, candidate_id)

    def list(self, status: str | None = None) -> list[DuplicateCandidate]:
        statement = select(DuplicateCandidate)
        if status:
            statement = statement.where(DuplicateCandidate.status == status)
        return list(self.db.scalars(statement.order_by(DuplicateCandidate.score.desc())).all())

    def pairs(self) -> set[tuple[str, str]]:
        return {(row.left_record_id, row.right_record_id) for row in self.list()}

    def add_many(self, candidates: Iterable[DuplicateCandidate]) -> None:
        self.db.add_all(list(candidates))

    def add_feedback(self, feedback: DuplicateFeedback) -> None:
        self.db.add(feedback)

    def feedback(self) -> list[DuplicateFeedback]:
        return list(self.db.scalars(select(DuplicateFeedback).order_by(DuplicateFeedback.created_at)).all())


class MetricRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_definition(self, definition: MetricDefinition) -> MetricDefinition:
        self.db.add(definition)
        self.db.flush()
        return definition

    def get_definition(self, metric_id: str) -> MetricDefinition | None:
        return self.db.get(MetricDefinition, metric_id)

    def definitions(self) -> list[MetricDefinition]:
        return list(self.db.scalars(select(MetricDefinition).order_by(MetricDefinition.created_at)).all())

    def add_computation(self, computed: ComputedMetric) -> ComputedMetric:
        self.db.add(computed)
        self.db.flush()
        return computed

    def computations(self) -> list[ComputedMetric]:
        return list(self.db.scalars(select(ComputedMetric).order_by(ComputedMetric.computed_at.desc())).all())

    def add_suggestion(self, suggestion: MetricSuggestion) -> MetricSuggestion:
        self.db.add(suggestion)
        self.db.flush()
        return suggestion

    def get_suggestion(self, suggestion_id: str) -> MetricSuggestion | None:
        return self.db.get(MetricSuggestion, suggestion_id)


class IdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_hash(self, digest: str) -> IdentityMapping | None:
        return self.db.scalar(select(IdentityMapping).where(IdentityMapping.identity_hash == digest))

    def add(self, mapping: IdentityMapping) -> IdentityMapping:
        self.db.add(mapping)
        self.db.flush()
        return mapping

    def get(self, mapping_id: str) -> IdentityMapping | None:
        return self.db.get(IdentityMapping, mapping_id)


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def append(self, action: str, entity_type: str, entity_id: str, details: dict, actor: str = "system") -> TransformLog:
        row = TransformLog(action=action, entity_type=entity_type, entity_id=entity_id, actor=actor, details_json=json.dumps(details, default=str))
        self.db.add(row)
        self.db.flush()
        return row

    def latest(self, limit: int = 100) -> list[TransformLog]:
        return list(self.db.scalars(select(TransformLog).order_by(TransformLog.created_at.desc()).limit(limit)).all())


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, job: BackgroundJob) -> BackgroundJob:
        self.db.add(job)
        self.db.flush()
        return job

    def get(self, job_id: str) -> BackgroundJob | None:
        return self.db.get(BackgroundJob, job_id)


class ShareRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, link: ShareLink) -> ShareLink:
        self.db.add(link)
        self.db.flush()
        return link

    def by_hash(self, token_hash: str) -> ShareLink | None:
        return self.db.scalar(select(ShareLink).where(ShareLink.token_hash == token_hash, ShareLink.active.is_(True)))
