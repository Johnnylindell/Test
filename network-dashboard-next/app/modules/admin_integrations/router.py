from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity

router = APIRouter(prefix="/api/v2/admin/integrations", tags=["admin-integrations"])
_MAX_GOOGLE_FILE = 2 * 1024 * 1024


class HomeAssistantCommand(BaseModel):
    entity_id: str = Field(min_length=3, max_length=180, pattern=r"^[a-z_]+\.[A-Za-z0-9_]+$")
    service: str = Field(min_length=3, max_length=40)


class IntegrationValueUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=10_000)
    confirm: bool = False


class LegacyAdoptRequest(BaseModel):
    overwrite: bool = False
    confirm: bool = False


class VapidGenerateRequest(BaseModel):
    subject: str = Field(default="mailto:admin@localhost", min_length=8, max_length=500)
    replace: bool = False
    confirm: bool = False


def _require_external(request: Request) -> None:
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Externa sidoeffekter är avstängda",
        )


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


async def _json_upload(file: UploadFile) -> dict[str, Any]:
    data = await file.read(_MAX_GOOGLE_FILE + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filen är tom")
    if len(data) > _MAX_GOOGLE_FILE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Filen är för stor")
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filen är inte giltig JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON-roten måste vara ett objekt")
    return payload


def _validate_google_client(payload: dict[str, Any]) -> dict[str, Any]:
    client = payload.get("installed") or payload.get("web")
    if not isinstance(client, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google-filen måste innehålla installed eller web",
        )
    required = ("client_id", "client_secret", "auth_uri", "token_uri")
    if any(not str(client.get(key) or "").strip() for key in required):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google client-filen saknar obligatoriska fält")
    redirect_uris = client.get("redirect_uris")
    if redirect_uris is not None and not isinstance(redirect_uris, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uris måste vara en lista")
    return payload


def _validate_google_token(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("client_id", "client_secret", "refresh_token")
    if any(not str(payload.get(key) or "").strip() for key in required):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google-tokenfilen saknar client_id, client_secret eller refresh_token",
        )
    payload.setdefault("type", "authorized_user")
    return payload


@router.get("/overview")
def overview(request: Request, _: Identity = Depends(require_admin)) -> dict:
    ha = request.app.state.home_assistant.status()
    google = request.app.state.google_workspace.status()
    credentials = request.app.state.integration_config.overview()
    return {
        "ok": True,
        "items": [
            {"id": "home-assistant", "configured": ha["configured"], "ok": ha["ok"], "state": ha["state"]},
            {
                "id": "google-workspace",
                "configured": google["configured"],
                "ok": google["authenticated"],
                "state": google["status"],
            },
            {"id": "tailscale", "configured": None, "ok": None, "state": "not_checked"},
        ],
        "credential_summary": {
            "configured": credentials["configured"],
            "missing": credentials["missing"],
        },
        "live_probes": {"home_assistant": True, "tailscale": False},
        "sensitive_values_exposed": False,
    }


@router.get("/configuration")
def configuration(request: Request, _: Identity = Depends(require_admin)) -> dict:
    google = request.app.state.google_workspace.status()
    result = request.app.state.integration_config.overview()
    return {
        **result,
        "google": {
            "client_configured": google["client_configured"],
            "token_configured": google["configured"],
            "authenticated": google["authenticated"],
            "status": google["status"],
            "token_refresh_persisted": google["token_refresh_persisted"],
        },
    }


@router.put("/configuration/{key}", dependencies=[Depends(require_same_origin)])
def update_configuration(
    key: str,
    payload: IntegrationValueUpdate,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ändringen måste bekräftas")
    try:
        variable = request.app.state.integration_config.set(key, payload.value)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.app.state.cache.invalidate("ha:")
    return {"ok": True, "variable": variable, "sensitive_values_exposed": False}


@router.delete("/configuration/{key}", dependencies=[Depends(require_same_origin)])
def clear_configuration(
    key: str,
    request: Request,
    confirm: bool = Query(False),
    _: Identity = Depends(require_admin),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rensningen måste bekräftas")
    try:
        variable = request.app.state.integration_config.clear(key)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    request.app.state.cache.invalidate("ha:")
    return {"ok": True, "variable": variable, "sensitive_values_exposed": False}


@router.post("/configuration/adopt-legacy", dependencies=[Depends(require_same_origin)])
def adopt_legacy(
    payload: LegacyAdoptRequest,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Importen måste bekräftas")
    try:
        result = request.app.state.integration_config.adopt_legacy(overwrite=payload.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.app.state.cache.invalidate("ha:")
    return result


@router.post("/vapid/generate", dependencies=[Depends(require_same_origin)])
def generate_vapid(
    payload: VapidGenerateRequest,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nyckelgenereringen måste bekräftas")
    config = request.app.state.integration_config
    existing = config.get("vapid_private_key") or config.get("vapid_public_key")
    if existing and not payload.replace:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="VAPID-nycklar finns redan; välj replace för att ersätta dem",
        )
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_key = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
    try:
        variables = config.set_many({
            "vapid_subject": payload.subject,
            "vapid_private_key": private_pem,
            "vapid_public_key": public_key,
        })
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "ok": True,
        "variables": variables,
        "sensitive_values_exposed": False,
    }


@router.post("/google/client-secret", dependencies=[Depends(require_same_origin)])
async def upload_google_client_secret(
    request: Request,
    file: UploadFile = File(...),
    _: Identity = Depends(require_admin),
) -> dict:
    payload = _validate_google_client(await _json_upload(file))
    _write_private_json(request.app.state.settings.google_client_secrets_path, payload)
    return {"ok": True, "client_configured": True, "sensitive_values_exposed": False}


@router.post("/google/token", dependencies=[Depends(require_same_origin)])
async def upload_google_token(
    request: Request,
    file: UploadFile = File(...),
    _: Identity = Depends(require_admin),
) -> dict:
    payload = _validate_google_token(await _json_upload(file))
    _write_private_json(request.app.state.settings.google_token_path, payload)
    request.app.state.cache.invalidate("google:")
    return {"ok": True, "token_configured": True, "sensitive_values_exposed": False}


@router.delete("/google/{kind}", dependencies=[Depends(require_same_origin)])
def delete_google_file(
    kind: str,
    request: Request,
    confirm: bool = Query(False),
    _: Identity = Depends(require_admin),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Raderingen måste bekräftas")
    paths = {
        "token": request.app.state.settings.google_token_path,
        "client-secret": request.app.state.settings.google_client_secrets_path,
    }
    if kind not in paths:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Okänd Google-fil")
    path = Path(paths[kind]).expanduser()
    removed = path.is_file()
    path.unlink(missing_ok=True)
    request.app.state.cache.invalidate("google:")
    return {"ok": True, "removed": removed, "sensitive_values_exposed": False}


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
