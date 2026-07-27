from app.auth.service import Identity
from app.modules.food.repository import FoodRepository
from app.modules.inventory.repository import InventoryRepository
from app.modules.shopping.repository import ShoppingRepository


class FoodService:
    def __init__(
        self,
        food: FoodRepository,
        shopping: ShoppingRepository,
        inventory: InventoryRepository,
    ) -> None:
        self.food = food
        self.shopping = shopping
        self.inventory = inventory

    def overview(self, identity: Identity) -> dict:
        meals = self.food.weekly_meals()
        recipes = self.food.saved_recipes()
        shopping = self.shopping.overview()
        inventory = self.inventory.overview()
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "meals": meals,
            "recipes": recipes,
            "shopping": shopping,
            "inventory": inventory,
            "source_status": {
                "meals": self.food.database.table_exists("weekly_meals"),
                "recipes": self.food.database.table_exists("saved_dinners"),
                "shopping": shopping.get("ok", False),
                "inventory": inventory.get("ok", False),
            },
            "totals": {
                "meals": len(meals),
                "recipes": len(recipes),
                "shopping_items": len(shopping.get("active", [])),
                "inventory_items": len(inventory.get("items", [])),
            },
        }
