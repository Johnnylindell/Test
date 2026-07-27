from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
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


def _key(text: str) -> str:
    return " ".join(str(text or "").casefold().split())


class ShoppingService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.repository = ShoppingRepository(database)

    def overview(self) -> dict[str, Any]:
        view = self.repository.overview()
        view["smart_suggestions"] = self.smart_suggestions()
        return view

    def smart_suggestions(self, limit: int = 12) -> list[dict[str, Any]]:
        if not self.repository.ready():
            return []
        active = {_key(row.get("text", "")) for row in self.repository.overview().get("active", [])}
        dismissed = self.database.get_json_state("shopping_suggestion_dismissals", {})
        dismissed = dismissed if isinstance(dismissed, dict) else {}
        cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        rows = self.database.fetch_all(
            "SELECT text,category,store,unit,COUNT(*) AS purchases,MAX(completed_at) AS last_bought," 
            "AVG(COALESCE(quantity,1)) AS average_quantity FROM shopping_items "
            "WHERE COALESCE(done,0)=1 AND COALESCE(completed_at,'')>=? "
            "GROUP BY lower(trim(text)),category,store,unit HAVING COUNT(*)>=2 "
            "ORDER BY purchases DESC,last_bought DESC LIMIT 100",
            (cutoff,),
        )
        suggestions = []
        now = datetime.now(timezone.utc)
        for row in rows:
            text = str(row.get("text") or "").strip()
            key = _key(text)
            if not key or key in active:
                continue
            dismissal = dismissed.get(key)
            if isinstance(dismissal, dict):
                until = str(dismissal.get("until") or "")
                if until:
                    try:
                        if datetime.fromisoformat(until.replace("Z", "+00:00")) > now:
                            continue
                    except ValueError:
                        pass
            suggestions.append({
                "id": hashlib_sha(key),
                "text": text,
                "quantity": round(float(row.get("average_quantity") or 1), 2),
                "unit": str(row.get("unit") or "")[:30],
                "category": str(row.get("category") or "")[:80],
                "store": str(row.get("store") or "")[:80],
                "purchases": int(row.get("purchases") or 0),
                "last_bought": str(row.get("last_bought") or ""),
                "reason": f"Köpt {int(row.get('purchases') or 0)} gånger senaste 180 dagarna",
            })
            if len(suggestions) >= max(1, min(limit, 50)):
                break
        return suggestions

    def add_suggestion(self, suggestion_id: str, actor: str) -> str:
        match = next((row for row in self.smart_suggestions(50) if row["id"] == suggestion_id), None)
        if not match:
            raise ValueError("Inköpsförslaget finns inte längre")
        return self.repository.add({
            "list_id": "shopping",
            "text": match["text"],
            "quantity": max(0.01, float(match["quantity"] or 1)),
            "unit": match["unit"],
            "category": match["category"],
            "store": match["store"],
        }, actor)

    def dismiss_suggestion(self, suggestion_id: str, days: int = 30) -> None:
        match = next((row for row in self.smart_suggestions(50) if row["id"] == suggestion_id), None)
        if not match:
            raise ValueError("Inköpsförslaget finns inte längre")
        until = (datetime.now(timezone.utc) + timedelta(days=max(1, min(days, 365)))).isoformat()

        def updater(current: Any) -> dict[str, Any]:
            values = dict(current) if isinstance(current, dict) else {}
            values[_key(match["text"])] = {"until": until, "dismissed_at": _now()}
            return values

        self.database.update_json_state("shopping_suggestion_dismissals", updater, default={})

    def complete(self, item_id: str, done: bool) -> None:
        now = _now()
        inventory_ready = self.database.table_exists("inventory_inbox")
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM shopping_items WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise ValueError("Inköpsvaran saknas")
            connection.execute(
                "UPDATE shopping_items SET done=?,completed_at=? WHERE id=?",
                (1 if done else 0, now if done else "", item_id),
            )
            if done:
                if not inventory_ready:
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


def hashlib_sha(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
