import json
from typing import Any

from sqlalchemy.orm import Session

from .models import TransformLog


def append_log(db: Session, action: str, entity_type: str, entity_id: str, details: dict[str, Any], actor: str = "system") -> None:
    db.add(TransformLog(action=action, entity_type=entity_type, entity_id=entity_id, actor=actor, details_json=json.dumps(details, default=str)))

