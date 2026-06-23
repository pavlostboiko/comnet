"""Unit tests for admin import helpers — pure-logic only.

Verifies the column-map parsing for items and the op-type → (operation,
form) mapping for movements without touching a DB.

`app.routers.admin` imports the SQLAlchemy stack which requires DATABASE_URL.
We set bogus values before import so config validation passes; we never
construct a session in this test file.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only")

from openpyxl import Workbook  # noqa: E402

from app.routers.admin import (  # noqa: E402
    ITEMS_COLUMN_MAP, OP_TYPE_MAP,
    _find_items_header_row, _build_items_col_map, _parse_decimal,
)


def _xlsx_with_items_header():
    wb = Workbook()
    ws = wb.active
    # Headers in row 1
    headers = ["№", "Товар", "Код номер", "Серійний номер",
               "Од. виміру", "Вартість", "Кіл-сть", "Категорія", "Де знаходиться"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    ws.cell(row=2, column=1, value="K-001")
    ws.cell(row=2, column=2, value="Ноутбук")
    return wb


def test_find_items_header_row():
    wb = _xlsx_with_items_header()
    ws = wb.active
    assert _find_items_header_row(ws) == 1


def test_build_items_col_map_maps_all_headers():
    wb = _xlsx_with_items_header()
    ws = wb.active
    col_map = _build_items_col_map(ws, 1)
    # All 9 headers map to fields
    assert set(col_map.values()) == set(ITEMS_COLUMN_MAP.values())


def test_find_items_header_row_returns_none_when_missing():
    wb = Workbook()
    ws = wb.active
    ws.cell(row=1, column=1, value="random")
    assert _find_items_header_row(ws) is None


def test_op_type_map_canonical_values():
    # Map produces the 2-axis values the new schema expects
    assert OP_TYPE_MAP["надходження"] == ("надходження", "акт")
    assert OP_TYPE_MAP["переміщення"] == ("переміщення", "накладна")
    assert OP_TYPE_MAP["внутрішнє переміщення"] == ("переміщення", "накладна")


def test_parse_decimal_handles_ua_locale():
    from decimal import Decimal
    assert _parse_decimal("1 234,56") == Decimal("1234.56")
    assert _parse_decimal("0") == Decimal("0")
    assert _parse_decimal(None) is None
    assert _parse_decimal("not a number") is None
    assert _parse_decimal(42) == Decimal("42")
