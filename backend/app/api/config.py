"""
Public configuration endpoint.

Exposes non-sensitive runtime flags (e.g. demo_mode) so the frontend
can adapt its UI without hard-coding environment assumptions.
"""

import os

from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["Config"])

_DEMO_MODE: bool = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")


@router.get("", summary="Runtime configuration flags")
def get_config():
    return {"demo_mode": _DEMO_MODE}
