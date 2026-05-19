"""Ukrainian number-to-words for invoice export.

Two public functions:
  - qty_to_words_uk(qty)    → number in feminine (agrees with «одиниць»)
  - amount_to_words_uk(amt) → «<words> гривень/гривні/гривня <NN> копійок/копійки/копійка»
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

from num2words import num2words


Number = Union[int, float, Decimal, str]


def _hryvnia_word(n: int) -> str:
    n = abs(int(n))
    last2 = n % 100
    last = n % 10
    if 11 <= last2 <= 14:
        return "гривень"
    if last == 1:
        return "гривня"
    if 2 <= last <= 4:
        return "гривні"
    return "гривень"


def _kopeck_word(n: int) -> str:
    n = abs(int(n))
    last2 = n % 100
    last = n % 10
    if 11 <= last2 <= 14:
        return "копійок"
    if last == 1:
        return "копійка"
    if 2 <= last <= 4:
        return "копійки"
    return "копійок"


def qty_to_words_uk(qty: Number) -> str:
    """Number in Ukrainian, feminine (to agree with «одиниць»).

    Fractional values returned as plain digits (no fractional words spec'd in TZ).
    """
    q = Decimal(str(qty))
    if q == q.to_integral_value():
        return num2words(int(q), lang="uk", gender="feminine")
    return format(q.normalize(), "f")


def amount_to_words_uk(amount: Number) -> str:
    """Money amount in Ukrainian: hryvnia in words + kopecks as 2-digit number.

    Example:
        Decimal("76453.20") →
            "сімдесят шість тисяч чотириста п'ятдесят три гривні 20 копійок"
    """
    a = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    int_part = int(a)
    kop = int((a - int_part) * 100)
    hryv_words = num2words(int_part, lang="uk", gender="feminine")
    return f"{hryv_words} {_hryvnia_word(int_part)} {kop:02d} {_kopeck_word(kop)}"
