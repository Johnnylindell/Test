from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.banking.importer import parse_statement
from app.modules.banking.repository import BankingRepository
from app.modules.banking.schemas import BankRuleCreate

router = APIRouter(prefix="/api/v2/banking", tags=["banking"])


def repository(request: Request) -> BankingRepository:
    return BankingRepository(request.app.state.database)


def require_adult(identity: Identity = Depends(require_login)) -> Identity:
    if not identity.admin and identity.user not in {"johnny", "kristina"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vuxenprofil krävs för bankdata")
    return identity


async def _parse(file: UploadFile) -> dict:
    try:
        return parse_statement(await file.read(), file.filename or "statement")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/overview")
def overview(
    _: Identity = Depends(require_adult),
    repo: BankingRepository = Depends(repository),
) -> dict:
    return repo.overview()


@router.post("/import/preview", dependencies=[Depends(require_same_origin)])
async def preview_import(
    file: UploadFile = File(...),
    _: Identity = Depends(require_adult),
    repo: BankingRepository = Depends(repository),
) -> dict:
    return repo.preview(await _parse(file))


@router.post("/import", dependencies=[Depends(require_same_origin)])
async def import_statement(
    file: UploadFile = File(...),
    confirm: bool = Form(False),
    identity: Identity = Depends(require_adult),
    repo: BankingRepository = Depends(repository),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bankimporten måste bekräftas")
    try:
        return repo.import_parsed(await _parse(file), identity.user)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/rules", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_rule(
    payload: BankRuleCreate,
    _: Identity = Depends(require_adult),
    repo: BankingRepository = Depends(repository),
) -> dict:
    try:
        rule_id = repo.save_rule(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "id": rule_id, "rules": repo.rules()}


@router.delete("/rules/{rule_id}", dependencies=[Depends(require_same_origin)])
def delete_rule(
    rule_id: str,
    _: Identity = Depends(require_adult),
    repo: BankingRepository = Depends(repository),
) -> dict:
    if not repo.delete_rule(rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategoriregeln hittades inte")
    return {"ok": True, "rules": repo.rules()}
