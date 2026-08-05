"""Shared XLSX-import parsing helpers.

Cell cleaning, decimal/date parsing, person lookup and serial normalization —
used by the v2 importer (`routers/import_v2.py`) and (until it is retired) the
v1 admin importer. Kept dependency-free of routers so neither imports the other.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

# Placeholder tokens that stand in for «no serial number» in source files.
# Normalized to NULL on import so serial-vs-non-serial logic works correctly.
SERIAL_NONE_TOKENS = {"б/н", "бн", "б\\н", "н/д", "нд", "-", "—", "–", ""}

TYPE_PREFIX_RE = re.compile(r"^\d+\.\s*")


def _clean(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _parse_decimal(val) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    s = str(val).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_date(val) -> Optional[str]:
    """Return YYYY-MM-DD or original string. doc_date columns are VARCHAR."""
    if val is None or val == "":
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val).strip()


def _build_person_lookup(persons) -> dict:
    """Case-insensitive many-key → person.id map.

    Registers every reasonable spelling of a person so the movements import
    can match values like «Petro Ivanenko», «PETRO IVANENKO»,
    «Ivanenko Petro», or the existing search_name.
    """
    lookup: dict[str, int] = {}
    for p in persons:
        first = (p.first_name or "").strip().lower()
        last  = (p.last_name  or "").strip().lower()
        keys = set()
        if p.search_name:
            keys.add(p.search_name.strip().lower())
        if first and last:
            keys.add(f"{first} {last}")   # «petro ivanenko»
            keys.add(f"{last} {first}")   # «ivanenko petro»
        elif last:
            keys.add(last)
        elif first:
            keys.add(first)
        for k in keys:
            # First one wins if there's a collision — we simply skip later
            # persons with the same spelling. In practice search_name is
            # unique, and duplicate first+last is rare.
            lookup.setdefault(k, p.id)
    return lookup


def _resolve_person(raw: Optional[str], lookup: dict) -> Optional[int]:
    if not raw:
        return None
    key = raw.strip().lower()
    if not key:
        return None
    return lookup.get(key)


def _normalize_serial(val) -> Optional[str]:
    s = _clean(val)
    if s is None:
        return None
    if s.lower() in SERIAL_NONE_TOKENS:
        return None
    return s


# ── Захист від навмисно «важких» файлів ──────────────────────────────────────

MAX_UPLOAD_BYTES = 15 * 1024 * 1024          # сам файл
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024   # розпакований вміст (zip-bomb)


def read_xlsx_upload(file) -> bytes:
    """Прочитати завантажений XLSX із двома лімітами.

    XLSX — це zip, тож маленький файл може розпакуватись у гігабайти й покласти
    бекенд ще до першого рядка. Перевіряємо і розмір файлу, і суму розмірів
    записів усередині — до того, як віддати його openpyxl.
    """
    import zipfile
    from io import BytesIO

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Файл більший за {MAX_UPLOAD_BYTES // (1024 * 1024)} МБ")
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            total = sum(i.file_size for i in zf.infolist())
    except zipfile.BadZipFile:
        raise ValueError("Файл не схожий на XLSX")
    if total > MAX_UNCOMPRESSED_BYTES:
        raise ValueError("Вміст файлу надто великий (підозра на zip-бомбу)")
    return data
