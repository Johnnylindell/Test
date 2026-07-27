from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database.database import Database
from app.database.migrations import upgrade
from app.modules.budget.repository import BudgetRepository
from app.modules.notifications.evaluator import SmartNotificationEvaluator
from app.modules.notifications.repository import NotificationsRepository


def migrated_database(tmp_path: Path) -> Database:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "dashboard.sqlite3"
    sqlite3.connect(path).close()
    upgrade(path, Path(__file__).resolve().parents[1] / "migrations")
    return Database(path)


def seed_budget(database: Database) -> None:
    with database.transaction() as connection:
        cursor = connection.execute(
            "INSERT INTO budget_sheets(name,kind,sort_order,max_row,max_col) VALUES('Januari','month',1,40,12)"
        )
        sheet_id = int(cursor.lastrowid)
        cells = [
            (18, 2, "Lön"),
            (18, 3, "3000"),
            (18, 5, "Mat"),
            (18, 6, "500"),
            (18, 7, "650"),
            (18, 9, "Buffert"),
            (18, 10, "200"),
        ]
        connection.executemany(
            "INSERT INTO budget_cells(sheet_id,row_num,col_num,value,updated_at) VALUES(?,?,?,?,datetime('now'))",
            [(sheet_id, row, col, value) for row, col, value in cells],
        )


def test_budget_year_and_roundtrip(tmp_path: Path) -> None:
    source = migrated_database(tmp_path / "source")
    seed_budget(source)
    repository = BudgetRepository(source)
    year = repository.year_summary()
    assert year["totals"] == {
        "income": 3000.0,
        "expenses": 650.0,
        "savings": 200.0,
        "balance": 2150.0,
    }
    exported = repository.export_payload()

    target = migrated_database(tmp_path / "target")
    result = BudgetRepository(target).import_payload(exported, replace=True)
    assert result["changed_cells"] == 7
    imported = BudgetRepository(target).overview("Januari")
    assert imported["totals"]["expenses_actual"] == 650.0
    assert imported["totals"]["balance_actual"] == 2150.0


def test_smart_notification_cooldown(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    now = datetime.now(timezone.utc)
    database.execute(
        "INSERT INTO home_reminders(id,title,owner,remind_at,note,done,created_at) VALUES(?,?,?,?,?,0,?)",
        ("r1", "Hämta paket", "johnny", (now + timedelta(minutes=5)).isoformat(), "", now.isoformat()),
    )
    repository = NotificationsRepository(database)
    repository.save_rules([
        {
            "id": "soon",
            "event": "smart_calendar_soon",
            "enabled": True,
            "target": "johnny",
            "severity": "normal",
            "template": "{title} {when}",
            "cooldown_minutes": 60,
            "conditions": {},
        }
    ])
    evaluator = SmartNotificationEvaluator(database, repository)
    first = evaluator.evaluate(trigger="manual")
    second = evaluator.evaluate(trigger="manual")
    assert first["created_count"] == 1
    assert second["created_count"] == 0
    assert repository.alerts("johnny")[0]["message"].startswith("Hämta paket")
