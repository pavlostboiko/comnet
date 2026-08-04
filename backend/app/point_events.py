"""Запис подій «майно переїхало в іншу точку зберігання».

Три шляхи міняють точку (екземпляр, видача, мітка залишку картки) — щоб історія
була повною, всі три пишуть подію через `log_point_change`. Виклик БЕЗ commit:
комітить той, хто змінює дані.
"""
from datetime import date as date_cls
from typing import Optional

from sqlalchemy.orm import Session

from app.models import PointEvent, StoragePoint


def log_point_change(db: Session, *, nomenclature_id: int, warehouse_id: int,
                     from_point_id: Optional[int], to_point_id: Optional[int],
                     user, instance_id: Optional[int] = None,
                     assignment_id: Optional[int] = None, quantity=None) -> Optional[PointEvent]:
    """Записати зміну точки. Якщо точка не змінилась — подія не потрібна."""
    if from_point_id == to_point_id:
        return None

    def name_of(pid):
        if not pid:
            return None
        p = db.get(StoragePoint, pid)
        return p.name if p else None

    row = PointEvent(
        date=date_cls.today(), nomenclature_id=nomenclature_id, instance_id=instance_id,
        assignment_id=assignment_id, warehouse_id=warehouse_id,
        from_point_id=from_point_id, to_point_id=to_point_id,
        from_point_name=name_of(from_point_id), to_point_name=name_of(to_point_id),
        quantity=quantity, created_by=getattr(user, "id", None),
    )
    db.add(row)
    return row
