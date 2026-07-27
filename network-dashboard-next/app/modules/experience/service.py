from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Any

from app.auth.service import Identity
from app.database.database import Database
from app.modules.family.repository import FamilyRepository
from app.modules.food.repository import FoodRepository
from app.modules.household.repository import HouseholdRepository
from app.modules.inventory.repository import InventoryRepository
from app.modules.planning.repository import PlanningRepository
from app.modules.shopping.repository import ShoppingRepository
from app.modules.wishlists.repository import WishlistRepository


class ExperienceService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.family = FamilyRepository(database)
        self.planning = PlanningRepository(database)
        self.food = FoodRepository(database)
        self.shopping = ShoppingRepository(database)
        self.inventory = InventoryRepository(database)
        self.wishlists = WishlistRepository(database)
        self.household = HouseholdRepository(database)

    def overview(self, identity: Identity) -> dict[str, Any]:
        shopping = self.shopping.overview()
        inventory = self.inventory.overview()
        family_lists = self.family.lists()
        reminders = self.planning.reminders(limit=30)
        forget = self.forget_items(identity.user)
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "cards": {
                "shopping": len(shopping.get("active") or []),
                "inventory_inbox": len(inventory.get("inbox") or []),
                "open_reminders": sum(not row.get("done") for row in reminders),
                "open_family_items": sum(row.get("open_count", 0) for row in family_lists),
                "forget_items": len([row for row in forget if not row.get("done")]),
            },
            "recent": {
                "reminders": reminders[:8],
                "family_lists": family_lists[:8],
                "forget_items": forget[:8],
            },
        }

    def personal_dashboard(self, identity: Identity) -> dict[str, Any]:
        user = identity.user
        reminders = [row for row in self.planning.reminders(limit=100) if not row.get("owner") or str(row.get("owner")).lower() == user]
        lists = self.family.lists()
        assigned = []
        for family_list in lists:
            for item in family_list.get("items") or []:
                if not item.get("owner") or str(item.get("owner")).lower() == user:
                    assigned.append({**item, "list_id": family_list.get("id"), "list_title": family_list.get("title")})
        return {
            "ok": True,
            "user": user,
            "reminders": reminders,
            "assigned_list_items": assigned,
            "forget_items": self.forget_items(user),
            "wishlist": self.wishlists.overview(user),
        }

    def search(self, query: str, identity: Identity) -> dict[str, Any]:
        q = query.strip().casefold()
        if len(q) < 2:
            return {"ok": True, "query": query, "results": []}
        results = []

        def add(kind: str, title: str, detail: str, url: str, data: dict[str, Any]) -> None:
            haystack = f"{title} {detail}".casefold()
            if q in haystack:
                results.append({"kind": kind, "title": title, "detail": detail, "url": url, "data": data})

        for row in self.planning.reminders(limit=200):
            add("reminder", row.get("title", ""), row.get("due_at", ""), "/#planning", row)
        for family_list in self.family.lists():
            for row in family_list.get("items") or []:
                add("family-list", row.get("text", ""), family_list.get("title", ""), "/#family", row)
        for row in self.shopping.overview().get("active") or []:
            add("shopping", str(row.get("text") or ""), str(row.get("store") or ""), "/#shopping", row)
        for row in self.inventory.overview().get("items") or []:
            add("inventory", str(row.get("name") or ""), f"{row.get('location','')} {row.get('shelf','')}", "/#inventory", row)
        for row in self.food.saved_recipes():
            add("recipe", str(row.get("title") or ""), str(row.get("source_url") or ""), "/#food", row)
        for row in self.wishlists.overview().get("items") or []:
            add("wishlist", str(row.get("title") or ""), str(row.get("member") or ""), "/#wishlists", row)
        for row in self.household.overview(query).get("items") or []:
            add("household", str(row.get("name") or ""), str(row.get("location") or ""), "/#household", row)
        return {"ok": True, "query": query, "results": results[:100], "count": len(results)}

    def forget_items(self, user: str) -> list[dict[str, Any]]:
        if not self.database.table_exists("forget_items"):
            return []
        return self.database.fetch_all(
            "SELECT * FROM forget_items WHERE owner IN ('',?,'all','family') ORDER BY done,due_at,created_at DESC",
            (user,),
        )

    def add_forget_item(self, data: dict[str, Any], actor: str) -> str:
        item_id = secrets.token_hex(8)
        owner = str(data.get("owner") or actor)
        self.database.execute(
            "INSERT INTO forget_items(id,owner,title,note,due_at,done,created_at,completed_at) VALUES(?,?,?,?,?,0,?,'')",
            (item_id, owner, data["title"].strip(), data.get("note", ""), data.get("due_at", ""), datetime.now(timezone.utc).isoformat()),
        )
        return item_id

    def update_forget_item(self, item_id: str, changes: dict[str, Any]) -> None:
        allowed = {key: value for key, value in changes.items() if value is not None and key in {"title", "note", "due_at", "owner", "done"}}
        if "done" in allowed:
            done = bool(allowed["done"])
            allowed["done"] = 1 if done else 0
            allowed["completed_at"] = datetime.now(timezone.utc).isoformat() if done else ""
        if not allowed:
            return
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE forget_items SET {assignments} WHERE id=?", (*allowed.values(), item_id))
            if cursor.rowcount != 1:
                raise ValueError("Glöm-inte-posten finns inte")

    def delete_forget_item(self, item_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM forget_items WHERE id=?", (item_id,))
            if cursor.rowcount != 1:
                raise ValueError("Glöm-inte-posten finns inte")

    def quests(self, identity: Identity) -> dict[str, Any]:
        today = date.today().isoformat()
        completed = set()
        if self.database.table_exists("home_quest_completions"):
            completed = {
                str(row["quest_id"])
                for row in self.database.fetch_all(
                    "SELECT quest_id FROM home_quest_completions WHERE quest_date=? AND owner=?",
                    (today, identity.user),
                )
            }
        shopping_count = len(self.shopping.overview().get("active") or [])
        inventory = self.inventory.overview()
        reminders = self.planning.reminders(limit=30)
        meal_rows = self.food.weekly_meals()
        quests = [
            {"id": "shopping-one", "title": "Ta en inköpssak", "detail": f"{shopping_count} saker på listan", "minutes": 2},
            {"id": "inventory-check", "title": "Kontrollera en förrådsvara", "detail": f"{len(inventory.get('items') or [])} registrerade varor", "minutes": 2},
            {"id": "planning-one", "title": "Bocka av en planerad sak", "detail": f"{sum(not row.get('done') for row in reminders)} öppna", "minutes": 2},
            {"id": "meal-prep", "title": "Förbered dagens mat", "detail": f"{len(meal_rows)} planerade måltider", "minutes": 3},
        ]
        for row in quests:
            row["done"] = row["id"] in completed
        return {"ok": True, "date": today, "quests": quests}

    def set_quest_done(self, quest_id: str, owner: str, done: bool) -> None:
        today = date.today().isoformat()
        with self.database.transaction() as connection:
            if done:
                connection.execute(
                    "INSERT OR REPLACE INTO home_quest_completions(quest_date,quest_id,owner,completed_at) VALUES(?,?,?,?)",
                    (today, quest_id, owner, datetime.now(timezone.utc).isoformat()),
                )
            else:
                connection.execute(
                    "DELETE FROM home_quest_completions WHERE quest_date=? AND quest_id=? AND owner=?",
                    (today, quest_id, owner),
                )
