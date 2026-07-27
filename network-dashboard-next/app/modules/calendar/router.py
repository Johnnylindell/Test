from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import require_admin, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.calendar.schemas import CalendarEventCreate, GoogleTaskCreate

router = APIRouter(prefix="/api/v2/calendar", tags=["calendar"])


def adapter(request: Request):
    return request.app.state.google_workspace


def _parse(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    raw = value.strip()
    if len(raw) == 10:
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)


@router.get("/overview")
def overview(start: str = "", end: str = "", fresh: bool = False, request: Request = None, _: Identity = Depends(require_login)) -> dict:
    now = datetime.now(timezone.utc)
    start_dt = _parse(start, now)
    end_dt = _parse(end, start_dt + timedelta(days=7))
    google = adapter(request)
    return {
        "ok": True,
        "auth": google.status(),
        "calendar": google.events(start_dt, end_dt, fresh=fresh),
        "tasks": google.tasks(fresh=fresh),
    }


@router.get("/auth-status")
def auth_status(request: Request, _: Identity = Depends(require_admin)) -> dict:
    return {"ok": True, "auth": adapter(request).status()}


@router.post("/events", dependencies=[Depends(require_same_origin)])
def create_event(payload: CalendarEventCreate, request: Request, _: Identity = Depends(require_login)) -> dict:
    if not request.app.state.settings.external_side_effects:
        raise HTTPException(status_code=423, detail="Externa sidoeffekter är avstängda")
    return adapter(request).create_event(payload.model_dump())


@router.post("/tasks", dependencies=[Depends(require_same_origin)])
def create_task(payload: GoogleTaskCreate, request: Request, _: Identity = Depends(require_login)) -> dict:
    if not request.app.state.settings.external_side_effects:
        raise HTTPException(status_code=423, detail="Externa sidoeffekter är avstängda")
    return adapter(request).create_task(payload.model_dump())
