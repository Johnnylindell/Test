from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.calendar.schemas import (
    CalendarEventCreate,
    GoogleTaskCompletion,
    GoogleTaskCreate,
    GoogleTaskDelete,
    GoogleTaskUpdate,
)

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


def _require_external(request: Request) -> None:
    if not request.app.state.settings.external_side_effects:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Externa sidoeffekter är avstängda",
        )


@router.get("/overview")
def overview(
    request: Request,
    start: str = "",
    end: str = "",
    fresh: bool = False,
    _: Identity = Depends(require_login),
) -> dict:
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
def create_event(
    payload: CalendarEventCreate,
    request: Request,
    _: Identity = Depends(require_login),
) -> dict:
    _require_external(request)
    return adapter(request).create_event(payload.model_dump())


@router.post("/tasks", dependencies=[Depends(require_same_origin)])
def create_task(
    payload: GoogleTaskCreate,
    request: Request,
    _: Identity = Depends(require_login),
) -> dict:
    _require_external(request)
    return adapter(request).create_task(payload.model_dump())


@router.patch("/tasks/{tasklist_id}/{task_id}", dependencies=[Depends(require_same_origin)])
def update_task(
    tasklist_id: str,
    task_id: str,
    payload: GoogleTaskUpdate,
    request: Request,
    _: Identity = Depends(require_login),
) -> dict:
    _require_external(request)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inga ändringar angavs")
    return adapter(request).update_task(tasklist_id, task_id, changes)


@router.patch(
    "/tasks/{tasklist_id}/{task_id}/completion",
    dependencies=[Depends(require_same_origin)],
)
def set_task_completion(
    tasklist_id: str,
    task_id: str,
    payload: GoogleTaskCompletion,
    request: Request,
    _: Identity = Depends(require_login),
) -> dict:
    _require_external(request)
    return adapter(request).set_task_completed(tasklist_id, task_id, payload.completed)


@router.delete("/tasks/{tasklist_id}/{task_id}", dependencies=[Depends(require_same_origin)])
def delete_task(
    tasklist_id: str,
    task_id: str,
    payload: GoogleTaskDelete,
    request: Request,
    _: Identity = Depends(require_login),
) -> dict:
    _require_external(request)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Radering måste bekräftas")
    return adapter(request).delete_task(tasklist_id, task_id)
