"""Журнал змін (audit_log) — перегляд, лише admin."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _row(a: AuditLog) -> dict:
    return {
        "id": a.id,
        "ts": a.ts.isoformat() if a.ts else None,
        "user_id": a.user_id,
        "username": a.username,
        "action": a.action,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "changes": a.changes or {},
    }


@router.get("")
def list_audit(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    entity_id: Optional[int] = None,
    date_from: Optional[str] = None,   # ISO date/datetime
    date_to: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)
    if date_from:
        try:
            q = q.filter(AuditLog.ts >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(AuditLog.ts <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    total = q.count()
    rows = q.order_by(AuditLog.ts.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_row(a) for a in rows]}


@router.get("/meta")
def audit_meta(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Значення для фільтрів: наявні типи сутностей + дії."""
    types = [t for (t,) in db.query(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)]
    actions = [a for (a,) in db.query(AuditLog.action).distinct().order_by(AuditLog.action)]
    return {"entity_types": types, "actions": actions}
