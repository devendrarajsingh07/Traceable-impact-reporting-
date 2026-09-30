from typing import Any, Literal

from pydantic import BaseModel, Field


class MappingConfirmation(BaseModel):
    canonical_field: str = Field(min_length=1)
    actor: str = "reviewer"


class DuplicateDecision(BaseModel):
    decision: Literal["confirmed_duplicate", "not_duplicate", "unresolved"]
    actor: str = "reviewer"


class FilterSpec(BaseModel):
    field: str
    operator: Literal["eq", "neq", "not_empty", "gte", "lte", "contains"] = "eq"
    value: Any | None = None


class FormulaSpec(BaseModel):
    operation: Literal["count", "count_distinct", "sum", "avg", "average", "min", "max"]
    field: str
    filters: list[FilterSpec] = []


class MetricCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    formula: FormulaSpec
    suggestion_id: str | None = None


class MetricSuggestionRequest(BaseModel):
    description: str = Field(min_length=4, max_length=500)


class LoginRequest(BaseModel):
    username: str
    password: str


class UploadLabelChange(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    actor: str = "ui-reviewer"
