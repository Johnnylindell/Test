from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.wishlists.repository import WishlistRepository
from app.modules.wishlists.schemas import WishlistCreate, WishlistUpdate

router = APIRouter(prefix="/api/v2/wishlists", tags=["wishlists"])


def repository(request: Request) -> WishlistRepository:
    return WishlistRepository(request.app.state.database)


@router.get("/overview")
def overview(member: str = "", repo: WishlistRepository = Depends(repository), _: Identity = Depends(require_login)) -> dict:
    return repo.overview(member)


@router.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(
    payload: WishlistCreate,
    repo: WishlistRepository = Depends(repository),
    _: Identity = Depends(require_login),
    __: None = Depends(require_same_origin),
) -> dict:
    try:
        return {"ok": True, "id": repo.add(payload.model_dump())}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/items/{item_id}")
def update_item(
    item_id: str,
    payload: WishlistUpdate,
    repo: WishlistRepository = Depends(repository),
    _: Identity = Depends(require_login),
    __: None = Depends(require_same_origin),
) -> dict:
    try:
        repo.update(item_id, payload.model_dump(exclude_unset=True))
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    repo: WishlistRepository = Depends(repository),
    _: Identity = Depends(require_login),
    __: None = Depends(require_same_origin),
) -> dict:
    try:
        repo.delete(item_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
