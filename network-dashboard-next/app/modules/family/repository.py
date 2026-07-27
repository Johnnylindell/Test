from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone
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

    def add_note(self, text: str, owner: str) -> str:
        note_id = secrets.token_hex(8)
        self.database.execute(
            "INSERT INTO family_notes(id,text,owner,created_at) VALUES(?,?,?,?)",
            (note_id, text.strip(), owner, datetime.now(timezone.utc).isoformat()),
        )
        return note_id

    def delete_note(self, note_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM family_notes WHERE id=?", (note_id,))
            if cursor.rowcount != 1:
                raise ValueError("Familjeanteckningen finns inte")

    def day_message(self) -> str:
        raw = self.database.get_json_state("day_message", "")
        if isinstance(raw, dict):
            return str(raw.get("message") or "")[:500]
        return str(raw or "")[:500]

    def set_day_message(self, message: str, actor: str) -> None:
        self.database.set_json_state(
            "day_message",
            {
                "message": message.strip()[:500],
                "updated_by": actor,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def add_list_item(self, list_id: str, text: str, owner: str) -> str:
        columns = self.database.table_columns("family_list_items")
        required = {"id", "list_id", "text"}
        if not required.issubset(columns):
            raise RuntimeError("family_list_items har inte förväntat schema")
        item_id = f"item-{time.time_ns()}"
        values: dict[str, Any] = {"id": item_id, "list_id": list_id, "text": text}
        if "owner" in columns:
            values["owner"] = owner
        if "done" in columns:
            values["done"] = 0
        if "sort_order" in columns:
            values["sort_order"] = self.database.count("family_list_items", "list_id=?", (list_id,))
        names = list(values)
        placeholders = ",".join("?" for _ in names)
        with self.database.transaction() as connection:
            exists = connection.execute("SELECT 1 FROM family_lists WHERE id=?", (list_id,)).fetchone()
            if not exists:
                raise ValueError("Listan finns inte")
            connection.execute(
                f"INSERT INTO family_list_items({','.join(names)}) VALUES({placeholders})",
                tuple(values[name] for name in names),
            )
        return item_id

    def set_item_done(self, item_id: str, done: bool) -> None:
        columns = self.database.table_columns("family_list_items")
        if "id" not in columns or "done" not in columns:
            raise RuntimeError("family_list_items saknar id eller done")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE family_list_items SET done=? WHERE id=?",
                (1 if done else 0, item_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Listpunkten finns inte")
