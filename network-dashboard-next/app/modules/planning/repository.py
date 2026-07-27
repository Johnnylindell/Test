from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database
from app.modules.common import as_bool, as_text, first_present


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            "note": as_text(first_present(row, "note", "description"), limit=1000),
            "done": as_bool(first_present(row, "done", "completed", default=False)),
            "source": "home_reminders",
        } for row in rows]

    def add_reminder(self, data: dict[str, Any], actor: str) -> str:
        reminder_id = secrets.token_hex(8)
        owner = str(data.get("owner") or actor)
        self.database.execute(
            "INSERT INTO home_reminders(id,title,owner,remind_at,note,done,created_at) VALUES(?,?,?,?,?,0,?)",
            (reminder_id, data["title"].strip(), owner, data.get("remind_at", ""), data.get("note", ""), _now()),
        )
        return reminder_id

    def update_reminder(self, reminder_id: str, changes: dict[str, Any]) -> None:
        allowed = {key: value for key, value in changes.items() if value is not None and key in {"title", "owner", "remind_at", "note", "done"}}
        if "done" in allowed:
            allowed["done"] = 1 if allowed["done"] else 0
        if not allowed:
            return
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE home_reminders SET {assignments} WHERE id=?", (*allowed.values(), reminder_id))
            if cursor.rowcount != 1:
                raise ValueError("Påminnelsen finns inte")

    def delete_reminder(self, reminder_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM home_reminders WHERE id=?", (reminder_id,))
            if cursor.rowcount != 1:
                raise ValueError("Påminnelsen finns inte")

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

    def add_routine_rule(self, data: dict[str, Any]) -> str:
        rule_id = secrets.token_hex(8)
        order = self.database.count("recurring_routine_rules")
        self.database.execute(
            "INSERT INTO recurring_routine_rules(id,title,assigned_to,schedule,active,sort_order) VALUES(?,?,?,?,?,?)",
            (rule_id, data["title"].strip(), data.get("assigned_to", ""), data.get("schedule", ""), 1 if data.get("active", True) else 0, order),
        )
        return rule_id

    def update_routine_rule(self, rule_id: str, changes: dict[str, Any]) -> None:
        allowed = {key: value for key, value in changes.items() if value is not None and key in {"title", "assigned_to", "schedule", "active"}}
        if "active" in allowed:
            allowed["active"] = 1 if allowed["active"] else 0
        if not allowed:
            return
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE recurring_routine_rules SET {assignments} WHERE id=?", (*allowed.values(), rule_id))
            if cursor.rowcount != 1:
                raise ValueError("Rutinen finns inte")

    def delete_routine_rule(self, rule_id: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM recurring_routine_instances WHERE rule_id=?", (rule_id,))
            cursor = connection.execute("DELETE FROM recurring_routine_rules WHERE id=?", (rule_id,))
            if cursor.rowcount != 1:
                raise ValueError("Rutinen finns inte")

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

    def set_instance_done(self, instance_id: str, done: bool) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("UPDATE recurring_routine_instances SET done=? WHERE id=?", (1 if done else 0, instance_id))
            if cursor.rowcount != 1:
                raise ValueError("Rutintillfället finns inte")

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

    def set_checklist_done(self, item_id: str, done: bool) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("UPDATE home_checklist_items SET done=? WHERE id=?", (1 if done else 0, item_id))
            if cursor.rowcount != 1:
                raise ValueError("Checklistpunkten finns inte")
