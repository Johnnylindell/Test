from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.auth.dependencies import current_identity, require_admin
from app.auth.service import Identity

router = APIRouter(tags=["web"])


def _safe_file(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        raise HTTPException(status_code=404)
    if not candidate.is_file():
        raise HTTPException(status_code=404)
    return candidate


@router.get("/choose-user", response_class=HTMLResponse)
def choose_user() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Välj användare</title></head>
<body><main><h1>Vem är du?</h1><form method="post" action="/api/select-user">
<button name="user" value="johnny">Johnny</button><button name="user" value="kristina">Kristina</button>
<button name="user" value="viktor">Viktor</button><button name="user" value="guest">Gäst</button>
</form><p><a href="/login">Admin</a></p></main></body></html>"""
    )


@router.get("/")
def live_index(request: Request, identity: Identity = Depends(current_identity)) -> FileResponse | RedirectResponse:
    if not request.cookies.get("homelab_user") and not identity.admin:
        return RedirectResponse("/choose-user", status_code=303)
    return FileResponse(_safe_file(request.app.state.settings.static_root / "live", "index.html"))


@router.get("/live/{path:path}")
def live_static(path: str, request: Request, _: Identity = Depends(current_identity)) -> FileResponse:
    return FileResponse(_safe_file(request.app.state.settings.static_root / "live", path))


@router.get("/preview-v2")
def v2_index(request: Request, _: Identity = Depends(require_admin)) -> FileResponse:
    return FileResponse(_safe_file(request.app.state.settings.static_root / "v2", "index.html"))


@router.get("/preview-v2/{path:path}")
def v2_static(path: str, request: Request, _: Identity = Depends(require_admin)) -> FileResponse:
    return FileResponse(_safe_file(request.app.state.settings.static_root / "v2", path))
