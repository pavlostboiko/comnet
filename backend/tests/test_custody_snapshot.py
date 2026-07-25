"""Pure-logic tests for v2 custody-document numbering (no DB)."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only")

from app.custody_snapshot import _next_seq  # noqa: E402
from app.document_snapshot import calc_validity  # noqa: E402


def test_next_seq_empty_starts_at_one():
    assert _next_seq([], 2026) == "НК-2026-001"


def test_next_seq_increments_ignoring_foreign_formats():
    existing = ["НК-2026-001", "НК-2026-002", "T-foo-3", "Н-440/5", None, ""]
    assert _next_seq(existing, 2026) == "НК-2026-003"


def test_next_seq_ignores_other_years():
    existing = ["НК-2025-009", "НК-2027-004"]
    assert _next_seq(existing, 2026) == "НК-2026-001"


def test_next_seq_zero_pads_to_three():
    existing = [f"НК-2026-{n:03d}" for n in range(1, 12)]  # up to 011
    assert _next_seq(existing, 2026) == "НК-2026-012"


def test_calc_validity_adds_three_days_uk():
    # 2026-07-25 + 3 днів = 28 липня 2026
    assert calc_validity("2026-07-25") == '"28" липня 2026 року'


def test_calc_validity_blank_on_bad_date():
    assert calc_validity(None) == ""
    assert calc_validity("not-a-date") == ""
