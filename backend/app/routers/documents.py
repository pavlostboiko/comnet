import io
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, DocumentItem, Movement, Person, UnitSettings, User

router = APIRouter(prefix="/api/documents", tags=["documents"])

DOC_TYPES = ("надходження", "переміщення", "накладна_25")

REQUIRED_FIELDS = {
    "надходження":  ["doc_number", "doc_date", "to_unit"],
    "переміщення":  ["doc_number", "doc_date", "from_unit", "to_unit"],
    "накладна_25":  ["doc_number", "doc_date", "from_unit", "to_unit"],
}

EXTRA_FIELDS = [
    "validity_date", "composed_date", "composed_location", "operation_date",
    "op_type_text", "responsible_recipient",
    "sender_id", "receiver_id", "commander_id", "mvo_from_id", "mvo_to_id",
    "accountant_id", "fin_chief_id",
    "total_qty_words", "total_amount_words",
]


# ── Schemas ────────────────────────────────────────────────────────────────

class DocItemIn(BaseModel):
    sort_order: Optional[int] = None
    item_name: Optional[str] = None
    nomenclature_code: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[Decimal] = None
    qty_received: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class DocIn(BaseModel):
    doc_type: str = "переміщення"
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    from_unit: Optional[str] = None
    to_unit: Optional[str] = None
    basis: Optional[str] = None
    service: Optional[str] = None
    # накладна_25 extra fields
    validity_date: Optional[str] = None
    composed_date: Optional[str] = None
    composed_location: Optional[str] = None
    operation_date: Optional[str] = None
    op_type_text: Optional[str] = None
    responsible_recipient: Optional[str] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    commander_id: Optional[int] = None
    mvo_from_id: Optional[int] = None
    mvo_to_id: Optional[int] = None
    accountant_id: Optional[int] = None
    fin_chief_id: Optional[int] = None
    total_qty_words: Optional[str] = None
    total_amount_words: Optional[str] = None
    items: List[DocItemIn] = []


# ── Helpers ────────────────────────────────────────────────────────────────

def _sorted_items(doc: Document):
    return sorted(doc.items, key=lambda x: (x.sort_order or 0, x.id))


def _items_for_display(doc: Document) -> list:
    if doc.items:
        return [
            {
                "id": it.id,
                "sort_order": it.sort_order,
                "item_name": it.item_name,
                "nomenclature_code": it.nomenclature_code,
                "unit_of_measure": it.unit_of_measure,
                "category": it.category,
                "quantity": float(it.quantity) if it.quantity is not None else None,
                "qty_received": float(it.qty_received) if it.qty_received is not None else None,
                "price": float(it.price) if it.price is not None else None,
                "amount": float(it.amount) if it.amount is not None else None,
                "notes": it.notes,
            }
            for it in _sorted_items(doc)
        ]
    # Fallback for imported documents: build from linked movements
    return [
        {
            "id": None,
            "sort_order": i,
            "item_name": m.item_name,
            "nomenclature_code": m.nomenclature_code,
            "unit_of_measure": m.unit_of_measure,
            "category": str(m.category) if m.category is not None else None,
            "quantity": float(m.qty_in or m.qty_out or 0),
            "qty_received": None,
            "price": float(m.price) if m.price is not None else None,
            "amount": float(m.price * (m.qty_in or m.qty_out or 0)) if m.price else None,
            "notes": m.serial_number,
        }
        for i, m in enumerate(sorted(doc.movements, key=lambda x: x.id), 1)
    ]


def _doc_to_dict(doc: Document) -> dict:
    extra = doc.extra_data or {}
    return {
        "id": doc.id,
        "doc_type": doc.doc_type,
        "doc_type_label": doc.movements[0].doc_type if doc.movements else None,
        "doc_number": doc.doc_number,
        "doc_date": doc.doc_date,
        "from_unit": doc.from_unit,
        "to_unit": doc.to_unit,
        "basis": doc.basis,
        "service": doc.service,
        "status": doc.status,
        "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
        **{f: extra.get(f) for f in EXTRA_FIELDS},
        "items": _items_for_display(doc),
    }


