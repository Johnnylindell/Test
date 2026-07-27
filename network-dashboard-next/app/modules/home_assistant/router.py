from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.home_assistant.service import HomeLifeService

router = APIRouter(prefix="/api/v2/home-assistant", tags=["home-assistant"])


class HomeServiceCommand(BaseModel):
    entity_id: str = Field(min_length=3, max_length=180, pattern=r"^[a-z_]+\.[A-Za-z0-9_]+$")
    service: str = Field(min_length=3, max_length=40)


class HomeFavoritesUpdate(BaseModel):
    entity_ids: list[str] = Field(default_factory=list, max_length=100)


def service(request: Request) -> HomeLifeService:
    return HomeLifeService(request.app.state.database, request.app.state.home_assistant)


def require_adult(identity: Identity = Depends(require_login)) -> Identity:
    if not identity.admin and identity.user not in {"johnny", "kristina"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vuxenprofil krävs för att styra hemmet")
    return identity


def require_external(request: Request) -> None:
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Hemstyrning är avstängd i parallelläge")


@router.get("/overview")
def overview(
    request: Request,
    fresh: bool = False,
    _: Identity = Depends(require_login),
    home: HomeLifeService = Depends(service),
) -> dict:
    if fresh and not request.app.state.settings.external_side_effects:
        fresh = False
    return home.overview(fresh=fresh)


@router.post("/service", dependencies=[Depends(require_same_origin)])
def call_service(
    payload: HomeServiceCommand,
    request: Request,
    _: Identity = Depends(require_adult),
) -> dict:
    require_external(request)
    try:
        result = request.app.state.home_assistant.call_service(payload.entity_id, payload.service)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Home Assistant svarar inte")
    return result


@router.put("/favorites", dependencies=[Depends(require_same_origin)])
def update_favorites(
    payload: HomeFavoritesUpdate,
    _: Identity = Depends(require_admin),
    home: HomeLifeService = Depends(service),
) -> dict:
    return {"ok": True, "favorites": home.save_favorites(payload.entity_ids)}
