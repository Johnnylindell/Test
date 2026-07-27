from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.dependencies import current_identity, get_auth_service
from app.auth.service import AuthService, Identity

router = APIRouter(tags=["auth"])


def _login_page(error: str = "") -> str:
    message = f'<p class="error">{error}</p>' if error else ""
    return f"""<!doctype html><html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin</title></head>
<body><main><h1>Admin</h1>{message}<form method="post" action="/login">
<input type="hidden" name="username" value="admin"><label>Lösenord
<input type="password" name="password" autocomplete="current-password" autofocus></label>
<button type="submit">Logga in</button></form><p><a href="/">Tillbaka</a></p></main></body></html>"""


@router.get("/login", response_class=HTMLResponse)
def login_page(identity: Identity = Depends(current_identity)) -> HTMLResponse | RedirectResponse:
    if identity.admin:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_login_page())


@router.post("/login")
def login(
    username: str = Form("admin"),
    password: str = Form(""),
    auth: AuthService = Depends(get_auth_service),
) -> HTMLResponse | RedirectResponse:
    if username.strip().lower() != "admin" or not auth.verify_admin_password(password):
        return HTMLResponse(_login_page("Fel lösenord"), status_code=401)
    token = auth.create_admin_session()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "homelab_session",
        token,
        max_age=auth.settings.admin_session_seconds,
        httponly=True,
        secure=auth.settings.cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout(request: Request, auth: AuthService = Depends(get_auth_service)) -> RedirectResponse:
    auth.revoke_admin_session(request.cookies.get("homelab_session"))
    response = RedirectResponse("/choose-user", status_code=303)
    response.delete_cookie("homelab_session")
    return response


@router.post("/api/select-user")
def select_user(user: str = Form("guest"), auth: AuthService = Depends(get_auth_service)) -> RedirectResponse:
    selected = auth.normalize_family_user(user)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "homelab_user",
        selected,
        max_age=2_592_000,
        secure=auth.settings.cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        "homelab_identity",
        "selected",
        max_age=2_592_000,
        secure=auth.settings.cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/api/access-control")
def access_control(identity: Identity = Depends(current_identity)) -> dict[str, object]:
    return {
        "admin": identity.admin,
        "user": identity.user,
        "controls_require_admin": True,
        "login_url": "/login",
        "logout_url": "/logout",
    }
