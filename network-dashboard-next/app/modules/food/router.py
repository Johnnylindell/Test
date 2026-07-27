from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.food.repository import FoodRepository
from app.modules.food.schemas import MealSet
from app.modules.food.service import FoodService
from app.modules.inventory.repository import InventoryRepository
from app.modules.shopping.repository import ShoppingRepository

router = APIRouter(prefix="/api/v2/food", tags=["food"])


def food_repository(request: Request) -> FoodRepository:
    return FoodRepository(request.app.state.database)


def service(request: Request) -> FoodService:
    database = request.app.state.database
    return FoodService(
        FoodRepository(database),
        ShoppingRepository(database),
        InventoryRepository(database),
    )


@router.get("/overview")
def overview(
    identity: Identity = Depends(require_login),
    food: FoodService = Depends(service),
) -> dict:
    return food.overview(identity)


@router.put("/meals", dependencies=[Depends(require_same_origin)])
def set_meal(
    payload: MealSet,
    identity: Identity = Depends(require_login),
    repo: FoodRepository = Depends(food_repository),
    food: FoodService = Depends(service),
) -> dict:
    if identity.user not in {"johnny", "kristina", "admin"}:
        raise PermissionError("Den valda profilen får inte ändra matsedeln")
    repo.set_meal(payload.model_dump())
    return {"ok": True, "view": food.overview(identity)}
