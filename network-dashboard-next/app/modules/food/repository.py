from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if str(item).strip()] if isinstance(parsed, list) else []


class FoodRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def weekly_meals(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("weekly_meals"):
            return []
        columns = self.database.table_columns("weekly_meals")
        order = []
        if "week_start" in columns:
            order.append("week_start DESC")
        if "day" in columns:
            order.append("day")
        order_sql = ",".join(order) if order else "rowid DESC"
        return self.database.fetch_all(f"SELECT * FROM weekly_meals ORDER BY {order_sql} LIMIT 70")

    def saved_recipes(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("saved_dinners"):
            return []
        columns = self.database.table_columns("saved_dinners")
        order = "favorite DESC,created_at DESC" if "favorite" in columns else "created_at DESC"
        rows = self.database.fetch_all(f"SELECT * FROM saved_dinners ORDER BY {order} LIMIT 100")
        result = []
        for row in rows:
            clone = dict(row)
            clone["ingredients"] = _json_list(row.get("ingredients_json"))
            clone["steps"] = _json_list(row.get("steps_json"))
            clone["tags"] = _json_list(row.get("tags_json"))
            clone["favorite"] = bool(row.get("favorite", 1))
            clone["manual"] = bool(row.get("manual", 0))
            result.append(clone)
        return result

    def set_meal(self, payload: dict[str, Any]) -> None:
        required = {"week_start", "day", "meal_id", "title", "url", "source"}
        columns = self.database.table_columns("weekly_meals")
        if not required.issubset(columns):
            raise RuntimeError("weekly_meals har inte förväntat schema")
        fields = ["week_start", "day", "meal_id", "title", "url", "source"]
        values = [payload[name] for name in fields]
        if "updated_at" in columns:
            fields.append("updated_at")
            values.append(_now())
        placeholders = ",".join("?" for _ in fields)
        updates = ",".join(f'"{name}"=excluded."{name}"' for name in fields[2:])
        sql = (
            f'INSERT INTO weekly_meals({",".join(fields)}) VALUES({placeholders}) '
            f'ON CONFLICT(week_start,day) DO UPDATE SET {updates}'
        )
        self.database.execute(sql, values)

    def add_recipe(self, payload: dict[str, Any]) -> str:
        recipe_id = "recipe-" + secrets.token_hex(8)
        now = _now()
        self.database.execute(
            "INSERT INTO saved_dinners(id,title,source_url,source_name,image_url,ingredients_json,steps_json,tags_json,servings,favorite,manual,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                recipe_id,
                payload["title"].strip(),
                payload.get("source_url", ""),
                payload.get("source_name", "Manuellt"),
                payload.get("image_url", ""),
                json.dumps(payload.get("ingredients", []), ensure_ascii=False),
                json.dumps(payload.get("steps", []), ensure_ascii=False),
                json.dumps(payload.get("tags", []), ensure_ascii=False),
                payload.get("servings", ""),
                1 if payload.get("favorite", True) else 0,
                1,
                now,
                now,
            ),
        )
        return recipe_id

    def update_recipe(self, recipe_id: str, changes: dict[str, Any]) -> None:
        allowed: dict[str, Any] = {}
        mapping = {
            "title": "title",
            "source_url": "source_url",
            "source_name": "source_name",
            "image_url": "image_url",
            "servings": "servings",
            "favorite": "favorite",
        }
        for source, target in mapping.items():
            if source in changes and changes[source] is not None:
                value = changes[source]
                allowed[target] = 1 if source == "favorite" and value else (0 if source == "favorite" else value)
        for source, target in (("ingredients", "ingredients_json"), ("steps", "steps_json"), ("tags", "tags_json")):
            if source in changes and changes[source] is not None:
                allowed[target] = json.dumps(changes[source], ensure_ascii=False)
        if not allowed:
            return
        allowed["updated_at"] = _now()
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE saved_dinners SET {assignments} WHERE id=?", (*allowed.values(), recipe_id))
            if cursor.rowcount != 1:
                raise ValueError("Receptet finns inte")

    def delete_recipe(self, recipe_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM saved_dinners WHERE id=?", (recipe_id,))
            if cursor.rowcount != 1:
                raise ValueError("Receptet finns inte")

    def ingredients_to_shopping(self, ingredients: list[str], list_id: str, actor: str, source: str) -> list[str]:
        now = _now()
        added: list[str] = []
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO shopping_lists(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (list_id, "Inköp" if list_id == "shopping" else list_id, now, now),
            )
            for ingredient in ingredients[:200]:
                text = " ".join(str(ingredient or "").split())[:300]
                if not text:
                    continue
                duplicate = connection.execute(
                    "SELECT id FROM shopping_items WHERE list_id=? AND COALESCE(done,0)=0 AND lower(trim(text))=lower(trim(?))",
                    (list_id, text),
                ).fetchone()
                if duplicate:
                    added.append(str(duplicate[0]))
                    continue
                item_id = "item-" + secrets.token_hex(8)
                order = connection.execute(
                    "SELECT COALESCE(MAX(sort_order),0)+1 FROM shopping_items WHERE list_id=? AND COALESCE(done,0)=0",
                    (list_id,),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO shopping_items(id,list_id,text,category,store,done,sort_order,owner,quantity,unit,created_at,source) "
                    "VALUES(?,?,?,?,?,0,?,?,?,?,?,?)",
                    (item_id, list_id, text, "", "", order, actor, 1, "", now, source),
                )
                added.append(item_id)
        return added
