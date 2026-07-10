"""Залишки — «яке майно де знаходиться».

Balance per (unit, item_card_num) = SUM(qty_in) − SUM(qty_out) computed
from movements. Only positive balances are surfaced.

Phase 1 endpoints:
- GET /api/residues/by-unit                → summary per unit
- GET /api/residues/by-unit/{unit}         → items detail for one unit

Later phases will add /by-recipient and /me (MOV личный кабинет).
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Item, ItemSplit, Movement, Recipient, User

router = APIRouter(prefix="/api/residues", tags=["residues"])


def _positive_balances_by_unit(db: Session):
    """Yield (to_unit, item_card_num, balance) rows where balance > 0."""
    q = (
        db.query(
            Movement.to_unit.label("unit"),
            Movement.item_card_num.label("card"),
            func.coalesce(func.sum(Movement.qty_in), 0).label("qty_in_total"),
        )
        .filter(Movement.to_unit.isnot(None), Movement.item_card_num.isnot(None))
        .group_by(Movement.to_unit, Movement.item_card_num)
    )
    in_totals = {(row.unit, row.card): Decimal(row.qty_in_total) for row in q.all()}

    q2 = (
        db.query(
            Movement.from_unit.label("unit"),
            Movement.item_card_num.label("card"),
            func.coalesce(func.sum(Movement.qty_out), 0).label("qty_out_total"),
        )
        .filter(Movement.from_unit.isnot(None), Movement.item_card_num.isnot(None))
        .group_by(Movement.from_unit, Movement.item_card_num)
    )
    out_totals = {(row.unit, row.card): Decimal(row.qty_out_total) for row in q2.all()}

    # Combine: for each unit find every card that ever came in, subtract
    # anything that ever left from that unit.
    result: dict[tuple[str, str], Decimal] = {}
    for key, qty in in_totals.items():
        result[key] = result.get(key, Decimal(0)) + qty
    for key, qty in out_totals.items():
        result[key] = result.get(key, Decimal(0)) - qty
    return [(unit, card, bal) for (unit, card), bal in result.items() if bal > 0]


@router.get("/by-unit")
def residues_by_unit(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Summary per unit: card count + total amount (using items.price)."""
    balances = _positive_balances_by_unit(db)

    # Fetch item prices in one round-trip
    card_nums = {card for _, card, _ in balances}
    price_by_card = {}
    if card_nums:
        for it in db.query(Item.number, Item.price).filter(Item.number.in_(card_nums)).all():
            price_by_card[it.number] = Decimal(it.price or 0)

    by_unit: dict[str, dict] = {}
    for unit, card, bal in balances:
        agg = by_unit.setdefault(unit, {"unit": unit, "items_count": 0, "total_qty": Decimal(0), "total_amount": Decimal(0)})
        agg["items_count"] += 1
        agg["total_qty"] += bal
        agg["total_amount"] += bal * price_by_card.get(card, Decimal(0))

    result = list(by_unit.values())
    result.sort(key=lambda x: x["unit"])
    for r in result:
        r["total_qty"] = str(r["total_qty"])
        r["total_amount"] = str(r["total_amount"])
    return result


