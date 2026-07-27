from __future__ import annotations

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


def require_admin(identity: Identity = Depends(current_identity)) -> Identity:
    if not identity.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin krävs")
    return identity
