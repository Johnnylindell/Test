from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.auth.dependencies import current_identity, require_admin
from app.auth.service import Identity

router = APIRouter(tags=["web"])


CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _safe_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    if resolved_root not in candidate.parents and candidate != resolved_root:
        raise HTTPException(status_code=404)
    if not candidate.is_file():
        raise HTTPException(status_code=404)
    return candidate


def _asset_response(path: Path) -> FileResponse:
    response = FileResponse(path, media_type=CONTENT_TYPES.get(path.suffix.lower()))
    response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
    return response


@router.get("/choose-user")
def choose_user(request: Request) -> FileResponse:
    response = FileResponse(_safe_file(request.app.state.settings.static_root / "live", "choose-user.html"))
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/", response_model=None)
def live_index(request: Request, identity: Identity = Depends(current_identity)) -> FileResponse | RedirectResponse:
    if not request.cookies.get("homelab_user") and not identity.admin:
        return RedirectResponse("/choose-user", status_code=303)
    response = FileResponse(_safe_file(request.app.state.settings.static_root / "live", "index.html"))
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/manifest.webmanifest")
def manifest(request: Request, _: Identity = Depends(current_identity)) -> FileResponse:
    return _asset_response(_safe_file(request.app.state.settings.static_root / "live", "manifest.webmanifest"))


@router.get("/app-icon.svg")
def app_icon(request: Request, _: Identity = Depends(current_identity)) -> FileResponse:
    return _asset_response(_safe_file(request.app.state.settings.static_root / "live", "app-icon.svg"))


@router.get("/sw.js")
def service_worker(request: Request, _: Identity = Depends(current_identity)) -> FileResponse:
    response = FileResponse(
        _safe_file(request.app.state.settings.static_root / "live", "sw.js"),
        media_type="text/javascript; charset=utf-8",
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@router.get("/assets/{path:path}")
def shared_static(path: str, request: Request, _: Identity = Depends(current_identity)) -> Response:
    return _asset_response(_safe_file(request.app.state.settings.static_root / "shared", path))


@router.get("/live/{path:path}")
def live_static(path: str, request: Request, _: Identity = Depends(current_identity)) -> Response:
    return _asset_response(_safe_file(request.app.state.settings.static_root / "live", path))


@router.get("/preview-v2")
def v2_index(request: Request, _: Identity = Depends(require_admin)) -> FileResponse:
    response = FileResponse(_safe_file(request.app.state.settings.static_root / "v2", "index.html"))
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/preview-v2/{path:path}")
def v2_static(path: str, request: Request, _: Identity = Depends(require_admin)) -> Response:
    return _asset_response(_safe_file(request.app.state.settings.static_root / "v2", path))
