from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import current_identity, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.shopping.repository import ShoppingRepository
from app.modules.shopping.schemas import ShoppingCompletion, ShoppingItemCreate, ShoppingItemUpdate

router = APIRouter(prefix="/api/v2/shopping", tags=["shopping"])


def repository(request: Request) -> ShoppingRepository:
    return ShoppingRepository(request.app.state.database)


@router.get("/overview")
def overview(
    _: Identity = Depends(require_login),
    repo: ShoppingRepository = Depends(repository),
) -> dict:
    return repo.overview()


@router.post("/items", dependencies=[Depends(require_same_origin)])
def add_item(
    payload: ShoppingItemCreate,
    identity: Identity = Depends(require_login),
    repo: ShoppingRepository = Depends(repository),
) -> dict:
    item_id = repo.add(payload.model_dump(), identity.user)
    return {"ok": True, "item_id": item_id, "view": repo.overview()}


@router.patch("/items/{item_id}", dependencies=[Depends(require_same_origin)])
def update_item(
    item_id: str,
    payload: ShoppingItemUpdate,
    _: Identity = Depends(require_login),
    repo: ShoppingRepository = Depends(repository),
) -> dict:
    repo.update(item_id, payload.model_dump(exclude_unset=True))
    return {"ok": True, "view": repo.overview()}


@router.patch("/items/{item_id}/completion", dependencies=[Depends(require_same_origin)])
def set_completion(
    item_id: str,
    payload: ShoppingCompletion,
    _: Identity = Depends(require_login),
    repo: ShoppingRepository = Depends(repository),
) -> dict:
    repo.complete(item_id, payload.done)
    return {"ok": True, "view": repo.overview()}
