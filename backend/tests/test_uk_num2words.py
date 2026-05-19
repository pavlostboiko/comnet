"""Tests for app.uk_num2words — TZ §8.7 & §8.9."""
import re
from decimal import Decimal

import pytest

from app.uk_num2words import amount_to_words_uk, qty_to_words_uk


LATIN = re.compile(r"[A-Za-z]")


# ── qty_to_words_uk ──────────────────────────────────────────────────────

@pytest.mark.parametrize(("n", "expected"), [
    (0,    "нуль"),
    (1,    "одна"),       # feminine to agree with «одиниць»
    (2,    "дві"),
    (5,    "п'ять"),
    (7,    "сім"),        # TZ §7.5 reference
    (11,   "одинадцять"),
    (21,   "двадцять одна"),
    (100,  "сто"),
    (1000, "одна тисяча"),
])
def test_qty_to_words(n, expected):
    assert qty_to_words_uk(n) == expected


def test_qty_to_words_no_latin():
    for n in [1, 2, 5, 7, 11, 21, 100, 1000]:
        s = qty_to_words_uk(n)
        assert not LATIN.search(s), f"Latin chars in {s!r}"


# ── amount_to_words_uk ───────────────────────────────────────────────────

def test_amount_tz_reference():
    """TZ §7.6 / §8.7 reference case."""
    assert amount_to_words_uk(Decimal("76453.20")) == (
        "сімдесят шість тисяч чотириста п'ятдесят три гривні 20 копійок"
    )


@pytest.mark.parametrize(("amt", "expected"), [
    ("0.00",    "нуль гривень 00 копійок"),
    ("1.00",    "одна гривня 00 копійок"),
    ("2.00",    "дві гривні 00 копійок"),
    ("5.00",    "п'ять гривень 00 копійок"),
    ("21.00",   "двадцять одна гривня 00 копійок"),
    ("100.00",  "сто гривень 00 копійок"),
    ("1000.00", "одна тисяча гривень 00 копійок"),
    ("0.01",    "нуль гривень 01 копійка"),
    ("0.50",    "нуль гривень 50 копійок"),
    ("1.01",    "одна гривня 01 копійка"),
    ("11.11",   "одинадцять гривень 11 копійок"),
])
def test_amount_cases(amt, expected):
    assert amount_to_words_uk(Decimal(amt)) == expected


def test_amount_no_latin_contamination():
    """TZ §8.9: жодної латинської літери в українському пропису."""
    for amt in ["1.00", "7.20", "76453.20", "1234.99"]:
        s = amount_to_words_uk(Decimal(amt))
        assert not LATIN.search(s), f"Latin chars in {s!r}"


def test_amount_rounding_half_up():
    # 0.005 rounds up to 0.01
    assert amount_to_words_uk(Decimal("0.005")) == "нуль гривень 01 копійка"
