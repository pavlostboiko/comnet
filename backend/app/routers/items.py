from datetime import date
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AssetDocument, Item, ItemDocument, ItemSplit, Movement, Person, Recipient, User
from app.schemas import ItemCreate, ItemListRead, ItemRead, ItemUpdate

router = APIRouter(prefix="/api/items", tags=["items"])


def _sync_documents(db: Session, item_id: int, docs: list) -> None:
    links = db.query(ItemDocument).filter(ItemDocument.item_id == item_id).all()
    doc_ids = [lnk.doc_id for lnk in links]
    for lnk in links:
        db.delete(lnk)
    db.flush()
    for doc_id in doc_ids:
        doc = db.get(AssetDocument, doc_id)
        if doc:
            db.delete(doc)
    db.flush()
    for d in docs:
        if not any([d.doc_type, d.doc_number, d.doc_date]):
            continue
        doc = AssetDocument(doc_type=d.doc_type, doc_number=d.doc_number, doc_date=d.doc_date)
        db.add(doc)
        db.flush()
        db.add(ItemDocument(item_id=item_id, doc_id=doc.id))


def _get_or_404(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _has_positive_residue_anywhere(db: Session, item_number: str | None) -> bool:
    """Any unit has SUM(qty_in) − SUM(qty_out) > 0 for this card."""
    if not item_number:
        return False
    in_by_unit = {
        row[0]: Decimal(row[1] or 0)
        for row in db.query(Movement.to_unit, func.sum(Movement.qty_in))
            .filter(Movement.item_card_num == item_number, Movement.to_unit.isnot(None))
            .group_by(Movement.to_unit).all()
    }
    out_by_unit = {
        row[0]: Decimal(row[1] or 0)
        for row in db.query(Movement.from_unit, func.sum(Movement.qty_out))
            .filter(Movement.item_card_num == item_number, Movement.from_unit.isnot(None))
            .group_by(Movement.from_unit).all()
    }
    all_units = set(in_by_unit) | set(out_by_unit)
    return any(in_by_unit.get(u, Decimal(0)) - out_by_unit.get(u, Decimal(0)) > 0 for u in all_units)


def maybe_place_orphan_return(db: Session, item: Item, user: User) -> Movement | None:
    """After a return event that leaves the item fully unassigned, if the
    item has no movement-based residue anywhere (i.e. it was never placed
    via a real movement — «Видано»-import shortcut), synthesize a movement
    placing item.quantity into the МВО's subdivision (from user.person.unit).

    Returns the created Movement (or None if no synthesis happened).
    Caller must have already closed any splits; this reads item.quantity as
    the amount to land, matching the split we just closed.
    """
    if not user.person_id or item.quantity is None:
        return None
    person = db.get(Person, user.person_id)
    if not person or not person.unit:
        return None
    if _has_positive_residue_anywhere(db, item.number):
        return None
    qty = Decimal(item.quantity or 0) or Decimal(1)
    today = date.today()
    mv = Movement(
        entry_date=today.isoformat(),
        item_name=item.name,
        item_card_num=item.number,
        unit_of_measure=item.unit_of_measure,
        category=item.category,
        qty_in=qty,
        to_unit=person.unit,
        mvo_to_id=user.person_id,
        serial_number=item.serial_number,
        notes="Автоматично при поверненні до МВО",
        price=item.price,
        nomenclature_code=item.nomenclature_code,
        created_by=user.id,
    )
    db.add(mv)
    return mv


def _journal_serial_change(
    db: Session,
    item: Item,
    old_recipient_id: int | None,
    new_recipient_id: int | None,
    user: User,
    issued_at: date | None = None,
) -> None:
    """Mirror an issued_to_recipient_id change into the item_splits ledger.

    Semantics:
      - old is None, new set        → open new split (initial issuance)
      - old set, new None           → close previous active split (return)
      - old set, new set (different) → close previous + open new (reassignment)

    Split qty: 1 for serial (physical unit), item.quantity for non-serial
    (the entire card lands on one recipient — matches the old items-modal
    quick-issue and the XLSX «Видано» column semantics).

    `issued_at` — when the new split's issue date should be; today if omitted.
    Return/close events always use today (when the return was recorded).

    On explicit return (new is None), if the item is orphan (no movements)
    we place it in МВО's unit via a synthetic movement — otherwise it would
    vanish from every residues surface.
    """
    if old_recipient_id == new_recipient_id:
        return
    today = date.today()
    if old_recipient_id is not None:
        active = (
            db.query(ItemSplit)
            .filter(ItemSplit.item_id == item.id, ItemSplit.returned_at.is_(None))
            .all()
        )
        for row in active:
            row.returned_at = today
            row.returned_by = user.id
    if new_recipient_id is not None:
        split_qty = Decimal(1) if item.serial_number else (Decimal(item.quantity or 0) or Decimal(1))
        db.add(ItemSplit(
            item_id=item.id,
            recipient_id=new_recipient_id,
            qty=split_qty,
            issued_at=issued_at or today,
            created_by=user.id,
        ))
    elif old_recipient_id is not None:
        # Explicit return branch — old set, new None.
        maybe_place_orphan_return(db, item, user)


@router.get("", response_model=List[ItemListRead])
def list_items(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    # Natural sort by `number`: pure-numeric strings sorted by zero-padded
    # value ("1" < "2" < "10"), mixed/alpha values keep lexicographic order.
    natural_key = case(
        (Item.number.op("~")("^[0-9]+$"), func.lpad(Item.number, 20, "0")),
        else_=Item.number,
    )
    return db.query(Item).order_by(natural_key, Item.number).all()


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_or_404(db, item_id)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.query(Item).filter(Item.number == payload.number).first()
    if existing:
        raise HTTPException(status_code=409, detail="Item number already exists")

    item = Item(
        number=payload.number,
        name=payload.name,
        category=payload.category,
        nomenclature_code=payload.nomenclature_code,
        serial_number=payload.serial_number,
        unit_of_measure=payload.unit_of_measure,
        price=payload.price,
        quantity=payload.quantity,
        item_type=payload.item_type,
        batch_id=payload.batch_id,
        notes=payload.notes,
        is_official=payload.is_official,
        issued_to_recipient_id=payload.issued_to_recipient_id,
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    issued_at = date.fromisoformat(payload.issued_at) if payload.issued_at else None
    _journal_serial_change(db, item, None, item.issued_to_recipient_id, user, issued_at)
    _sync_documents(db, item.id, payload.documents)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = _get_or_404(db, item_id)

    if payload.number and payload.number != item.number:
        conflict = db.query(Item).filter(Item.number == payload.number).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Item number already exists")

    old_recipient_id = item.issued_to_recipient_id
    # issued_at is transient — used to seed the new split, never stored on Item
    payload_issued_at = payload.issued_at
    for field, value in payload.model_dump(exclude_unset=True, exclude={"documents", "issued_at"}).items():
        setattr(item, field, value)

    issued_at = date.fromisoformat(payload_issued_at) if payload_issued_at else None
    _journal_serial_change(db, item, old_recipient_id, item.issued_to_recipient_id, user, issued_at)

    if payload.documents is not None:
        _sync_documents(db, item_id, payload.documents)

    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}/history")
def get_item_history(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Chronological history of an item — external movements + issuance ledger.

    Returns events sorted DESC by date. Each event includes:
      - date, kind, qty, actor (username, if known), notes, source-specific fields.

    Missing pre-migration data (e.g. serial items assigned before migration 011)
    is not backfilled — history starts from the point splits were captured.
    """
    item = _get_or_404(db, item_id)

    # Users cache for actor labels
    user_ids: set[int] = set()

    # ── movements matched by item_card_num == item.number ────────────────
    movements = (
        db.query(Movement)
        .filter(Movement.item_card_num == item.number)
        .all()
    )
    for m in movements:
        if m.created_by is not None:
            user_ids.add(m.created_by)

    # ── splits (both issued & returned events) ───────────────────────────
    splits = (
        db.query(ItemSplit)
        .filter(ItemSplit.item_id == item.id)
        .all()
    )
    recipient_ids = {s.recipient_id for s in splits if s.recipient_id is not None}
    for s in splits:
        if s.created_by is not None:
            user_ids.add(s.created_by)
        if s.returned_by is not None:
            user_ids.add(s.returned_by)

    user_by_id = {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}
    rcpt_by_id = {
        r.id: r.callsign
        for r in db.query(Recipient).filter(Recipient.id.in_(recipient_ids)).all()
    } if recipient_ids else {}

    events: list[dict] = []
    for m in movements:
        qty_in = float(m.qty_in or 0)
        qty_out = float(m.qty_out or 0)
        events.append({
            "date": m.entry_date or m.doc_date,
            "kind": "in" if qty_in > qty_out else "out",
            "qty": qty_in if qty_in > qty_out else qty_out,
            "from_unit": m.from_unit,
            "to_unit": m.to_unit,
            "doc_number": m.doc_number,
            "doc_date": m.doc_date,
            "notes": m.notes,
            "actor": user_by_id.get(m.created_by) if m.created_by else None,
            "source": "movement",
            "source_id": m.id,
        })

    for s in splits:
        callsign = rcpt_by_id.get(s.recipient_id) if s.recipient_id else None
        events.append({
            "date": s.issued_at.isoformat() if s.issued_at else None,
            "kind": "issued",
            "qty": float(s.qty or 0),
            "recipient": callsign,
            "notes": s.notes,
            "actor": user_by_id.get(s.created_by) if s.created_by else None,
            "source": "split",
            "source_id": s.id,
        })
        if s.returned_at is not None:
            events.append({
                "date": s.returned_at.isoformat(),
                "kind": "returned",
                "qty": float(s.qty or 0),
                "recipient": callsign,
                "notes": s.return_notes,
                "actor": user_by_id.get(s.returned_by) if s.returned_by else None,
                "source": "split",
                "source_id": s.id,
            })

    # Sort DESC by date (missing dates last)
    events.sort(key=lambda e: (e["date"] is None, e["date"] or ""), reverse=True)
    return events


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = _get_or_404(db, item_id)
    _sync_documents(db, item_id, [])
    db.delete(item)
    db.commit()
