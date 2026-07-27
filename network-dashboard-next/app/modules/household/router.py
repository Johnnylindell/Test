from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.household.repository import HouseholdRepository
from app.modules.household.schemas import HouseholdItemCreate, HouseholdItemUpdate, HouseholdLogCreate, HouseholdPlaceUpsert

router = APIRouter(prefix="/api/v2/household", tags=["household"])


def repository(request: Request) -> HouseholdRepository:
    return HouseholdRepository(request.app.state.database)


@router.get("/overview")
def overview(q: str = "", repo: HouseholdRepository = Depends(repository), _: Identity = Depends(require_login)) -> dict:
    return repo.overview(q)


@router.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(payload: HouseholdItemCreate, repo: HouseholdRepository = Depends(repository), identity: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    return {"ok": True, "id": repo.add_item(payload.model_dump(), identity.user)}


@router.patch("/items/{item_id}")
def update_item(item_id: str, payload: HouseholdItemUpdate, repo: HouseholdRepository = Depends(repository), identity: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    try:
        repo.update_item(item_id, payload.model_dump(exclude_unset=True), identity.user)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/items/{item_id}")
def delete_item(item_id: str, repo: HouseholdRepository = Depends(repository), _: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    try:
        repo.delete_item(item_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/places")
def upsert_place(payload: HouseholdPlaceUpsert, repo: HouseholdRepository = Depends(repository), identity: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    return {"ok": True, "id": repo.upsert_place(payload.model_dump(), identity.user)}


@router.delete("/places")
def delete_place(path: str, repo: HouseholdRepository = Depends(repository), _: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    try:
        repo.delete_place(path)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/log", status_code=status.HTTP_201_CREATED)
def create_log(payload: HouseholdLogCreate, repo: HouseholdRepository = Depends(repository), identity: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    return {"ok": True, "id": repo.add_log(payload.model_dump(), identity.user)}


@router.delete("/log/{entry_id}")
def delete_log(entry_id: str, repo: HouseholdRepository = Depends(repository), _: Identity = Depends(require_login), __: None = Depends(require_same_origin)) -> dict:
    try:
        repo.delete_log(entry_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
