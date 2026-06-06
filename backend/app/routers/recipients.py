"""CRUD for `recipients` — особовий склад (бійці), іdentified by callsign.

Distinct from `persons` (which holds chiefs / signatories). Used as
items.issued_to_recipient_id target for the «Видане» field.

Auth: all authenticated users can list/create — needed for inline-create
in the items form. Update/delete: admin only.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Recipient, User
from app.schemas import RecipientCreate, RecipientRead, RecipientUpdate

router = APIRouter(prefix="/api/recipients", tags=["recipients"])


@router.get("", response_model=List[RecipientRead])
def list_recipients(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Recipient).order_by(Recipient.callsign).all()


@router.post("", response_model=RecipientRead, status_code=status.HTTP_201_CREATED)
def create_recipient(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    callsign = (payload.callsign or "").strip()
    if not callsign:
        raise HTTPException(400, "Позивний не може бути порожнім")
    existing = db.query(Recipient).filter(Recipient.callsign == callsign).first()
    if existing:
        raise HTTPException(409, "Отримувач з таким позивним уже існує")
    row = Recipient(callsign=callsign, is_active=payload.is_active, created_by=user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{recipient_id}", response_model=RecipientRead)
def update_recipient(
    recipient_id: int,
    payload: RecipientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.get(Recipient, recipient_id)
    if not row:
        raise HTTPException(404, "Not found")
    if payload.callsign is not None:
        callsign = payload.callsign.strip()
        if not callsign:
            raise HTTPException(400, "Позивний не може бути порожнім")
        conflict = db.query(Recipient).filter(
            Recipient.callsign == callsign, Recipient.id != recipient_id,
        ).first()
        if conflict:
            raise HTTPException(409, "Отримувач з таким позивним уже існує")
        row.callsign = callsign
    if payload.is_active is not None:
        row.is_active = payload.is_active
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.get(Recipient, recipient_id)
    if not row:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
