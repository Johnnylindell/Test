from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.food.importer import RecipeImporter
from app.modules.food.repository import FoodRepository
from app.modules.food.schemas import (
    IngredientsToShopping,
    MealSet,
    RecipeCreate,
    RecipeImportPreview,
    RecipeImportSave,
    RecipeUpdate,
)
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


def require_adult(identity: Identity = Depends(require_login)) -> Identity:
    if not identity.admin and identity.user not in {"johnny", "kristina"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Den valda profilen får inte ändra recept eller matsedel",
        )
    return identity


@router.get("/overview")
def overview(identity: Identity = Depends(require_login), food: FoodService = Depends(service)) -> dict:
    return food.overview(identity)


@router.put("/meals", dependencies=[Depends(require_same_origin)])
def set_meal(
    payload: MealSet,
    identity: Identity = Depends(require_adult),
    repo: FoodRepository = Depends(food_repository),
    food: FoodService = Depends(service),
) -> dict:
    repo.set_meal(payload.model_dump())
    return {"ok": True, "view": food.overview(identity)}


@router.post("/recipes", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_recipe(
    payload: RecipeCreate,
    _: Identity = Depends(require_adult),
    repo: FoodRepository = Depends(food_repository),
) -> dict:
    return {"ok": True, "id": repo.add_recipe(payload.model_dump()), "recipes": repo.saved_recipes()}


@router.post("/recipes/import/preview", dependencies=[Depends(require_same_origin)])
def preview_recipe_import(
    payload: RecipeImportPreview,
    _: Identity = Depends(require_adult),
) -> dict:
    try:
        return RecipeImporter().preview(str(payload.url))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Receptsidan kunde inte läsas") from exc


@router.post(
    "/recipes/import/save",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_same_origin)],
)
def save_recipe_import(
    payload: RecipeImportSave,
    _: Identity = Depends(require_adult),
    repo: FoodRepository = Depends(food_repository),
) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Importen måste bekräftas")
    recipe_id = repo.add_recipe(payload.recipe.model_dump())
    return {"ok": True, "id": recipe_id, "recipes": repo.saved_recipes()}


@router.patch("/recipes/{recipe_id}", dependencies=[Depends(require_same_origin)])
def update_recipe(
    recipe_id: str,
    payload: RecipeUpdate,
    _: Identity = Depends(require_adult),
    repo: FoodRepository = Depends(food_repository),
) -> dict:
    try:
        repo.update_recipe(recipe_id, payload.model_dump(exclude_unset=True))
        return {"ok": True, "recipes": repo.saved_recipes()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/recipes/{recipe_id}", dependencies=[Depends(require_same_origin)])
def delete_recipe(
    recipe_id: str,
    _: Identity = Depends(require_adult),
    repo: FoodRepository = Depends(food_repository),
) -> dict:
    try:
        repo.delete_recipe(recipe_id)
        return {"ok": True, "recipes": repo.saved_recipes()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ingredients/shopping", dependencies=[Depends(require_same_origin)])
def ingredients_to_shopping(
    payload: IngredientsToShopping,
    identity: Identity = Depends(require_login),
    repo: FoodRepository = Depends(food_repository),
) -> dict:
    item_ids = repo.ingredients_to_shopping(
        payload.ingredients,
        payload.list_id,
        identity.user,
        payload.source,
    )
    return {"ok": True, "item_ids": item_ids}
