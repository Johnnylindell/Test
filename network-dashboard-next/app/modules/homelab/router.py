from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_admin
from app.auth.service import Identity
from app.modules.homelab.repository import HomelabRepository

router = APIRouter(prefix="/api/v2/admin/homelab", tags=["admin-homelab"])


@router.get("/overview")
def overview(request: Request, _: Identity = Depends(require_admin)) -> dict:
    repository = HomelabRepository(request.app.state.database)
    return repository.overview()


@router.get("/system")
def system(request: Request, _: Identity = Depends(require_admin)) -> dict:
    repository = HomelabRepository(request.app.state.database)
    return {"ok": True, "system": repository.system_counts(), "live_probes_performed": False}
