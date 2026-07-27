from __future__ import annotations

from typing import Any

from app.database.database import Database
from app.modules.common import as_bool, as_text, first_present


class PlanningRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def reminders(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.database.table_exists("home_reminders"):
            return []
        columns = self.database.table_columns("home_reminders")
        order_parts = []
        if "done" in columns:
            order_parts.append("done")
        if "due_at" in columns:
            order_parts.append("due_at")
        elif "remind_at" in columns:
            order_parts.append("remind_at")
        order_parts.append("rowid DESC")
        rows = self.database.fetch_all(
            f"SELECT * FROM home_reminders ORDER BY {', '.join(order_parts)} LIMIT ?",
            (limit,),
        )
        return [{
            "id": as_text(first_present(row, "id", "reminder_id"), limit=120),
            "title": as_text(first_present(row, "title", "text", "message"), limit=300),
            "owner": as_text(first_present(row, "owner", "assigned_to", "user"), limit=80),
            "due_at": as_text(first_present(row, "due_at", "remind_at", "scheduled_at"), limit=80),
            "done": as_bool(first_present(row, "done", "completed", default=False)),
            "source": "home_reminders",
        } for row in rows]

    def routine_rules(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("recurring_routine_rules"):
            return []
        columns = self.database.table_columns("recurring_routine_rules")
        order = "sort_order, rowid" if "sort_order" in columns else "rowid"
        rows = self.database.fetch_all(f"SELECT * FROM recurring_routine_rules ORDER BY {order}")
        return [{
            "id": as_text(first_present(row, "id", "rule_id"), limit=120),
            "title": as_text(first_present(row, "title", "text", "name"), limit=300),
            "owner": as_text(first_present(row, "owner", "assigned_to"), limit=80),
            "active": as_bool(first_present(row, "active", "enabled", default=True)),
            "schedule": as_text(first_present(row, "schedule", "rrule", "days"), limit=300),
        } for row in rows]

    def routine_instances(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.database.table_exists("recurring_routine_instances"):
            return []
        columns = self.database.table_columns("recurring_routine_instances")
        order = "scheduled_for DESC" if "scheduled_for" in columns else "rowid DESC"
        rows = self.database.fetch_all(
            f"SELECT * FROM recurring_routine_instances ORDER BY {order} LIMIT ?",
            (limit,),
        )
        return [{
            "id": as_text(first_present(row, "id", "instance_id"), limit=120),
            "rule_id": as_text(first_present(row, "rule_id", "routine_id"), limit=120),
            "title": as_text(first_present(row, "title", "text", "name"), limit=300),
            "scheduled_for": as_text(first_present(row, "scheduled_for", "due_at", "date"), limit=80),
            "done": as_bool(first_present(row, "done", "completed", default=False)),
        } for row in rows]

    def checklist_items(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("home_checklist_items"):
            return []
        columns = self.database.table_columns("home_checklist_items")
        order = "sort_order, rowid" if "sort_order" in columns else "rowid"
        rows = self.database.fetch_all(f"SELECT * FROM home_checklist_items ORDER BY {order}")
        return [{
            "id": as_text(first_present(row, "id", "item_id"), limit=120),
            "checklist_id": as_text(first_present(row, "checklist_id", "list_id"), limit=120),
            "title": as_text(first_present(row, "text", "title", "name"), limit=300),
            "done": as_bool(first_present(row, "done", "completed", default=False)),
            "source": "home_checklist_items",
        } for row in rows]
