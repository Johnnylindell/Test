from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import (
    InventoryAdjustment,
    InventoryInboxPlacement,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryShelfCreate,
    InventorySuggestionShopping,
)

router = APIRouter(prefix="/api/v2/inventory", tags=["inventory"])


def repository(request: Request) -> InventoryRepository:
    return InventoryRepository(request.app.state.database)


def require_adult(identity: Identity = Depends(require_login)) -> Identity:
    if not identity.admin and identity.user not in {"johnny", "kristina"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Barnprofilen kan inte ändra förrådet")
    return identity


@router.get("/overview")
def overview(_: Identity = Depends(require_login), repo: InventoryRepository = Depends(repository)) -> dict:
    return repo.overview()


@router.post("/items", dependencies=[Depends(require_same_origin)])
def add_item(payload: InventoryItemCreate, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    item_id = repo.add(payload.model_dump())
    return {"ok": True, "item_id": item_id, "view": repo.overview()}


@router.patch("/items/{item_id}", dependencies=[Depends(require_same_origin)])
def update_item(item_id: str, payload: InventoryItemUpdate, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        repo.update(item_id, payload.model_dump(exclude_unset=True))
        return {"ok": True, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/items/{item_id}/quantity", dependencies=[Depends(require_same_origin)])
def adjust_quantity(item_id: str, payload: InventoryAdjustment, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        quantity = repo.adjust(item_id, payload.delta)
        return {"ok": True, "item_id": item_id, "quantity": quantity, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/items/{item_id}", dependencies=[Depends(require_same_origin)])
def delete_item(item_id: str, confirm: bool = False, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    if not confirm:
        raise HTTPException(status_code=400, detail="Radering måste bekräftas")
    try:
        repo.delete_item(item_id)
        return {"ok": True, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/shelves", dependencies=[Depends(require_same_origin)])
def add_shelf(payload: InventoryShelfCreate, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        return {"ok": True, "id": repo.add_shelf(payload.location, payload.name), "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/shelves/{shelf_id}", dependencies=[Depends(require_same_origin)])
def delete_shelf(shelf_id: str, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        repo.delete_shelf(shelf_id)
        return {"ok": True, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/inbox/{inbox_id}/place", dependencies=[Depends(require_same_origin)])
def place_inbox(inbox_id: str, payload: InventoryInboxPlacement, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        item_id = repo.place_inbox(inbox_id, payload.location, payload.shelf)
        return {"ok": True, "item_id": item_id, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/inbox/{inbox_id}", dependencies=[Depends(require_same_origin)])
def dismiss_inbox(inbox_id: str, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        repo.dismiss_inbox(inbox_id)
        return {"ok": True, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/suggestions/{suggestion_id}/shopping", dependencies=[Depends(require_same_origin)])
def suggestion_to_shopping(suggestion_id: str, payload: InventorySuggestionShopping, identity: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        shopping_id = repo.suggestion_to_shopping(suggestion_id, payload.list_id, identity.user)
        return {"ok": True, "shopping_item_id": shopping_id, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/suggestions/{suggestion_id}", dependencies=[Depends(require_same_origin)])
def dismiss_suggestion(suggestion_id: str, _: Identity = Depends(require_adult), repo: InventoryRepository = Depends(repository)) -> dict:
    try:
        repo.dismiss_suggestion(suggestion_id)
        return {"ok": True, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
