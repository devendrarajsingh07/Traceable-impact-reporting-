import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import MappingRepository, MetricRepository
from ..schemas import MetricCreate, MetricSuggestionRequest
from ..services import AIUnavailableError, InvalidSuggestionError, compute_metric, create_metric_definition, suggest_metric_definition


router = APIRouter(prefix="/api", tags=["metrics"])


def _create(payload: MetricCreate, db: Session):
    try:
        definition = create_metric_definition(db, payload)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {"id": definition.id, "name": definition.name, "formula": json.loads(definition.formula_json), "origin": definition.origin}


@router.post("/metrics", status_code=201)
def create_metric(payload: MetricCreate, db: Session = Depends(get_db)):
    return _create(payload, db)


@router.post("/report/metric-definition", status_code=201)
def confirm_metric(payload: MetricCreate, db: Session = Depends(get_db)):
    return _create(payload, db)


@router.post("/report/metric-definition/suggest")
def suggest_metric(payload: MetricSuggestionRequest, db: Session = Depends(get_db)):
    try:
        suggestion = suggest_metric_definition(db, payload.description)
    except AIUnavailableError as error:
        raise HTTPException(503, {"message": str(error), "manual_fallback": True, "canonical_schema": MappingRepository(db).live_schema()}) from error
    except InvalidSuggestionError as error:
        raise HTTPException(422, {"message": str(error), "manual_fallback": True, "canonical_schema": MappingRepository(db).live_schema()}) from error
    return {"suggestion_id": suggestion.id, "formula_spec": json.loads(suggestion.formula_json) if suggestion.formula_json else None, "restatement": suggestion.restatement, "clarification_needed": suggestion.clarification_needed, "canonical_schema": json.loads(suggestion.schema_json)}


@router.get("/metrics")
def list_metrics(db: Session = Depends(get_db)):
    definitions = MetricRepository(db).definitions()
    return [{"id": item.id, "name": item.name, "description": item.description, "formula": json.loads(item.formula_json), "origin": item.origin} for item in definitions]


@router.post("/metrics/{metric_id}/compute")
def calculate_metric(metric_id: str, db: Session = Depends(get_db)):
    definition = MetricRepository(db).get_definition(metric_id)
    if not definition:
        raise HTTPException(404, "Metric definition not found")
    try:
        result = compute_metric(db, definition)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {"id": result.id, "value": json.loads(result.value_json), "source_record_ids": json.loads(result.source_record_ids_json), "caveats": json.loads(result.caveats_json)}
