from __future__ import annotations

from typing import Any

from app.database.database import Database
from app.modules.common import as_bool, as_text, first_present


class FamilyRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def profiles(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("family_profiles"):
            return []
        rows = self.database.fetch_all("SELECT * FROM family_profiles ORDER BY rowid")
        result = []
        for row in rows:
            result.append({
                "id": as_text(first_present(row, "id", "profile", "user", "name"), limit=80),
                "name": as_text(first_present(row, "display_name", "label", "name", "id"), limit=120),
                "active": as_bool(first_present(row, "active", "enabled", default=True)),
                "data": row,
            })
        return result

    def lists(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("family_lists"):
            return []
        list_rows = self.database.fetch_all("SELECT * FROM family_lists ORDER BY sort_order, rowid")
        item_columns = self.database.table_columns("family_list_items")
        result = []
        for row in list_rows:
            list_id = as_text(first_present(row, "id", "list_id"), limit=120)
            items: list[dict[str, Any]] = []
            if list_id and item_columns and "list_id" in item_columns:
                order_column = "sort_order" if "sort_order" in item_columns else "rowid"
                for item in self.database.fetch_all(
                    f"SELECT * FROM family_list_items WHERE list_id=? ORDER BY {order_column}",
                    (list_id,),
                ):
                    items.append({
                        "id": as_text(first_present(item, "id", "item_id"), limit=120),
                        "text": as_text(first_present(item, "text", "title", "name"), limit=300),
                        "owner": as_text(first_present(item, "owner", "assigned_to"), limit=80),
                        "done": as_bool(first_present(item, "done", "completed", default=False)),
                    })
            result.append({
                "id": list_id,
                "title": as_text(first_present(row, "title", "name", "id"), limit=120),
                "items": items,
                "open_count": sum(not item["done"] for item in items),
            })
        return result

    def notes(self, limit: int = 30) -> list[dict[str, Any]]:
        if not self.database.table_exists("family_notes"):
            return []
        columns = self.database.table_columns("family_notes")
        order = "created_at DESC" if "created_at" in columns else "rowid DESC"
        rows = self.database.fetch_all(f"SELECT * FROM family_notes ORDER BY {order} LIMIT ?", (limit,))
        return [{
            "id": as_text(first_present(row, "id", default=""), limit=120),
            "text": as_text(first_present(row, "text", "note", "content"), limit=1000),
            "owner": as_text(first_present(row, "owner", "user", "created_by"), limit=80),
            "created_at": as_text(first_present(row, "created_at", "updated_at"), limit=80),
        } for row in rows]
