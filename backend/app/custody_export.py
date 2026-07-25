"""Build the Додаток 25 XLSX for a v2 `custody_documents` document.

Reuses the v1 renderer `document_export.build_xlsx` (which reads only snap fields
+ a list of position dicts). Positions are assembled here from the document's
linked `custody_movements` + their `nomenclature`.
"""
from typing import List

from sqlalchemy.orm import Session

from app.document_export import build_xlsx
from app.document_snapshot import SNAP_KEYS
from app.models import CustodyDocument, Instance, Nomenclature

__all__ = ["build_xlsx_v2", "has_snap", "document_lines"]


def has_snap(doc: CustodyDocument) -> bool:
    """v2 docs are snapped on every save, so any snap key present = exportable.
    (Unlike v1, there are no pre-snap legacy v2 documents; org name may be blank
    on dev without making the doc unexportable.)"""
    extra = doc.extra_data or {}
    return any(k in extra for k in SNAP_KEYS)


def document_lines(doc: CustodyDocument, db: Session) -> List[dict]:
    """Position dicts for the XLSX renderer, ordered by movement id."""
    lines: List[dict] = []
    for m in sorted(doc.movements or [], key=lambda x: x.id):
        nom = m.nomenclature or db.get(Nomenclature, m.nomenclature_id)
        serial = None
        if m.instance_id:
            inst = m.instance or db.get(Instance, m.instance_id)
            serial = inst.serial_no if inst else None
        lines.append({
            "item_name": nom.name if nom else "",
            "nomenclature_code": nom.code if nom else None,
            "unit_of_measure": nom.unit_of_measure if nom else None,
            "category": nom.category if nom else None,
            "price": nom.price if nom else None,
            "quantity": m.quantity,
            "qty_received": None,
            "notes": serial or m.card_number,
        })
    return lines


def build_xlsx_v2(doc: CustodyDocument, db: Session) -> bytes:
    """Render `doc` + its linked movements into Дод.25 XLSX bytes."""
    return build_xlsx(doc, document_lines(doc, db))
