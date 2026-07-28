"""v2 двохосьовий доступ.

Осі:
- service (user.service_id) — бачить майно своєї служби в усіх підрозділах.
- mvo (user.warehouse_id) — бачить майно свого складу всіх служб.
- admin — усе. (operator — legacy v1, для v2-ендпойнтів = без доступу.)

Читання: фільтр query. Запис: guard-функції кидають 403.
"""
from fastapi import HTTPException

from app.models import Assignment, CustodyMovement, Nomenclature


def is_admin(user) -> bool:
    return user.role == "admin"


def _forbid():
    raise HTTPException(403, "Немає доступу до цього ресурсу")


# ── Reads: scope queries ─────────────────────────────────────────────────────

def scope_nomenclature(q, user):
    """Список номенклатури: service — лише своя служба; admin/інші — усе."""
    if user.role == "service" and user.service_id:
        return q.filter(Nomenclature.service_id == user.service_id)
    return q


def scope_movements(q, user):
    if is_admin(user):
        return q
    if user.role == "service" and user.service_id:
        return q.join(Nomenclature, CustodyMovement.nomenclature_id == Nomenclature.id) \
                .filter(Nomenclature.service_id == user.service_id)
    if user.role == "mvo" and user.warehouse_id:
        return q.filter(
            (CustodyMovement.from_warehouse_id == user.warehouse_id)
            | (CustodyMovement.to_warehouse_id == user.warehouse_id)
        )
    return q.filter(False)  # без ролі-скоупу — нічого


def scope_assignments(q, user):
    if is_admin(user):
        return q
    if user.role == "service" and user.service_id:
        return q.join(Nomenclature, Assignment.nomenclature_id == Nomenclature.id) \
                .filter(Nomenclature.service_id == user.service_id)
    if user.role == "mvo" and user.warehouse_id:
        return q.filter(Assignment.warehouse_id == user.warehouse_id)
    return q.filter(False)


def filter_balance_lines(lines, user, warehouse_id):
    """lines: list of dicts with nomenclature service already resolvable.
    Returns the subset the user may see for this warehouse."""
    if is_admin(user):
        return lines
    if user.role == "mvo":
        return lines if user.warehouse_id == warehouse_id else []
    # service filtering handled by caller (needs nomenclature.service) — passthrough
    return lines


def check_warehouse_read(user, warehouse_id):
    """MVO may only read their own warehouse's per-warehouse views."""
    if is_admin(user) or user.role == "service":
        return
    if user.role == "mvo" and user.warehouse_id == warehouse_id:
        return
    _forbid()


# ── Writes: guards ───────────────────────────────────────────────────────────

def check_nomenclature_cud(user, service_id):
    if is_admin(user):
        return
    if user.role == "service" and user.service_id == service_id:
        return
    _forbid()


def check_movement_create(user, from_warehouse_id, nomenclature):
    if is_admin(user):
        return
    if user.role == "service" and user.service_id == nomenclature.service_id:
        return
    if user.role == "mvo" and user.warehouse_id and from_warehouse_id == user.warehouse_id:
        return
    _forbid()


def check_assignment_create(user, warehouse_id):
    if is_admin(user):
        return
    if user.role == "mvo" and user.warehouse_id == warehouse_id:
        return
    _forbid()