def _get_or_404(doc_id: int, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


def _apply_items(doc: Document, items: List[DocItemIn], db: Session):
    for it in list(doc.items):
        db.delete(it)
    db.flush()
    for idx, it in enumerate(items):
        db.add(DocumentItem(
            document_id=doc.id,
            sort_order=it.sort_order if it.sort_order is not None else idx,
            item_name=it.item_name,
            nomenclature_code=it.nomenclature_code,
            unit_of_measure=it.unit_of_measure,
            category=it.category,
            quantity=it.quantity,
            qty_received=it.qty_received,
            price=it.price,
            amount=it.amount,
            notes=it.notes,
        ))


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.get("")
def list_documents(
    doc_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Document)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    docs = q.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "doc_type": d.doc_type,
            "doc_type_label": d.movements[0].doc_type if d.movements else None,
            "doc_number": d.doc_number,
            "doc_date": d.doc_date,
            "from_unit": d.from_unit,
            "to_unit": d.to_unit,
            "status": d.status,
            "items_count": len(d.movements) if d.status != 'draft' else len(d.items),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return _doc_to_dict(_get_or_404(doc_id, db))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(payload: DocIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.doc_type not in DOC_TYPES:
        raise HTTPException(400, f"doc_type must be one of: {DOC_TYPES}")

    extra = {f: getattr(payload, f) for f in EXTRA_FIELDS}
    doc = Document(
        doc_type=payload.doc_type,
        doc_number=payload.doc_number,
        doc_date=payload.doc_date,
        from_unit=payload.from_unit,
        to_unit=payload.to_unit,
        basis=payload.basis,
        service=payload.service,
        status="draft",
        extra_data=extra,
        created_by=user.id,
    )
    db.add(doc)
    db.flush()
    _apply_items(doc, payload.items, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.put("/{doc_id}")
def update_document(doc_id: int, payload: DocIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Підписаний документ не можна редагувати. Спочатку зніміть підпис.")

    doc.doc_type = payload.doc_type
    doc.doc_number = payload.doc_number
    doc.doc_date = payload.doc_date
    doc.from_unit = payload.from_unit
    doc.to_unit = payload.to_unit
    doc.basis = payload.basis
    doc.service = payload.service
    doc.extra_data = {f: getattr(payload, f) for f in EXTRA_FIELDS}
    _apply_items(doc, payload.items, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Не можна видалити підписаний документ. Спочатку зніміть підпис.")
    db.delete(doc)
    db.commit()


# ── Sign / Unsign ──────────────────────────────────────────────────────────

@router.post("/{doc_id}/sign")
def sign_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status != "draft":
        raise HTTPException(400, "Документ вже підписано.")

    # Validate required fields
    errors = []
    for field in REQUIRED_FIELDS.get(doc.doc_type, []):
        if not getattr(doc, field, None):
            errors.append(field)
    if not doc.items:
        errors.append("items (список позицій порожній)")
    if errors:
        raise HTTPException(422, {"detail": "Заповніть обов'язкові поля", "missing": errors})

    extra = doc.extra_data or {}
    mvo_from_id = extra.get("mvo_from_id") or extra.get("sender_id")
    mvo_to_id   = extra.get("mvo_to_id")   or extra.get("receiver_id")

    for it in _sorted_items(doc):
        is_incoming = (doc.doc_type == "надходження")
        m = Movement(
            document_id=doc.id,
            entry_date=doc.doc_date,
            item_name=it.item_name,
            unit_of_measure=it.unit_of_measure,
            category=it.category,
            nomenclature_code=it.nomenclature_code,
            qty_in=it.quantity if is_incoming else (it.qty_received or None),
            qty_out=None if is_incoming else it.quantity,
            from_unit=doc.from_unit,
            to_unit=doc.to_unit,
            basis=doc.basis,
            doc_date=doc.doc_date,
            doc_number=doc.doc_number,
            doc_type=doc.doc_type,
            service=doc.service,
            price=it.price,
            mvo_from_id=mvo_from_id,
            mvo_to_id=mvo_to_id,
            created_by=user.id,
        )
        db.add(m)

    doc.status = "signed"
    doc.signed_at = datetime.utcnow()
    doc.signed_by = user.id
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.post("/{doc_id}/unsign")
def unsign_document(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)
    if doc.status == "draft":
        raise HTTPException(400, "Документ вже у статусі чернетки.")

    db.query(Movement).filter(Movement.document_id == doc.id).delete(synchronize_session=False)
    doc.status = "draft"
    doc.signed_at = None
    doc.signed_by = None
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


# ── Excel export (накладна_25) ─────────────────────────────────────────────

@router.get("/{doc_id}/export/xlsx")
def export_xlsx(doc_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    doc = _get_or_404(doc_id, db)

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(500, "openpyxl not installed")

    extra    = doc.extra_data or {}
    settings = db.query(UnitSettings).first()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _person(pid):
        if not pid:
            return None
        return db.query(Person).filter(Person.id == int(pid)).first()

    def person_name(pid):
        """Returns 'Ім'я ПРІЗВИЩЕ' (first_name + LAST_NAME uppercase)."""
        p = _person(pid)
        if not p:
            return ""
        return " ".join(filter(None, [p.first_name or "", (p.last_name or "").upper()])).strip()

    def person_pos(pid):
        p = _person(pid)
        return (p.position or "") if p else ""

    executor_name = ""
    if doc.created_by:
        u = db.query(User).filter(User.id == doc.created_by).first()
        if u:
            executor_name = u.username

    # ── Styles ────────────────────────────────────────────────────────────────
    thin    = Side(style="thin")
    all_bdr = Border(left=thin, right=thin, top=thin, bottom=thin)
    bot_bdr = Border(bottom=thin)
    c_aln   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    l_aln   = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    r_aln   = Alignment(horizontal="right",  vertical="center", wrap_text=True)
    bold    = Font(bold=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Накладна"

    # Column widths A–J matching nakladna.xlsx reference
    for i, w in enumerate([4.33, 21.86, 12.13, 4.13, 4.86, 10.66, 4.66, 6.66, 12.66, 11.66], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    def v(row, col, val="", fnt=None, aln=None, brd=None):
        c = ws.cell(row=row, column=col, value=val)
        if fnt: c.font = fnt
        if aln: c.alignment = aln
        if brd: c.border = brd
        return c

    def mcel(r1, c1, r2, c2, val="", fnt=None, aln=None, brd=None):
        if r1 != r2 or c1 != c2:
            ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
        c = ws.cell(row=r1, column=c1, value=val)
        if fnt: c.font = fnt
        if aln: c.alignment = aln
        if brd: c.border = brd
        return c

    unit_name = (settings.name  or "") if settings else ""
    edrpou    = (settings.edrpou or "") if settings else ""
    location  = extra.get("composed_location") or ((settings.location or "") if settings else "")

    # ── Rows 1–15: Header block ───────────────────────────────────────────────

    # B1:D2 merged — unit name (spans 2 rows)
    mcel(1, 2, 2, 4, unit_name, aln=l_aln)
    v(1, 8, "Додаток 25", aln=r_aln)
    ws.row_dimensions[1].height = 14.45

    v(2, 8, "до Інструкції з обліку військового майна", aln=r_aln)
    ws.row_dimensions[2].height = 14.25

    mcel(3, 2, 3, 4, "(найменування юридичної особи)", aln=c_aln)
    v(3, 8, "у Збройних Силах України", aln=r_aln)

    v(4, 1, "Код згідно з\xa0ЄДРПОУ", aln=l_aln)
    mcel(4, 4, 4, 5, edrpou, aln=c_aln)
    v(4, 8, "(пункт 24 розділу ІV)", aln=l_aln)
    ws.row_dimensions[4].height = 15.4

    ws.row_dimensions[5].height = 10  # spacer

    validity = extra.get("validity_date") or ""
    v(6, 2, f'Дійсна до "{validity}"', aln=l_aln)
    ws.row_dimensions[6].height = 14.25

    v(7, 3, "Накладна (вимога)", fnt=Font(bold=True, size=11), aln=c_aln)
    v(7, 4, "№",                  fnt=Font(bold=True, size=11), aln=c_aln)
    v(7, 5, doc.doc_number or "", fnt=Font(bold=True, size=11), aln=l_aln)
    ws.row_dimensions[7].height = 21.6

    # Rows 8–11: location and signing date (right side, columns I:J)
    mcel(8,  9, 8,  10, location,              aln=c_aln)
    mcel(9,  9, 9,  10, "(місце складання)",   aln=c_aln)
    mcel(10, 9, 10, 10, extra.get("composed_date") or doc.doc_date or "", aln=c_aln)
    mcel(11, 9, 11, 10, "(дата складання)",    aln=c_aln)
    ws.row_dimensions[8].height = 14.45

    v(12, 1, "Дата операції", aln=l_aln)
    v(12, 3, extra.get("operation_date") or "", aln=l_aln)
    v(12, 5, "Служба забезпечення", aln=l_aln)
    v(12, 9, doc.service or "", aln=l_aln)
    ws.row_dimensions[12].height = 15.4

    v(13, 1, "Вид операції", aln=l_aln)
    mcel(13, 3, 13, 4, extra.get("op_type_text") or "", aln=l_aln)
    v(13, 5, "Підстава (мета) ", aln=l_aln)
    mcel(13, 9, 13, 10, doc.basis or "", aln=l_aln)
    ws.row_dimensions[13].height = 26.0

    v(14, 1, "Відповідальний одержувач ", aln=l_aln)
    mcel(14, 3, 14, 10, extra.get("responsible_recipient") or "", aln=l_aln)
    ws.row_dimensions[14].height = 15.6

    v(15, 1, "Передає", aln=l_aln)
    mcel(15, 3, 15, 4, doc.from_unit or "", aln=l_aln)
    v(15, 5, "Приймає", aln=l_aln)
    mcel(15, 9, 15, 10, doc.to_unit or "", aln=l_aln)
    ws.row_dimensions[15].height = 15.4

    ws.row_dimensions[16].height = 9.6  # spacer before table

    # ── Rows 17–19: Table header ──────────────────────────────────────────────

    # Columns that span both rows 17 and 18
    for col, label in [
        (1,  "№ з/п"),
        (2,  "Назва військового майна або однорідна група (вид)"),
        (3,  "Код номенклатури"),
        (4,  "одиниця виміру"),
        (5,  "категорія (сорт)"),
        (6,  "Вартість за\xa0одиницю"),
        (9,  "Сума"),
        (10, "Примітка"),
    ]:
        mcel(17, col, 18, col, label, fnt=bold, aln=c_aln, brd=all_bdr)

    # G17:H17 — "Кількість" spans both qty columns horizontally in row 17
    mcel(17, 7, 17, 8, "Кількість", fnt=bold, aln=c_aln, brd=all_bdr)
    ws.row_dimensions[17].height = 14.45

    # Row 18: split sub-headers under "Кількість"
    v(18, 7, "відправлено\n(вимагається)", fnt=bold, aln=c_aln, brd=all_bdr)
    v(18, 8, "прийнято\n(відпущено)",      fnt=bold, aln=c_aln, brd=all_bdr)
    ws.row_dimensions[18].height = 82.25

    # Row 19: column numbers 1–10
    for i in range(1, 11):
        v(19, i, str(i), aln=c_aln, brd=all_bdr)

    # ── Data rows ─────────────────────────────────────────────────────────────
    items_list = _items_for_display(doc)
    r = 20
    total_qty = Decimal(0)
    total_amt = Decimal(0)

    for idx, it in enumerate(items_list, 1):
        qty = Decimal(str(it["quantity"])) if it["quantity"] is not None else Decimal(0)
        amt = Decimal(str(it["amount"]))   if it["amount"]   is not None else Decimal(0)
        row_data = [
            (1,  idx),
            (2,  it["item_name"] or ""),
            (3,  it["nomenclature_code"] or ""),
            (4,  it["unit_of_measure"] or ""),
            (5,  it["category"] or ""),
            (6,  float(it["price"])        if it["price"]        is not None else ""),
            (7,  float(qty) if qty else ""),
            (8,  float(it["qty_received"]) if it["qty_received"] is not None else ""),
            (9,  float(amt) if amt else ""),
            (10, it["notes"] or ""),
        ]
        for col, val in row_data:
            c = ws.cell(row=r, column=col, value=val)
            c.border    = all_bdr
            c.alignment = l_aln if col == 2 else c_aln
        ws.row_dimensions[r].height = 26
        r += 1
        total_qty += qty
        total_amt += amt

    # Minimum 8 filler rows
    for _ in range(max(0, 8 - len(items_list))):
        for col in range(1, 11):
            ws.cell(row=r, column=col).border = all_bdr
        ws.row_dimensions[r].height = 26
        r += 1

    # Totals row "Всього"
    mcel(r, 1, r, 6, "Всього", fnt=bold, aln=r_aln, brd=all_bdr)
    v(r, 7, float(total_qty) if total_qty else "", brd=all_bdr, aln=c_aln)
    v(r, 8, "",                                    brd=all_bdr, aln=c_aln)
    v(r, 9, float(total_amt) if total_amt else "", brd=all_bdr, aln=c_aln)
    v(r, 10, "",                                   brd=all_bdr, aln=c_aln)
    r += 2

    # ── Commander block ───────────────────────────────────────────────────────
    cmd_id = extra.get("commander_id")
    v(r, 1,  person_pos(cmd_id),  aln=l_aln)
    v(r, 10, person_name(cmd_id), aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    mcel(r, 6, r, 7, "(підпис)",                   aln=c_aln)
    mcel(r, 9, r, 10, "(власне ім'я та прізвище)", aln=c_aln)
    r += 1

    v(r, 1, "Всього передано ", aln=l_aln)
    mcel(r, 3, r, 9, extra.get("total_qty_words") or "", aln=c_aln)
    v(r, 10, "одиниць,", aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    v(r, 7, "(кількість прописом)", aln=c_aln)
    r += 1

    amt_words = extra.get("total_amount_words") or ""
    mcel(r, 1, r, 10, f"на\xa0суму {amt_words}", aln=l_aln)
    ws.row_dimensions[r].height = 13.9
    r += 1

    v(r, 7, "(сума прописом)", aln=c_aln)
    r += 1

    if executor_name:
        v(r, 1, "Виконавець:", aln=l_aln)
        v(r, 3, executor_name,  aln=l_aln)
        r += 1
    r += 1  # blank before МВО

    # ── МВО section ───────────────────────────────────────────────────────────
    v(r, 1, "Матеріально відповідальні особи:", aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    v(r, 1, "здав:", aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    mvo_from = extra.get("mvo_from_id") or extra.get("sender_id")
    v(r, 1,  person_pos(mvo_from),  aln=l_aln)
    v(r, 10, person_name(mvo_from), aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    v(r, 3, "(посада)", aln=c_aln, brd=bot_bdr)
    v(r, 7, "(підпис)", aln=c_aln, brd=bot_bdr)
    mcel(r, 9, r, 10, "(власне ім'я та прізвище)", aln=c_aln, brd=bot_bdr)
    r += 1

    v(r, 1, "прийняв:", aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    mvo_to = extra.get("mvo_to_id") or extra.get("receiver_id")
    v(r, 1,  person_pos(mvo_to),  aln=l_aln)
    v(r, 10, person_name(mvo_to), aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    v(r, 3, "(посада)", aln=c_aln, brd=bot_bdr)
    v(r, 7, "(підпис)", aln=c_aln, brd=bot_bdr)
    mcel(r, 9, r, 10, "(власне ім'я та прізвище)", aln=c_aln, brd=bot_bdr)
    r += 1

    # ── Financial section ─────────────────────────────────────────────────────
    mcel(r, 1, r, 10,
         "Відмітка фінансово-економічного органу про\xa0відображення у\xa0регістрах бухгалтерського обліку:",
         aln=l_aln)
    ws.row_dimensions[r].height = 19.25
    r += 1

    # Financial table header
    mcel(r, 1, r, 2, "Найменування\nоблікового регістру",
         fnt=bold, aln=c_aln, brd=all_bdr)
    mcel(r, 3, r, 5, "За дебетом рахунку (субрахунку, коду аналітичного обліку)",
         fnt=bold, aln=c_aln, brd=all_bdr)
    mcel(r, 6, r, 8, "За кредитом рахунку (субрахунку, коду аналітичного обліку)",
         fnt=bold, aln=c_aln, brd=all_bdr)
    mcel(r, 9, r, 10, "Сума", fnt=bold, aln=c_aln, brd=all_bdr)
    r += 1

    for _ in range(3):
        mcel(r, 1, r, 2,  brd=all_bdr)
        mcel(r, 3, r, 5,  brd=all_bdr)
        mcel(r, 6, r, 8,  brd=all_bdr)
        mcel(r, 9, r, 10, brd=all_bdr)
        ws.row_dimensions[r].height = 15
        r += 1

    mcel(r, 1, r, 10,
         "Особа, яка відобразила господарську операцію в\xa0бухгалтерському обліку ",
         aln=l_aln)
    ws.row_dimensions[r].height = 13.9
    r += 1

    acc_id = extra.get("accountant_id")
    v(r, 1,  person_pos(acc_id) or "головний бухгалтер", aln=l_aln)
    v(r, 10, person_name(acc_id), aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 1

    v(r, 2, "(посада)", aln=c_aln, brd=bot_bdr)
    v(r, 7, "(підпис)", aln=c_aln, brd=bot_bdr)
    mcel(r, 9, r, 10, "(власне ім'я та прізвище)", aln=c_aln, brd=bot_bdr)
    ws.row_dimensions[r].height = 15.4
    r += 1

    v(r, 3, f"{doc.doc_date or ''} року", aln=l_aln)
    ws.row_dimensions[r].height = 19.25
    r += 2

    fin_id = extra.get("fin_chief_id")
    mcel(r, 1, r + 2, 3,
         person_pos(fin_id) or "начальник фінансової служби",
         aln=Alignment(horizontal="left", vertical="center", wrap_text=True))
    v(r + 2, 10, person_name(fin_id), aln=l_aln)
    ws.row_dimensions[r].height = 15.4
    r += 3

    v(r, 7, "(підпис)", aln=c_aln, brd=bot_bdr)
    mcel(r, 9, r, 10, "(власне ім'я та прізвище)", aln=c_aln, brd=bot_bdr)

    # ── Stream ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"накладна_{doc.doc_number or doc.id}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
