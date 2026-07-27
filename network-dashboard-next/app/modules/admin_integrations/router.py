from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity

router = APIRouter(prefix="/api/v2/admin/integrations", tags=["admin-integrations"])


class HomeAssistantCommand(BaseModel):
    entity_id: str = Field(min_length=3, max_length=180, pattern=r"^[a-z_]+\.[A-Za-z0-9_]+$")
    service: str = Field(min_length=3, max_length=40)


def _require_external(request: Request) -> None:
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Externa sidoeffekter är avstängda",
        )


@router.get("/overview")
def overview(request: Request, _: Identity = Depends(require_admin)) -> dict:
    ha = request.app.state.home_assistant.status()
    return {
        "ok": True,
        "items": [
            {"id": "home-assistant", "configured": ha["configured"], "ok": ha["ok"], "state": ha["state"]},
            {"id": "tailscale", "configured": None, "ok": None, "state": "not_checked"},
        ],
        "live_probes": {"home_assistant": True, "tailscale": False},
        "sensitive_values_exposed": False,
    }


@router.get("/home-assistant/status")
def home_assistant_status(
    request: Request,
    fresh: bool = Query(default=False),
    _: Identity = Depends(require_admin),
) -> dict:
    return request.app.state.home_assistant.status(fresh=fresh)


@router.get("/home-assistant/entities")
def home_assistant_entities(
    request: Request,
    fresh: bool = Query(default=False),
    _: Identity = Depends(require_admin),
) -> dict:
    return request.app.state.home_assistant.entities(fresh=fresh)


@router.post("/home-assistant/service", dependencies=[Depends(require_same_origin)])
def home_assistant_service(
    payload: HomeAssistantCommand,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    _require_external(request)
    try:
        result = request.app.state.home_assistant.call_service(payload.entity_id, payload.service)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Home Assistant svarar inte")
    return result


@router.get("/tailscale/status")
def tailscale_status(
    request: Request,
    fresh: bool = Query(default=False),
    _: Identity = Depends(require_admin),
) -> dict:
    return request.app.state.tailscale.status(fresh=fresh)
