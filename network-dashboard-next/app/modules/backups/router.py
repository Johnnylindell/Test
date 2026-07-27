from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity
from app.modules.admin_security.repository import AdminSecurityRepository
from app.modules.backups.schemas import BackupCreate, BackupRestore
from app.modules.backups.service import BackupService

router = APIRouter(prefix="/api/v2/admin/backups", tags=["admin-backups"])


def service(request: Request) -> BackupService:
    backup_dir = Path.home() / ".local" / "share" / "network-dashboard-next" / "backups"
    return BackupService(request.app.state.database.path, backup_dir)


def audit(request: Request) -> AdminSecurityRepository:
    return AdminSecurityRepository(request.app.state.database)


@router.get("")
def list_backups(
    _: Identity = Depends(require_admin),
    backups: BackupService = Depends(service),
) -> dict:
    return {"ok": True, "backups": backups.list()}


@router.post("", dependencies=[Depends(require_same_origin)])
def create_backup(
    payload: BackupCreate,
    request: Request,
    identity: Identity = Depends(require_admin),
    backups: BackupService = Depends(service),
    security: AdminSecurityRepository = Depends(audit),
) -> dict:
    result = backups.create(payload.label)
    security.audit(identity.user, "backup.create", result["name"], {"size_bytes": result["size_bytes"]})
    return {"ok": True, "backup": result}


@router.get("/{name}/verify")
def verify_backup(
    name: str,
    _: Identity = Depends(require_admin),
    backups: BackupService = Depends(service),
) -> dict:
    try:
        return backups.verify(name)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{name}", dependencies=[Depends(require_same_origin)])
def delete_backup(
    name: str,
    identity: Identity = Depends(require_admin),
    backups: BackupService = Depends(service),
    security: AdminSecurityRepository = Depends(audit),
) -> dict:
    try:
        deleted = backups.delete(name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backupen hittades inte")
    security.audit(identity.user, "backup.delete", name)
    return {"ok": True, "deleted": name}


@router.post("/{name}/restore", dependencies=[Depends(require_same_origin)])
def restore_backup(
    name: str,
    payload: BackupRestore,
    request: Request,
    identity: Identity = Depends(require_admin),
    backups: BackupService = Depends(service),
    security: AdminSecurityRepository = Depends(audit),
) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Återställning måste bekräftas")
    if request.app.state.settings.read_only:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Skrivskyddat parallelläge")
    try:
        result = backups.restore(name)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    security.audit(identity.user, "backup.restore", name, {"safety_backup": result["safety_backup"]["name"]})
    return result
