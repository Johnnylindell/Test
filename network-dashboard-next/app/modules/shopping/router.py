from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.shopping.repository import ShoppingRepository
from app.modules.shopping.schemas import ShoppingCompletion, ShoppingItemCreate, ShoppingItemUpdate
from app.modules.shopping.service import ShoppingService

router = APIRouter(prefix="/api/v2/shopping", tags=["shopping"])


def repository(request: Request) -> ShoppingRepository:
    return ShoppingRepository(request.app.state.database)


def service(request: Request) -> ShoppingService:
    return ShoppingService(request.app.state.database)


@router.get("/overview")
def overview(_: Identity = Depends(require_login), shopping: ShoppingService = Depends(service)) -> dict:
    return shopping.overview()


@router.post("/items", dependencies=[Depends(require_same_origin)])
def add_item(payload: ShoppingItemCreate, identity: Identity = Depends(require_login), repo: ShoppingRepository = Depends(repository)) -> dict:
    item_id = repo.add(payload.model_dump(), identity.user)
    return {"ok": True, "item_id": item_id, "view": repo.overview()}


@router.patch("/items/{item_id}", dependencies=[Depends(require_same_origin)])
def update_item(item_id: str, payload: ShoppingItemUpdate, _: Identity = Depends(require_login), repo: ShoppingRepository = Depends(repository)) -> dict:
    try:
        repo.update(item_id, payload.model_dump(exclude_unset=True))
        return {"ok": True, "view": repo.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/items/{item_id}/completion", dependencies=[Depends(require_same_origin)])
def set_completion(item_id: str, payload: ShoppingCompletion, _: Identity = Depends(require_login), shopping: ShoppingService = Depends(service)) -> dict:
    try:
        shopping.complete(item_id, payload.done)
        return {"ok": True, "view": shopping.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/suggestions/{suggestion_id}/shopping", dependencies=[Depends(require_same_origin)])
def add_suggestion(
    suggestion_id: str,
    identity: Identity = Depends(require_login),
    shopping: ShoppingService = Depends(service),
) -> dict:
    try:
        item_id = shopping.add_suggestion(suggestion_id, identity.user)
        return {"ok": True, "item_id": item_id, "view": shopping.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/suggestions/{suggestion_id}", dependencies=[Depends(require_same_origin)])
def dismiss_suggestion(
    suggestion_id: str,
    days: int = 30,
    _: Identity = Depends(require_login),
    shopping: ShoppingService = Depends(service),
) -> dict:
    try:
        shopping.dismiss_suggestion(suggestion_id, days)
        return {"ok": True, "view": shopping.overview()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
