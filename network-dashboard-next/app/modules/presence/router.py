from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.presence.schemas import PresenceDeviceCreate, PresenceObservation
from app.modules.presence.service import PresenceService

router = APIRouter(prefix="/api/v2/presence", tags=["presence"])


def service(request: Request) -> PresenceService:
    secret = request.app.state.settings.presence_hash_secret
    if not secret:
        raise HTTPException(status_code=503, detail="Närvarohashning är inte konfigurerad")
    return PresenceService(request.app.state.database, secret)


@router.get("/overview")
def overview(
    _: Identity = Depends(require_login),
    presence: PresenceService = Depends(service),
) -> dict:
    return presence.overview()


@router.post("/devices", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def register_device(
    payload: PresenceDeviceCreate,
    _: Identity = Depends(require_admin),
    presence: PresenceService = Depends(service),
) -> dict:
    try:
        return presence.register(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/devices/{device_id}", dependencies=[Depends(require_same_origin)])
def remove_device(
    device_id: str,
    _: Identity = Depends(require_admin),
    presence: PresenceService = Depends(service),
) -> dict:
    if not presence.remove(device_id):
        raise HTTPException(status_code=404, detail="Närvaroenheten hittades inte")
    return {"ok": True, "deleted": device_id}


@router.post("/observations")
def observe(
    payload: PresenceObservation,
    request: Request,
    x_presence_token: str = Header(default=""),
    presence: PresenceService = Depends(service),
) -> dict:
    expected = request.app.state.settings.presence_ingest_token
    if not expected or not hmac.compare_digest(x_presence_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ogiltig närvarotoken")
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Närvaroingest är avstängd i parallelläge")
    cooldown = int(request.app.state.database.get_setting("arrival_alert_cooldown_minutes", 15) or 15)
    try:
        result = presence.observe(**payload.model_dump(), cooldown_minutes=cooldown)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    alert = result.get("alert")
    if alert:
        request.app.state.notification_delivery.deliver(
            title="Lindells app",
            message=str(alert.get("message") or ""),
            target="family",
            severity="normal",
            send_push=True,
            send_discord=False,
        )
    return result
