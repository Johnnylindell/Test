from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database

LOCATIONS = {
    "fridge": "Kyl",
    "freezer": "Frys",
    "pantry": "Skafferi",
    "chest_freezer": "Frysbox",
    "other": "Övrigt",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            location_shelves = [row for row in shelves if str(row.get("location") or "") == location_id]
            grouped: dict[str, list[dict[str, Any]]] = {}
            for item in location_items:
                grouped.setdefault(str(item.get("shelf") or "Standard"), []).append(item)
            for shelf in location_shelves:
                grouped.setdefault(str(shelf.get("name") or "Standard"), [])
            locations.append({
                "id": location_id,
                "label": label,
                "items": location_items,
                "custom_shelves": location_shelves,
                "shelves": [{"name": name, "items": rows} for name, rows in grouped.items()],
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

    def _validate_location(self, location: str) -> str:
        value = str(location or "other").strip() or "other"
        if value not in LOCATIONS:
            raise ValueError("Ogiltig förrådsplats")
        return value

    def _ensure_suggestion(self, connection, item_id: str, name: str, unit: str, reason: str) -> None:
        active = connection.execute(
            "SELECT id FROM inventory_shopping_suggestions WHERE item_id=? AND COALESCE(dismissed_at,'')=''",
            (item_id,),
        ).fetchone()
        if active:
            return
        connection.execute(
            "INSERT INTO inventory_shopping_suggestions(id,item_id,text,quantity,unit,reason,created_at,dismissed_at) "
            "VALUES(?,?,?,?,?,?,?,'')",
            ("inv-sugg-" + secrets.token_hex(8), item_id, name, 1, unit, reason, _now()),
        )

    def add(self, payload: dict[str, Any]) -> str:
        if not self.ready():
            raise RuntimeError("Inventory-schema saknas")
        location = self._validate_location(payload["location"])
        item_id = "inv-" + secrets.token_hex(8)
        now = _now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO inventory_items(id,name,quantity,unit,location,shelf,usual_location,usual_shelf,note,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    payload["name"].strip(),
                    payload["quantity"],
                    payload["unit"],
                    location,
                    payload["shelf"],
                    location,
                    payload["shelf"],
                    payload["note"],
                    now,
                    now,
                ),
            )
            if payload["quantity"] <= 0:
                self._ensure_suggestion(connection, item_id, payload["name"].strip(), payload["unit"], "Tog slut i förrådet")
        return item_id

    def update(self, item_id: str, changes: dict[str, Any]) -> None:
        allowed = {
            key: value for key, value in changes.items()
            if value is not None and key in {"name", "quantity", "unit", "location", "shelf", "note"}
        }
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM inventory_items WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise ValueError("Förrådsvaran saknas")
            if "location" in allowed:
                allowed["location"] = self._validate_location(allowed["location"])
            allowed["updated_at"] = _now()
            assignments = ",".join(f'"{key}"=?' for key in allowed)
            connection.execute(f"UPDATE inventory_items SET {assignments} WHERE id=?", (*allowed.values(), item_id))
            quantity = float(allowed.get("quantity", row["quantity"]) or 0)
            name = str(allowed.get("name", row["name"]) or "")
            unit = str(allowed.get("unit", row["unit"]) or "")
            if quantity <= 0:
                self._ensure_suggestion(connection, item_id, name, unit, "Tog slut i förrådet")

    def adjust(self, item_id: str, delta: float) -> float:
        now = _now()
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
                self._ensure_suggestion(connection, item_id, str(row[0] or ""), str(row[2] or ""), "Tog slut i förrådet")
        return quantity

    def delete_item(self, item_id: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("UPDATE inventory_shopping_suggestions SET dismissed_at=? WHERE item_id=? AND COALESCE(dismissed_at,'')=''", (_now(), item_id))
            cursor = connection.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))
            if cursor.rowcount != 1:
                raise ValueError("Förrådsvaran saknas")

    def add_shelf(self, location: str, name: str) -> str:
        location = self._validate_location(location)
        clean_name = str(name or "").strip()[:80]
        if not clean_name:
            raise ValueError("Hyllnamn krävs")
        shelf_id = "shelf-" + secrets.token_hex(8)
        self.database.execute(
            "INSERT INTO inventory_shelves(id,location,name,created_at) VALUES(?,?,?,?)",
            (shelf_id, location, clean_name, _now()),
        )
        return shelf_id

    def delete_shelf(self, shelf_id: str) -> None:
        with self.database.transaction() as connection:
            shelf = connection.execute("SELECT location,name FROM inventory_shelves WHERE id=?", (shelf_id,)).fetchone()
            if not shelf:
                raise ValueError("Hyllan finns inte")
            used = connection.execute(
                "SELECT 1 FROM inventory_items WHERE location=? AND shelf=? LIMIT 1",
                (shelf["location"], shelf["name"]),
            ).fetchone()
            if used:
                raise ValueError("Hyllan innehåller varor")
            connection.execute("DELETE FROM inventory_shelves WHERE id=?", (shelf_id,))

    def place_inbox(self, inbox_id: str, location: str = "", shelf: str = "") -> str:
        now = _now()
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM inventory_inbox WHERE id=?", (inbox_id,)).fetchone()
            if not row:
                raise ValueError("Mellanlagerposten saknas")
            target_location = self._validate_location(location or row["suggested_location"] or "other")
            target_shelf = str(shelf or row["suggested_shelf"] or "Standard").strip()[:80]
            existing = connection.execute(
                "SELECT id FROM inventory_items WHERE lower(name)=lower(?) AND unit=? AND location=? AND shelf=?",
                (row["name"], row["unit"] or "", target_location, target_shelf),
            ).fetchone()
            quantity = float(row["quantity"] or 1)
            if existing:
                inventory_item_id = str(existing[0])
                connection.execute(
                    "UPDATE inventory_items SET quantity=quantity+?,updated_at=? WHERE id=?",
                    (quantity, now, inventory_item_id),
                )
            else:
                inventory_item_id = "inv-" + secrets.token_hex(8)
                connection.execute(
                    "INSERT INTO inventory_items(id,name,quantity,unit,location,shelf,usual_location,usual_shelf,note,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        inventory_item_id,
                        row["name"],
                        quantity,
                        row["unit"] or "",
                        target_location,
                        target_shelf,
                        target_location,
                        target_shelf,
                        "",
                        now,
                        now,
                    ),
                )
            connection.execute(
                "INSERT INTO inventory_placements(id,shopping_item_id,inventory_item_id,quantity,unit,placed_at,reverted_at,revert_mode) "
                "VALUES(?,?,?,?,?,?,'','')",
                (
                    "place-" + secrets.token_hex(8),
                    row["shopping_item_id"] or "",
                    inventory_item_id,
                    quantity,
                    row["unit"] or "",
                    now,
                ),
            )
            connection.execute("DELETE FROM inventory_inbox WHERE id=?", (inbox_id,))
            return inventory_item_id

    def dismiss_inbox(self, inbox_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM inventory_inbox WHERE id=?", (inbox_id,))
            if cursor.rowcount != 1:
                raise ValueError("Mellanlagerposten saknas")

    def suggestion_to_shopping(self, suggestion_id: str, list_id: str, actor: str) -> str:
        now = _now()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM inventory_shopping_suggestions WHERE id=? AND COALESCE(dismissed_at,'')=''",
                (suggestion_id,),
            ).fetchone()
            if not row:
                raise ValueError("Inköpsförslaget saknas")
            connection.execute(
                "INSERT OR IGNORE INTO shopping_lists(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (list_id, "Inköp" if list_id == "shopping" else list_id, now, now),
            )
            duplicate = connection.execute(
                "SELECT id FROM shopping_items WHERE list_id=? AND COALESCE(done,0)=0 AND lower(trim(text))=lower(trim(?))",
                (list_id, row["text"]),
            ).fetchone()
            if duplicate:
                shopping_id = str(duplicate[0])
            else:
                shopping_id = "item-" + secrets.token_hex(8)
                order = connection.execute(
                    "SELECT COALESCE(MAX(sort_order),0)+1 FROM shopping_items WHERE list_id=? AND COALESCE(done,0)=0",
                    (list_id,),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO shopping_items(id,list_id,text,category,store,done,sort_order,owner,quantity,unit,created_at,source) "
                    "VALUES(?,?,?,?,?,0,?,?,?,?,?,?)",
                    (
                        shopping_id,
                        list_id,
                        row["text"],
                        "",
                        "",
                        order,
                        actor,
                        row["quantity"] or 1,
                        row["unit"] or "",
                        now,
                        "Inventory",
                    ),
                )
            connection.execute(
                "UPDATE inventory_shopping_suggestions SET dismissed_at=? WHERE id=?",
                (now, suggestion_id),
            )
            return shopping_id

    def dismiss_suggestion(self, suggestion_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE inventory_shopping_suggestions SET dismissed_at=? WHERE id=? AND COALESCE(dismissed_at,'')=''",
                (_now(), suggestion_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Inköpsförslaget saknas")