@router.get("/by-unit/{unit:path}")
def residues_by_unit_detail(
    unit: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Items list for a specific unit with current balance ≥ 1."""
    all_balances = _positive_balances_by_unit(db)
    unit_balances = [(card, bal) for u, card, bal in all_balances if u == unit]

    if not unit_balances:
        return {"unit": unit, "items": []}

    card_nums = [c for c, _ in unit_balances]
    items_by_number = {
        it.number: it for it in db.query(Item).filter(Item.number.in_(card_nums)).all()
    }

    items = []
    for card, bal in unit_balances:
        it = items_by_number.get(card)
        items.append({
            "item_card_num": card,
            "item_id": it.id if it else None,
            "name": it.name if it else None,
            "category": it.category if it else None,
            "unit_of_measure": it.unit_of_measure if it else None,
            "serial_number": it.serial_number if it else None,
            "price": str(it.price) if it and it.price is not None else None,
            "qty": str(bal),
            "amount": str(bal * Decimal(it.price or 0)) if it else None,
        })
    items.sort(key=lambda x: (x["name"] or "", x["item_card_num"]))
    return {"unit": unit, "items": items}


# ── By recipient ─────────────────────────────────────────────────────────

def _recipient_holdings(db: Session, recipient_id: Optional[int] = None):
    """Return (recipient, active_splits_list, serial_items_list) for each
    recipient with anything on hand. If `recipient_id` given, filter to
    just that one.
    """
    q_splits = db.query(ItemSplit).filter(ItemSplit.returned_at.is_(None))
    if recipient_id is not None:
        q_splits = q_splits.filter(ItemSplit.recipient_id == recipient_id)
    splits = q_splits.all()

    q_serial = db.query(Item).filter(Item.issued_to_recipient_id.isnot(None))
    if recipient_id is not None:
        q_serial = q_serial.filter(Item.issued_to_recipient_id == recipient_id)
    serial_items = q_serial.all()

    return splits, serial_items


@router.get("/by-recipient")
def residues_by_recipient(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Summary per recipient — anything with active splits or serial items."""
    splits, serial_items = _recipient_holdings(db)

    # Build item lookup for prices
    item_ids = {s.item_id for s in splits if s.item_id is not None}
    prices: dict[int, Decimal] = {}
    if item_ids:
        for it in db.query(Item.id, Item.price).filter(Item.id.in_(item_ids)).all():
            prices[it.id] = Decimal(it.price or 0)

    # Also load recipients so we can label rows even if a recipient has
    # only serial items (no splits) or vice versa.
    recipient_ids = {s.recipient_id for s in splits if s.recipient_id is not None}
    recipient_ids.update(it.issued_to_recipient_id for it in serial_items if it.issued_to_recipient_id is not None)
    if not recipient_ids:
        return []
    rcpt_by_id = {
        r.id: r for r in db.query(Recipient).filter(Recipient.id.in_(recipient_ids)).all()
    }

    agg: dict[int, dict] = {}
    for s in splits:
        rid = s.recipient_id
        if rid is None:
            continue
        row = agg.setdefault(rid, {
            "recipient_id": rid,
            "callsign": rcpt_by_id[rid].callsign if rid in rcpt_by_id else None,
            "splits_count": 0,
            "serial_count": 0,
            "total_qty": Decimal(0),
            "total_amount": Decimal(0),
        })
        row["splits_count"] += 1
        row["total_qty"] += Decimal(s.qty or 0)
        row["total_amount"] += Decimal(s.qty or 0) * prices.get(s.item_id, Decimal(0))

    for it in serial_items:
        rid = it.issued_to_recipient_id
        row = agg.setdefault(rid, {
            "recipient_id": rid,
            "callsign": rcpt_by_id[rid].callsign if rid in rcpt_by_id else None,
            "splits_count": 0,
            "serial_count": 0,
            "total_qty": Decimal(0),
            "total_amount": Decimal(0),
        })
        row["serial_count"] += 1
        row["total_qty"] += Decimal(it.quantity or 1)
        row["total_amount"] += Decimal(it.quantity or 1) * Decimal(it.price or 0)

    result = list(agg.values())
    result.sort(key=lambda x: (x["callsign"] or "").lower())
    for r in result:
        r["total_qty"] = str(r["total_qty"])
        r["total_amount"] = str(r["total_amount"])
    return result


@router.get("/by-recipient/{recipient_id}")
def residues_by_recipient_detail(
    recipient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rcpt = db.get(Recipient, recipient_id)
    if not rcpt:
        raise HTTPException(404, "Recipient not found")

    splits, serial_items = _recipient_holdings(db, recipient_id)

    # Load items metadata for split rows
    item_ids = {s.item_id for s in splits if s.item_id is not None}
    items_by_id = {}
    if item_ids:
        for it in db.query(Item).filter(Item.id.in_(item_ids)).all():
            items_by_id[it.id] = it

    split_rows = []
    for s in splits:
        it = items_by_id.get(s.item_id)
        split_rows.append({
            "split_id": s.id,
            "item_id": s.item_id,
            "item_number": it.number if it else None,
            "item_name": it.name if it else None,
            "category": it.category if it else None,
            "unit_of_measure": it.unit_of_measure if it else None,
            "qty": str(s.qty),
            "issued_at": s.issued_at.isoformat() if s.issued_at else None,
            "price": str(it.price) if it and it.price is not None else None,
            "amount": str(Decimal(s.qty or 0) * Decimal(it.price or 0)) if it else None,
            "notes": s.notes,
        })
    split_rows.sort(key=lambda x: (x["item_name"] or "", x["item_number"] or ""))

    serial_rows = []
    for it in serial_items:
        serial_rows.append({
            "item_id": it.id,
            "item_number": it.number,
            "item_name": it.name,
            "category": it.category,
            "serial_number": it.serial_number,
            "unit_of_measure": it.unit_of_measure,
            "qty": str(it.quantity or 1),
            "price": str(it.price) if it.price is not None else None,
            "amount": str(Decimal(it.quantity or 1) * Decimal(it.price or 0)),
        })
    serial_rows.sort(key=lambda x: (x["item_name"] or "", x["item_number"] or ""))

    return {
        "recipient_id": rcpt.id,
        "callsign": rcpt.callsign,
        "splits": split_rows,
        "serial_items": serial_rows,
    }
