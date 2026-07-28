"""Автоматичний аудит-лог: хук after_flush пише всі ORM-зміни у `audit_log`.

Ловить create/update/delete для моделей з TRACKED — будь-який ендпоінт, що
змінює їх через ORM, логується автоматично (в т.ч. майбутні функції). Діючий
користувач читається з `session.info` (кладеться в get_current_user).

Свідоме обмеження: bulk `.delete()/.update()` (напр. wipe) НЕ тригерять ORM-
події й не логуються — для очистки це прийнятно.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models import (
    Assignment, AuditLog, CustodyDocument, CustodyMovement, Group, Instance,
    Mvo, Nomenclature, Person, Service, Unit, User, Warehouse,
)

# Сутності, зміни яких логуємо (майно + довідники + користувачі).
TRACKED = {
    Nomenclature, Instance, CustodyMovement, Assignment, CustodyDocument,
    Service, Unit, Group, Warehouse, Person, Mvo, User,
}

# Поля, що не зберігаємо в diff (чутливі/шумні).
_SKIP_FIELDS = {"hashed_password"}


def set_current_user(db: Session, user) -> None:
    """Запам'ятати діючого користувача на сесії — хук читає його при записі."""
    db.info["audit_user"] = user


def _jsonable(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v  # int / float / str / bool / None


def _column_values(obj) -> dict:
    return {c.key: _jsonable(getattr(obj, c.key))
            for c in inspect(obj).mapper.column_attrs
            if c.key not in _SKIP_FIELDS}


def _diff(obj) -> dict:
    st = inspect(obj)
    out = {}
    for attr in st.mapper.column_attrs:
        if attr.key in _SKIP_FIELDS:
            continue
        hist = st.attrs[attr.key].history
        if hist.has_changes():
            old = hist.deleted[0] if hist.deleted else None
            new = hist.added[0] if hist.added else None
            out[attr.key] = [_jsonable(old), _jsonable(new)]
    return out


@event.listens_for(Session, "before_flush")
def _capture(session, flush_context, instances):
    """До flush — знімаємо diff (історія атрибутів іще ціла) і старі значення
    видалених рядків. Creates лишаємо на after_flush (там уже є id)."""
    pend = session.info.setdefault("audit_pending", [])
    for obj in session.new:
        if type(obj) in TRACKED:
            pend.append(["create", obj, None])
    for obj in session.dirty:
        if type(obj) in TRACKED:
            d = _diff(obj)
            if d:
                pend.append(["update", obj, d])
    for obj in session.deleted:
        if type(obj) in TRACKED:
            pend.append(["delete", obj, _column_values(obj)])


@event.listens_for(Session, "after_flush")
def _write(session, flush_context):
    """Після flush — id вже призначені; пишемо рядки аудиту Core-інсертом
    (не тригерить ORM-події → без рекурсії)."""
    pend = session.info.pop("audit_pending", None)
    if not pend:
        return
    user = session.info.get("audit_user")
    uid = getattr(user, "id", None)
    uname = getattr(user, "username", None)
    ts = datetime.utcnow()
    rows = []
    for action, obj, extra in pend:
        # inspect(obj).identity ще None одразу після flush → беремо PK-атрибут.
        pk = inspect(obj).mapper.primary_key[0].key
        eid = extra.get(pk) if action == "delete" else getattr(obj, pk, None)
        if action == "create":
            changes = {k: [None, v] for k, v in _column_values(obj).items()}
        elif action == "update":
            changes = extra
        else:  # delete
            changes = {k: [v, None] for k, v in extra.items()}
        rows.append({
            "ts": ts, "user_id": uid, "username": uname,
            "action": action, "entity_type": type(obj).__name__,
            "entity_id": eid, "changes": changes,
        })
    session.execute(AuditLog.__table__.insert(), rows)
