from __future__ import annotations

from typing import Any

from app.database.database import Database


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
        order = "created_at DESC" if "created_at" in columns else "rowid DESC"
        return self.database.fetch_all(f"SELECT * FROM saved_dinners ORDER BY {order} LIMIT 100")

    def set_meal(self, payload: dict[str, Any]) -> None:
        required = {"week_start", "day", "meal_id", "title", "url", "source"}
        columns = self.database.table_columns("weekly_meals")
        if not required.issubset(columns):
            raise RuntimeError("weekly_meals har inte förväntat schema")
        updated_column = "updated_at" if "updated_at" in columns else None
        fields = ["week_start", "day", "meal_id", "title", "url", "source"]
        values = [payload[name] for name in fields]
        if updated_column:
            fields.append(updated_column)
            values.append("now")
        placeholders = ",".join("?" for _ in fields)
        updates = ",".join(f'"{name}"=excluded."{name}"' for name in fields[2:])
        sql = (
            f'INSERT INTO weekly_meals({",".join(fields)}) VALUES({placeholders}) '
            f'ON CONFLICT(week_start,day) DO UPDATE SET {updates}'
        )
        with self.database.transaction() as connection:
            if updated_column:
                values[-1] = connection.execute("SELECT datetime('now')").fetchone()[0]
            connection.execute(sql, values)
