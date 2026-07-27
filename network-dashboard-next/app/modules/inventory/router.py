from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import InventoryAdjustment, InventoryItemCreate

router = APIRouter(prefix="/api/v2/inventory", tags=["inventory"])


def repository(request: Request) -> InventoryRepository:
    return InventoryRepository(request.app.state.database)


@router.get("/overview")
def overview(
    _: Identity = Depends(require_login),
    repo: InventoryRepository = Depends(repository),
) -> dict:
    return repo.overview()


@router.post("/items", dependencies=[Depends(require_same_origin)])
def add_item(
    payload: InventoryItemCreate,
    _: Identity = Depends(require_login),
    repo: InventoryRepository = Depends(repository),
) -> dict:
    item_id = repo.add(payload.model_dump())
    return {"ok": True, "item_id": item_id, "view": repo.overview()}


@router.patch("/items/{item_id}/quantity", dependencies=[Depends(require_same_origin)])
def adjust_quantity(
    item_id: str,
    payload: InventoryAdjustment,
    _: Identity = Depends(require_login),
    repo: InventoryRepository = Depends(repository),
) -> dict:
    quantity = repo.adjust(item_id, payload.delta)
    return {"ok": True, "item_id": item_id, "quantity": quantity, "view": repo.overview()}
