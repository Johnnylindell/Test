from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status

from app.auth.service import AuthService, Identity


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def current_identity(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> Identity:
    return auth.identity(
        request.cookies.get("homelab_session"),
        request.cookies.get("homelab_user"),
    )


def require_login(identity: Identity = Depends(current_identity)) -> Identity:
    if not identity.admin and not identity.selected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Välj användare först")
    return identity


def require_admin(identity: Identity = Depends(current_identity)) -> Identity:
    if not identity.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin krävs")
    return identity


def require_same_origin(request: Request) -> None:
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Same-origin krävs")
    parsed = urlparse(source)
    source_host = parsed.netloc.lower()
    request_host = (request.headers.get("host") or "").lower()
    if parsed.scheme not in {"http", "https"} or not source_host or source_host != request_host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ogiltigt ursprung")
