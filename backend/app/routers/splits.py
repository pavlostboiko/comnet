"""Item splits — per-recipient issuance ledger.

Attached to non-serial items. Every authenticated user can create/return
splits (matches the wider «all users see all issuances» decision).

Free-on-hand = item.quantity − SUM(qty WHERE returned_at IS NULL). Any
POST that would push the sum over item.quantity is rejected with 400.
"""
from datetime import date
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Item, ItemSplit, Recipient, User
from app.schemas import ItemSplitCreate, ItemSplitRead, ItemSplitReturn

router = APIRouter(prefix="/api/items/{item_id}/splits", tags=["item-splits"])


def _get_item_or_404(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item


def _active_issued(db: Session, item_id: int, exclude_id: int | None = None) -> Decimal:
    q = db.query(ItemSplit).filter(
        ItemSplit.item_id == item_id,
        ItemSplit.returned_at.is_(None),
    )
    if exclude_id is not None:
        q = q.filter(ItemSplit.id != exclude_id)
    return sum((s.qty for s in q.all()), Decimal(0))


def _serialize(s: ItemSplit) -> dict:
    return {
        "id": s.id,
        "item_id": s.item_id,
        "recipient_id": s.recipient_id,
        "recipient_callsign": s.recipient.callsign if s.recipient else None,
        "qty": s.qty,
        "issued_at": s.issued_at.isoformat() if s.issued_at else None,
        "returned_at": s.returned_at.isoformat() if s.returned_at else None,
        "notes": s.notes,
        "return_notes": s.return_notes,
        "is_active": s.returned_at is None,
    }


@router.get("", response_model=List[ItemSplitRead])
def list_splits(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _get_item_or_404(db, item_id)
    rows = (
        db.query(ItemSplit)
        .filter(ItemSplit.item_id == item_id)
        .order_by(ItemSplit.issued_at.desc(), ItemSplit.id.desc())
        .all()
    )
    return [_serialize(s) for s in rows]


@router.post("", response_model=ItemSplitRead, status_code=status.HTTP_201_CREATED)
def create_split(
    item_id: int,
    payload: ItemSplitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = _get_item_or_404(db, item_id)
    if payload.qty is None or payload.qty <= 0:
        raise HTTPException(400, "Кількість має бути більшою за 0")

    recipient = db.get(Recipient, payload.recipient_id)
    if not recipient:
        raise HTTPException(400, "Отримувача не знайдено")

    active = _active_issued(db, item_id)
    total = Decimal(item.quantity or 0)
    if active + payload.qty > total:
        free = total - active
        raise HTTPException(
            400,
            f"Не можна видати {payload.qty}: вільно лише {free} з {total}",
        )

    issued_at = date.fromisoformat(payload.issued_at) if payload.issued_at else date.today()

    row = ItemSplit(
        item_id=item_id,
        recipient_id=recipient.id,
        qty=payload.qty,
        issued_at=issued_at,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.post("/{split_id}/return", response_model=ItemSplitRead)
def return_split(
    item_id: int,
    split_id: int,
    payload: ItemSplitReturn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = payload or ItemSplitReturn()
    row = db.get(ItemSplit, split_id)
    if not row or row.item_id != item_id:
        raise HTTPException(404, "Split not found")
    if row.returned_at is not None:
        raise HTTPException(400, "Уже повернено")
    row.returned_at = (
        date.fromisoformat(payload.returned_at) if payload.returned_at else date.today()
    )
    row.return_notes = payload.return_notes
    row.returned_by = user.id
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/{split_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_split(
    item_id: int,
    split_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(ItemSplit, split_id)
    if not row or row.item_id != item_id:
        raise HTTPException(404, "Split not found")
    db.delete(row)
    db.commit()
