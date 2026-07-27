"""Pure-logic tests for v2 custody-document numbering (no DB)."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only")

from app.custody_snapshot import _next_seq, doc_sort_key  # noqa: E402
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


def test_doc_sort_key_later_suffix_is_greater():
    # Дві накладні однієї серії в одну дату: більший суфікс = пізніша.
    assert doc_sort_key("596/250/2/1") < doc_sort_key("596/250/2/2")


def test_doc_sort_key_numeric_not_lexical():
    # Числове, а не лексичне порівняння: 10 > 2 (лексично "10" < "2").
    assert doc_sort_key("596/250/2/2") < doc_sort_key("596/250/2/10")


def test_doc_sort_key_shorter_prefix_is_less():
    # Коротший (менш конкретний) номер сортується раніше за свій розширений.
    assert doc_sort_key("596/250/2") < doc_sort_key("596/250/2/1")


def test_doc_sort_key_missing_or_nonnumeric_sorts_earliest():
    # Порожній/без цифр → порожній кортеж → найраніше (програє нумерованим).
    assert doc_sort_key(None) == ()
    assert doc_sort_key("") == ()
    assert doc_sort_key("б/н") == ()
    assert doc_sort_key(None) < doc_sort_key("1")


def test_calc_validity_adds_three_days_uk():
    # 2026-07-25 + 3 днів = 28 липня 2026
    assert calc_validity("2026-07-25") == '"28" липня 2026 року'


def test_calc_validity_blank_on_bad_date():
    assert calc_validity(None) == ""
    assert calc_validity("not-a-date") == ""
