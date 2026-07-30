"""v1 Додаток-25 export shim.

The renderer now lives in `app.nakladna_common` (shared with the v2 custody
chain). This module re-exports it for the legacy v1 `documents` router.
"""
from app.nakladna_common import EXPORT_REQUIRED_SNAP, build_xlsx, has_snap

__all__ = ["EXPORT_REQUIRED_SNAP", "build_xlsx", "has_snap"]
