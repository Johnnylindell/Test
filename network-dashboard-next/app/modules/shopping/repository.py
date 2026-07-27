from __future__ import annotations

import time
from typing import Any

from app.database.database import Database


class ShoppingRepository:
    REQUIRED = {"shopping_lists", "shopping_items"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def ready(self) -> bool:
        return all(self.database.table_exists(name) for name in self.REQUIRED)

    def overview(self) -> dict[str, Any]:
        if not self.ready():
            return {"ok": False, "lists": [], "active": [], "completed": [], "reason": "schema_missing"}
        lists = self.database.fetch_all("SELECT * FROM shopping_lists ORDER BY created_at, rowid")
        active = self.database.fetch_all(
            "SELECT * FROM shopping_items WHERE COALESCE(done,0)=0 ORDER BY sort_order, created_at, rowid"
        )
        completed = self.database.fetch_all(
            "SELECT * FROM shopping_items WHERE COALESCE(done,0)=1 ORDER BY completed_at DESC, rowid DESC LIMIT 100"
        )
        by_list: dict[str, list[dict[str, Any]]] = {}
        for item in active:
            by_list.setdefault(str(item.get("list_id") or "shopping"), []).append(item)
        return {
            "ok": True,
            "lists": [dict(row, items=by_list.get(str(row.get("id") or ""), [])) for row in lists],
            "active": active,
            "completed": completed,
        }

    def add(self, payload: dict[str, Any], actor: str) -> str:
        if not self.ready():
            raise RuntimeError("Shopping-schema saknas")
        item_id = f"item-{int(time.time() * 1000)}"
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO shopping_lists(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (payload["list_id"], "Inköp" if payload["list_id"] == "shopping" else payload["list_id"], now, now),
            )
            duplicate = connection.execute(
                "SELECT id FROM shopping_items WHERE list_id=? AND COALESCE(done,0)=0 AND lower(trim(text))=lower(trim(?))",
                (payload["list_id"], payload["text"]),
            ).fetchone()
            if duplicate:
                return str(duplicate[0])
            order = connection.execute(
                "SELECT COALESCE(MAX(sort_order),0)+1 FROM shopping_items WHERE list_id=? AND COALESCE(done,0)=0",
                (payload["list_id"],),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO shopping_items(id,list_id,text,category,store,done,sort_order,owner,quantity,unit,created_at,source) "
                "VALUES(?,?,?,?,?,0,?,?,?,?,?,?)",
                (item_id, payload["list_id"], payload["text"], payload["category"], payload["store"], order, actor, payload["quantity"], payload["unit"], now, "Next"),
            )
            connection.execute("UPDATE shopping_lists SET updated_at=? WHERE id=?", (now, payload["list_id"]))
        return item_id

    def update(self, item_id: str, changes: dict[str, Any]) -> None:
        allowed = {key: value for key, value in changes.items() if value is not None}
        if not allowed:
            return
        columns = self.database.table_columns("shopping_items")
        allowed = {key: value for key, value in allowed.items() if key in columns and key in {"text", "quantity", "unit", "category", "store"}}
        if not allowed:
            return
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        params = [*allowed.values(), item_id]
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE shopping_items SET {assignments} WHERE id=?", params)
            if cursor.rowcount != 1:
                raise ValueError("Inköpsvaran saknas")

    def complete(self, item_id: str, done: bool) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE shopping_items SET done=?,completed_at=? WHERE id=?",
                (1 if done else 0, now if done else "", item_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Inköpsvaran saknas")
