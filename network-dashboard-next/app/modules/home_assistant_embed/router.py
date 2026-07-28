from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity

router = APIRouter(
    prefix="/api/v2/admin/home-assistant-embed",
    tags=["admin-home-assistant-embed"],
)


class EmbedSettingsUpdate(BaseModel):
    enabled: bool = False
    path: str = Field(default="/lovelace", min_length=1, max_length=500)
    confirm: bool = False


def _embed_path(value: str) -> str:
    path = str(value or "").strip()
    parsed = urlparse(path)
    if (
        not path.startswith("/")
        or path.startswith("//")
        or "\\" in path
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or any(part == ".." for part in parsed.path.split("/"))
    ):
        raise ValueError("Embed-sökvägen måste vara en säker relativ Home Assistant-sökväg")
    return parsed.path.rstrip("/") or "/"


def _overview(request: Request) -> dict:
    stored = request.app.state.database.get_json_state("home_assistant_embed", {})
    settings = stored if isinstance(stored, dict) else {}
    enabled = bool(settings.get("enabled"))
    try:
        path = _embed_path(str(settings.get("path") or "/lovelace"))
    except ValueError:
        path = "/lovelace"
        enabled = False

    base = request.app.state.integration_config.get("home_assistant_url").strip().rstrip("/")
    base_configured = bool(base)
    frame_url = ""
    error = ""
    if enabled and base_configured:
        try:
            validated = request.app.state.home_assistant._validated_base(base)
            frame_url = validated + path
        except ValueError as exc:
            error = str(exc)[:240]

    ready = bool(enabled and frame_url)
    return {
        "ok": True,
        "enabled": enabled,
        "path": path,
        "base_configured": base_configured,
        "ready": ready,
        "frame_url": frame_url,
        "error": error,
        "updated_at": str(settings.get("updated_at") or "")[:64],
        "policy": {
            "admin_only": True,
            "family_url_exposed": False,
            "access_token_exposed": False,
            "same_origin_settings_required": True,
            "sandboxed_preview": True,
        },
        "sensitive_values_exposed": False,
    }


@router.get("/overview")
def overview(request: Request, _: Identity = Depends(require_admin)) -> dict:
    return _overview(request)


@router.put("/settings", dependencies=[Depends(require_same_origin)])
def update_settings(
    payload: EmbedSettingsUpdate,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Embed-inställningen måste bekräftas")
    try:
        path = _embed_path(payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.app.state.database.set_json_state(
        "home_assistant_embed",
        {
            "enabled": bool(payload.enabled),
            "path": path,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return _overview(request)
