from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.budget.excel import BudgetExcelWorkbook
from app.modules.budget.repository import BudgetRepository
from app.modules.budget.schemas import (
    BudgetEntryCreate,
    BudgetEntryDelete,
    BudgetEntryUpdate,
    BudgetImportRequest,
    BudgetSyncSettings,
)
from app.modules.budget.service import BudgetService

router = APIRouter(prefix="/api/v2/budget", tags=["budget"])


def repository(request: Request) -> BudgetRepository:
    return BudgetRepository(request.app.state.database)


def service(repo: BudgetRepository = Depends(repository)) -> BudgetService:
    return BudgetService(repo)


@router.get("/overview")
def overview(
    sheet: str = Query(default="", max_length=80),
    identity: Identity = Depends(require_login),
    budget: BudgetService = Depends(service),
) -> dict:
    return budget.overview(identity, sheet)


@router.get("/year")
def year_summary(
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    return repo.year_summary()


@router.get("/export")
def export_budget(
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    return {"ok": True, "payload": repo.export_payload()}


@router.get("/excel/export")
def export_excel(
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> Response:
    budget.require_adult(identity)
    data = BudgetExcelWorkbook.export(repo.export_payload())
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="lindells-budget.xlsx"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/excel/preview", dependencies=[Depends(require_same_origin)])
async def preview_excel_import(
    file: UploadFile = File(...),
    identity: Identity = Depends(require_login),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    try:
        parsed = BudgetExcelWorkbook.parse(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "ok": True,
        "summary": parsed["summary"],
        "format": parsed["format"],
        "saved": False,
    }


@router.post("/excel/import", dependencies=[Depends(require_same_origin)])
async def import_excel(
    file: UploadFile = File(...),
    replace: bool = Form(False),
    confirm: bool = Form(False),
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    if not confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Excel-importen måste bekräftas")
    try:
        parsed = BudgetExcelWorkbook.parse(await file.read())
        result = repo.import_payload(parsed, replace=replace)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {**result, "summary": parsed["summary"]}


@router.post("/import", dependencies=[Depends(require_same_origin)])
def import_budget(
    payload: BudgetImportRequest,
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    if payload.replace and not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ersättande import måste bekräftas",
        )
    return repo.import_payload(payload.payload, replace=payload.replace)


@router.get("/sync")
def sync_status(
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    return repo.sync_status()


@router.put("/sync", dependencies=[Depends(require_same_origin)])
def update_sync(
    payload: BudgetSyncSettings,
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    return repo.update_sync_settings(payload.model_dump())


@router.post("/entries", dependencies=[Depends(require_same_origin)])
def add_entry(
    payload: BudgetEntryCreate,
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    repo.add_entry(payload.model_dump())
    return budget.overview(identity, payload.sheet)


@router.patch("/entries/{entry_id}", dependencies=[Depends(require_same_origin)])
def update_entry(
    entry_id: str,
    payload: BudgetEntryUpdate,
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    try:
        repo.update_entry(entry_id, payload.field, payload.value)
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ogiltigt budget-ID") from None
    return {"ok": True}


@router.delete("/entries/{entry_id}", dependencies=[Depends(require_same_origin)])
def delete_entry(
    entry_id: str,
    payload: BudgetEntryDelete,
    identity: Identity = Depends(require_login),
    repo: BudgetRepository = Depends(repository),
    budget: BudgetService = Depends(service),
) -> dict:
    budget.require_adult(identity)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Radering måste bekräftas")
    try:
        repo.delete_entry(entry_id)
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ogiltigt budget-ID") from None
    return {"ok": True}
