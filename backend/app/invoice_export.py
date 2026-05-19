"""Pure openpyxl helpers for invoice XLSX export.

Extracted from `routers.documents` so they can be unit-tested in isolation
(no FastAPI / DB dependencies in the import chain).
"""
from copy import copy as _copy


# ── Template layout constants (N=5 baseline) ─────────────────────────────

TEMPLATE_SLOTS = 5            # rows 20–24 reserved for items
TEMPLATE_LAST_ROW = 44        # last printable row at N=5
ROW_ITEM_START = 20
ROW_TOTALS = 25               # "Всього" row
ROW_CHIEF_POST = 27
ROW_CHIEF_NAME = 27
ROW_QTY_WORDS = 29            # "Всього передано <words> одиниць"
ROW_AMT_WORDS = 31            # "на суму ..."
ROW_SENDER = 36               # MVO «здав»
ROW_RECEIVER = 39             # MVO «прийняв»
ROW_FIN_POST = 41             # Fin signature post (merged A41:C43)
ROW_FIN_NAME = 43


# ── Row & merge manipulation ─────────────────────────────────────────────

def capture_and_unmerge(ws, base_row: int):
    """Return list of (r1,c1,r2,c2) for every merged range at/below `base_row`,
    and unmerge them. Used together with `remerge_shifted` around insert/delete.
    """
    ranges = [
        (mr.min_row, mr.min_col, mr.max_row, mr.max_col)
        for mr in list(ws.merged_cells.ranges)
        if mr.min_row >= base_row
    ]
    for r1, c1, r2, c2 in ranges:
        ws.unmerge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
    return ranges


def remerge_shifted(ws, ranges, delta: int):
    for r1, c1, r2, c2 in ranges:
        ws.merge_cells(start_row=r1 + delta, start_column=c1,
                       end_row=r2 + delta, end_column=c2)


def capture_row_style(ws, row: int, cols: int = 10):
    return [
        {
            "border":        _copy(ws.cell(row=row, column=c).border),
            "alignment":     _copy(ws.cell(row=row, column=c).alignment),
            "font":          _copy(ws.cell(row=row, column=c).font),
            "number_format": ws.cell(row=row, column=c).number_format,
        }
        for c in range(1, cols + 1)
    ]


def apply_row_style(ws, row: int, style: list):
    for ci, fmt in enumerate(style, 1):
        c = ws.cell(row=row, column=ci)
        c.border        = fmt["border"]
        c.alignment     = fmt["alignment"]
        c.font          = fmt["font"]
        c.number_format = fmt["number_format"]


def adjust_item_rows(ws, n_items: int) -> int:
    """Insert (N-5) or delete (5-N) item rows; shift footer merges accordingly.

    Returns `delta = n_items - TEMPLATE_SLOTS`. Caller offsets every footer row
    address by this value.
    """
    delta = n_items - TEMPLATE_SLOTS

    if delta > 0:
        style = capture_row_style(ws, ROW_ITEM_START, cols=10)
        ranges = capture_and_unmerge(ws, ROW_TOTALS)
        ws.insert_rows(ROW_TOTALS, delta)
        remerge_shifted(ws, ranges, delta)
        for nr in range(ROW_TOTALS, ROW_TOTALS + delta):
            apply_row_style(ws, nr, style)
    elif delta < 0:
        drop = -delta
        first_drop = ROW_ITEM_START + n_items
        ranges = capture_and_unmerge(ws, ROW_TOTALS)
        ws.delete_rows(first_drop, drop)
        remerge_shifted(ws, ranges, delta)

    return delta
