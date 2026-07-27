from __future__ import annotations

import time
from typing import Any

from app.database.database import Database

LOCATIONS = {
    "fridge": "Kyl",
    "freezer": "Frys",
    "pantry": "Skafferi",
    "chest_freezer": "Frysbox",
    "other": "Övrigt",
}


class InventoryRepository:
    REQUIRED = {"inventory_items", "inventory_inbox", "inventory_shelves", "inventory_shopping_suggestions"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def ready(self) -> bool:
        return all(self.database.table_exists(name) for name in self.REQUIRED)

    def overview(self) -> dict[str, Any]:
        if not self.ready():
            return {
                "ok": False,
                "items": [],
                "inbox": [],
                "suggestions": [],
                "locations": [],
                "reason": "schema_missing",
            }
        items = self.database.fetch_all(
            "SELECT * FROM inventory_items ORDER BY location,shelf,name COLLATE NOCASE"
        )
        inbox = self.database.fetch_all("SELECT * FROM inventory_inbox ORDER BY created_at DESC")
        suggestions = self.database.fetch_all(
            "SELECT * FROM inventory_shopping_suggestions "
            "WHERE COALESCE(dismissed_at,'')='' ORDER BY created_at DESC"
        )
        shelves = self.database.fetch_all("SELECT * FROM inventory_shelves ORDER BY location,name COLLATE NOCASE")
        locations = []
        for location_id, label in LOCATIONS.items():
            location_items = [item for item in items if str(item.get("location") or "other") == location_id]
            locations.append({
                "id": location_id,
                "label": label,
                "items": location_items,
                "shelves": [row for row in shelves if str(row.get("location") or "") == location_id],
            })
        return {
            "ok": True,
            "items": items,
            "inbox": inbox,
            "suggestions": suggestions,
            "locations": locations,
            "totals": {
                "items": len(items),
                "inbox": len(inbox),
                "suggestions": len(suggestions),
                "out_of_stock": sum(float(item.get("quantity") or 0) <= 0 for item in items),
            },
        }

    def add(self, payload: dict[str, Any]) -> str:
        if not self.ready():
            raise RuntimeError("Inventory-schema saknas")
        if payload["location"] not in LOCATIONS:
            raise ValueError("Ogiltig förrådsplats")
        item_id = f"inv-{int(time.time() * 1000)}"
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO inventory_items(id,name,quantity,unit,location,shelf,usual_location,usual_shelf,note,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    payload["name"],
                    payload["quantity"],
                    payload["unit"],
                    payload["location"],
                    payload["shelf"],
                    payload["location"],
                    payload["shelf"],
                    payload["note"],
                    now,
                    now,
                ),
            )
            if payload["quantity"] <= 0:
                suggestion_id = f"inv-sugg-{int(time.time() * 1000)}"
                connection.execute(
                    "INSERT INTO inventory_shopping_suggestions"
                    "(id,item_id,text,quantity,unit,reason,created_at,dismissed_at) VALUES(?,?,?,?,?,?,?,'')",
                    (suggestion_id, item_id, payload["name"], 1, payload["unit"], "Tog slut i förrådet", now),
                )
        return item_id

    def adjust(self, item_id: str, delta: float) -> float:
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with self.database.transaction() as connection:
            row = connection.execute("SELECT name,quantity,unit FROM inventory_items WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise ValueError("Förrådsvaran saknas")
            quantity = max(0.0, float(row[1] or 0) + float(delta))
            connection.execute(
                "UPDATE inventory_items SET quantity=?,updated_at=? WHERE id=?",
                (quantity, now, item_id),
            )
            if quantity <= 0:
                active = connection.execute(
                    "SELECT id FROM inventory_shopping_suggestions WHERE item_id=? AND COALESCE(dismissed_at,'')=''",
                    (item_id,),
                ).fetchone()
                if not active:
                    suggestion_id = f"inv-sugg-{int(time.time() * 1000)}"
                    connection.execute(
                        "INSERT INTO inventory_shopping_suggestions"
                        "(id,item_id,text,quantity,unit,reason,created_at,dismissed_at) VALUES(?,?,?,?,?,?,?,'')",
                        (suggestion_id, item_id, str(row[0] or ""), 1, str(row[2] or ""), "Tog slut i förrådet", now),
                    )
        return quantity
