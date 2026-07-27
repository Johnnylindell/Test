from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import get_auth_service, require_admin, require_same_origin
from app.auth.service import AuthService, Identity
from app.modules.admin_security.repository import AdminSecurityRepository
from app.modules.admin_security.schemas import AccessProfileUpdate, PasswordChange, RevokeSessions

router = APIRouter(prefix="/api/v2/admin/security", tags=["admin-security"])


def repository(request: Request) -> AdminSecurityRepository:
    return AdminSecurityRepository(request.app.state.database)


@router.get("/overview")
def overview(
    request: Request,
    _: Identity = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
    repo: AdminSecurityRepository = Depends(repository),
) -> dict:
    current = request.cookies.get("homelab_session")
    sessions = auth.sessions()
    for row in sessions:
        row["current"] = bool(current and str(row["token_hint"]).startswith(current[:6]))
    return {
        "ok": True,
        "access": repo.access_profiles(),
        "sessions": sessions,
        "audit": repo.audit_log(100),
        "read_only": request.app.state.settings.read_only,
        "external_side_effects": request.app.state.settings.external_side_effects,
        "legacy_writes": request.app.state.settings.allow_legacy_writes,
    }


@router.put("/password", dependencies=[Depends(require_same_origin)])
def change_password(
    payload: PasswordChange,
    _: Identity = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
    repo: AdminSecurityRepository = Depends(repository),
) -> dict:
    if not auth.verify_admin_password(payload.current_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nuvarande lösenord är fel")
    auth.set_admin_password(payload.new_password)
    repo.audit("admin", "password_changed")
    return {"ok": True}


@router.put("/access", dependencies=[Depends(require_same_origin)])
def update_access(
    payload: AccessProfileUpdate,
    _: Identity = Depends(require_admin),
    repo: AdminSecurityRepository = Depends(repository),
) -> dict:
    try:
        access = repo.set_access_profile(payload.user, payload.sections, payload.readonly)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repo.audit("admin", "access_profile_updated", payload.user, {"sections": payload.sections, "readonly": payload.readonly})
    return {"ok": True, "access": access}


@router.post("/sessions/revoke", dependencies=[Depends(require_same_origin)])
def revoke_sessions(
    payload: RevokeSessions,
    request: Request,
    _: Identity = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
    repo: AdminSecurityRepository = Depends(repository),
) -> dict:
    current = request.cookies.get("homelab_session") if payload.keep_current else None
    revoked = auth.revoke_all_sessions(current)
    repo.audit("admin", "sessions_revoked", detail={"count": revoked, "kept_current": payload.keep_current})
    return {"ok": True, "revoked": revoked}


@router.get("/audit")
def audit(limit: int = 200, _: Identity = Depends(require_admin), repo: AdminSecurityRepository = Depends(repository)) -> dict:
    return {"ok": True, "entries": repo.audit_log(limit)}
