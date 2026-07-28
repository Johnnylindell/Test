from __future__ import annotations

import html

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.dependencies import current_identity, get_auth_service
from app.auth.service import AuthService, Identity

router = APIRouter(tags=["auth"])


def _login_page(error: str = "") -> str:
    message = f'<p class="error" role="alert">{html.escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#174c39">
  <title>Admin · Lindells app</title>
  <link rel="icon" href="/app-icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/assets/entry.css">
</head>
<body>
  <main class="entry">
    <div class="entry__brand"><span class="entry__mark">L</span><div><h1>Lindells app</h1><p>Skyddad administration</p></div></div>
    <section class="entry__card">
      <header class="entry__hero"><p>Administration</p><h2>Logga in säkert</h2><small>Sessionen är tidsbegränsad och alla känsliga åtgärder kräver adminbehörighet.</small></header>
      {message}
      <form class="entry__form" method="post" action="/login">
        <input type="hidden" name="username" value="admin">
        <label class="entry__field">Lösenord
          <input type="password" name="password" autocomplete="current-password" required autofocus>
        </label>
        <button class="entry__button" type="submit">Logga in</button>
      </form>
      <footer class="entry__footer"><span>För många felaktiga försök spärras tillfälligt.</span><a class="entry__link" href="/choose-user">Till familjeprofiler</a></footer>
    </section>
  </main>
</body>
</html>"""


def _source(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return (forwarded or (request.client.host if request.client else "unknown"))[:200]


@router.get("/login", response_class=HTMLResponse)
def login_page(identity: Identity = Depends(current_identity)) -> HTMLResponse | RedirectResponse:
    if identity.admin:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_login_page())


@router.post("/login")
def login(
    request: Request,
    username: str = Form("admin"),
    password: str = Form(""),
    auth: AuthService = Depends(get_auth_service),
) -> HTMLResponse | RedirectResponse:
    source = _source(request)
    allowed, retry_after = auth.login_allowed(source)
    if not allowed:
        return HTMLResponse(
            _login_page(f"För många försök. Försök igen om {retry_after} sekunder."),
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
    success = username.strip().lower() == "admin" and auth.verify_admin_password(password)
    auth.record_login_attempt(source, success)
    if not success:
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
        "sections": sorted(identity.sections),
        "readonly": identity.readonly,
        "controls_require_admin": True,
        "login_url": "/login",
        "logout_url": "/logout",
    }
