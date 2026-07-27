from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

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
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Externa sidoeffekter är avstängda",
        )


def _redirect_uri(request: Request) -> str:
    return str(request.url_for("google_oauth_callback"))


@router.get("/overview")
def overview(
    request: Request,
    start: str = "",
    end: str = "",
    calendar_id: str = "primary",
    fresh: bool = False,
    _: Identity = Depends(require_login),
) -> dict:
    now = datetime.now(timezone.utc)
    start_dt = _parse(start, now)
    end_dt = _parse(end, start_dt + timedelta(days=7))
    google = adapter(request)
    auth = google.status()
    calendars = google.calendars(fresh=fresh) if auth.get("authenticated") else {"ok": False, "calendars": [], "count": 0}
    return {
        "ok": True,
        "auth": auth,
        "calendars": calendars,
        "selected_calendar_id": calendar_id,
        "calendar": google.events(start_dt, end_dt, calendar_id=calendar_id, fresh=fresh),
        "tasks": google.tasks(fresh=fresh),
    }


@router.get("/auth-status")
def auth_status(request: Request, _: Identity = Depends(require_admin)) -> dict:
    return {"ok": True, "auth": adapter(request).status()}


@router.post("/oauth/start", dependencies=[Depends(require_same_origin)])
def google_oauth_start(
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    _require_external(request)
    result = adapter(request).begin_oauth(_redirect_uri(request))
    nonce = secrets.token_urlsafe(24)
    request.app.state.database.set_json_state(
        f"google_oauth:{nonce}",
        {
            "state": result["state"],
            "code_verifier": result.get("code_verifier", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"ok": True, "authorization_url": result["authorization_url"], "nonce": nonce}


@router.get("/oauth/callback", name="google_oauth_callback")
def google_oauth_callback(
    request: Request,
    state: str = "",
    nonce: str = "",
    error: str = "",
) -> RedirectResponse:
    _require_external(request)
    if error:
        return RedirectResponse(url=f"/preview-v2#calendar?oauth=error", status_code=303)
    stored = request.app.state.database.get_json_state(f"google_oauth:{nonce}", {})
    request.app.state.database.set_json_state(f"google_oauth:{nonce}", {})
    if not isinstance(stored, dict) or not stored.get("state") or not secrets.compare_digest(str(stored.get("state")), state):
        raise HTTPException(status_code=400, detail="Ogiltigt eller förbrukat OAuth-state")
    try:
        created = datetime.fromisoformat(str(stored.get("created_at") or "").replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Ogiltigt OAuth-state") from exc
    if datetime.now(timezone.utc) - created.astimezone(timezone.utc) > timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="OAuth-state har gått ut")
    adapter(request).complete_oauth(
        authorization_response=str(request.url),
        redirect_uri=_redirect_uri(request),
        state=state,
        code_verifier=str(stored.get("code_verifier") or ""),
    )
    return RedirectResponse(url="/preview-v2#calendar", status_code=303)


@router.delete("/oauth", dependencies=[Depends(require_same_origin)])
def google_oauth_disconnect(
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    _require_external(request)
    return adapter(request).disconnect()


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
