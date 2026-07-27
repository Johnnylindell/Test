from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database
from app.modules.shopping.repository import ShoppingRepository

_CATEGORY_LOCATIONS = {
    "frys": ("freezer", "Standard"),
    "fryst": ("freezer", "Standard"),
    "kyl": ("fridge", "Standard"),
    "mejeri": ("fridge", "Standard"),
    "grönsak": ("fridge", "Standard"),
    "skafferi": ("pantry", "Standard"),
    "torrvara": ("pantry", "Standard"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_text(text: str, quantity: Any, unit: str) -> tuple[str, float, str]:
    clean = re.sub(r"\s+", " ", str(text or "").strip())
    if quantity not in (None, ""):
        return clean, max(0.0, float(quantity)), str(unit or "")[:30]
    match = re.match(r"^(\d+(?:[.,]\d+)?)\s+([A-Za-zÅÄÖåäö]+)\s+(.+)$", clean)
    if match:
        return match.group(3).strip(), float(match.group(1).replace(",", ".")), match.group(2)[:30]
    match = re.match(r"^(\d+(?:[.,]\d+)?)\s+(.+)$", clean)
    if match:
        return match.group(2).strip(), float(match.group(1).replace(",", ".")), ""
    return clean, 1.0, str(unit or "")[:30]


def _suggest(category: str, text: str) -> tuple[str, str]:
    haystack = f"{category} {text}".casefold()
    for key, value in _CATEGORY_LOCATIONS.items():
        if key in haystack:
            return value
    return "other", "Standard"


class ShoppingService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.repository = ShoppingRepository(database)

    def overview(self) -> dict[str, Any]:
        return self.repository.overview()

    def complete(self, item_id: str, done: bool) -> None:
        now = _now()
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM shopping_items WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise ValueError("Inköpsvaran saknas")
            connection.execute(
                "UPDATE shopping_items SET done=?,completed_at=? WHERE id=?",
                (1 if done else 0, now if done else "", item_id),
            )
            if done:
                if not self.database.table_exists("inventory_inbox"):
                    return
                name, quantity, unit = _parse_text(row["text"], row["quantity"], row["unit"])
                location, shelf = _suggest(row["category"], row["text"])
                existing = connection.execute(
                    "SELECT id FROM inventory_inbox WHERE shopping_item_id=?",
                    (item_id,),
                ).fetchone()
                inbox_id = str(existing[0]) if existing else "inbox-" + secrets.token_hex(8)
                connection.execute(
                    "INSERT INTO inventory_inbox(id,shopping_item_id,text,name,quantity,unit,category,store,suggested_location,suggested_shelf,created_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET text=excluded.text,name=excluded.name,quantity=excluded.quantity,unit=excluded.unit,category=excluded.category,store=excluded.store,suggested_location=excluded.suggested_location,suggested_shelf=excluded.suggested_shelf,created_at=excluded.created_at",
                    (
                        inbox_id,
                        item_id,
                        row["text"],
                        name,
                        quantity,
                        unit,
                        row["category"],
                        row["store"],
                        location,
                        shelf,
                        now,
                    ),
                )
                return

            connection.execute("DELETE FROM inventory_inbox WHERE shopping_item_id=?", (item_id,))
            placements = connection.execute(
                "SELECT id,inventory_item_id,quantity FROM inventory_placements "
                "WHERE shopping_item_id=? AND COALESCE(reverted_at,'')=''",
                (item_id,),
            ).fetchall()
            for placement in placements:
                inventory = connection.execute(
                    "SELECT quantity FROM inventory_items WHERE id=?",
                    (placement["inventory_item_id"],),
                ).fetchone()
                if inventory:
                    new_quantity = max(0.0, float(inventory[0] or 0) - float(placement["quantity"] or 0))
                    connection.execute(
                        "UPDATE inventory_items SET quantity=?,updated_at=? WHERE id=?",
                        (new_quantity, now, placement["inventory_item_id"]),
                    )
                connection.execute(
                    "UPDATE inventory_placements SET reverted_at=?,revert_mode='shopping_reopened' WHERE id=?",
                    (now, placement["id"]),
                )
