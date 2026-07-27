"""Pure-logic tests for v2 import helpers (no DB)."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only")

from app.routers.import_v2 import (  # noqa: E402
    _form_from_hint, _op_from_hint, is_service_warehouse_location,
)


def test_sklad_token_means_service_warehouse():
    for v in ("СКЛАД", "склад", " Склад ", "на складі", "Склад служби"):
        assert is_service_warehouse_location(v) is True, v


def test_real_locations_are_not_warehouse_token():
    for v in ("1 рота", "1 рота Петренко", "Штаб", "", None, "складський Петренко"):
        assert is_service_warehouse_location(v) is False, v


def test_op_from_hint_reads_receipt_and_transfer():
    assert _op_from_hint("надходження") == "receipt"
    assert _op_from_hint(" Надходження ") == "receipt"
    assert _op_from_hint("внутрішнє переміщення") == "transfer"
    assert _op_from_hint("Внутрішнє Переміщення") == "transfer"


def test_op_from_hint_unknown_is_none():
    for v in (None, "", "щось інше", "видача"):
        assert _op_from_hint(v) is None, v


def test_form_from_hint_maps_act_and_defaults_to_nakladna():
    assert _form_from_hint("Акт прийому-передачі") == "акт"
    assert _form_from_hint("акт списання") == "акт"
    assert _form_from_hint("Накладна (вимога)") == "накладна"
    assert _form_from_hint(None) == "накладна"
    assert _form_from_hint("") == "накладна"
