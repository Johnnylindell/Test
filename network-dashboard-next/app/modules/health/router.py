from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v2/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, object]:
    return {"ok": True, "status": "live"}


@router.get("/ready")
def ready(request: Request) -> dict[str, object]:
    database = request.app.state.database
    integrity = database.integrity_check()
    return {
        "ok": integrity == "ok",
        "status": "ready" if integrity == "ok" else "degraded",
        "database": {"integrity": integrity, "path": str(database.path)},
        "legacy_origin": request.app.state.settings.legacy_origin,
        "selected_port": request.app.state.selected_port,
    }
