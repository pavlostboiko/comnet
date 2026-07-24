"""Pure-logic tests for v2 import helpers (no DB)."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only")

from app.routers.import_v2 import is_service_warehouse_location  # noqa: E402


def test_sklad_token_means_service_warehouse():
    for v in ("СКЛАД", "склад", " Склад ", "на складі", "Склад служби"):
        assert is_service_warehouse_location(v) is True, v


def test_real_locations_are_not_warehouse_token():
    for v in ("1 рота", "1 рота Петренко", "Штаб", "", None, "складський Петренко"):
        assert is_service_warehouse_location(v) is False, v
