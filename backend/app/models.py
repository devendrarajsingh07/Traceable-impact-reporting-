from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def uid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawUpload(Base):
    __tablename__ = "raw_uploads"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    columns_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RawRecord(Base):
    __tablename__ = "raw_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    upload_id: Mapped[str] = mapped_column(ForeignKey("raw_uploads.id"), index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ColumnMapping(Base):
    __tablename__ = "column_mappings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    upload_id: Mapped[str] = mapped_column(ForeignKey("raw_uploads.id"), index=True)
    raw_column: Mapped[str] = mapped_column(String, nullable=False)
    canonical_field: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    left_record_id: Mapped[str] = mapped_column(ForeignKey("raw_records.id"))
    right_record_id: Mapped[str] = mapped_column(ForeignKey("raw_records.id"))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model_version: Mapped[str] = mapped_column(String, default="fellegi-sunter-ecm-v1")


class DuplicateFeedback(Base):
    __tablename__ = "duplicate_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("duplicate_candidates.id"), index=True)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    features_json: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TransformLog(Base):
    __tablename__ = "transform_log"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, default="system")
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IdentityMapping(Base):
    __tablename__ = "identity_mappings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    identity_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    pseudonym: Mapped[str] = mapped_column(String, unique=True, index=True)
    encrypted_identity: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    formula_json: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(String, default="manual")
    suggestion_id: Mapped[str | None] = mapped_column(ForeignKey("metric_suggestions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MetricSuggestion(Base):
    __tablename__ = "metric_suggestions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    formula_json: Mapped[str | None] = mapped_column(Text)
    restatement: Mapped[str | None] = mapped_column(Text)
    clarification_needed: Mapped[str | None] = mapped_column(Text)
    schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ComputedMetric(Base):
    __tablename__ = "computed_metrics"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    metric_definition_id: Mapped[str] = mapped_column(ForeignKey("metric_definitions.id"))
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_record_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    caveats_json: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShareLink(Base):
    __tablename__ = "share_links"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    report_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _immutable(*_args, **_kwargs):
    raise ValueError("Raw and audit records are immutable; append a new decision instead.")


for immutable_model in (RawUpload, RawRecord, TransformLog):
    event.listen(immutable_model, "before_update", _immutable)
    event.listen(immutable_model, "before_delete", _immutable)
