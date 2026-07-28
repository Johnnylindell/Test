from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.migrations import discover, status, upgrade
from app.main import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "dashboard.sqlite3"
    sqlite3.connect(database).close()
    expected = [migration.version for migration in discover(ROOT / "migrations")]

    first = upgrade(database, ROOT / "migrations")
    second = upgrade(database, ROOT / "migrations")

    assert first["ok"] is True
    assert first["applied"] == expected
    assert second["applied"] == []
    report = status(database, ROOT / "migrations")
    assert report["pending"] == 0
    assert all(row["status"] == "applied" for row in report["migrations"])
    assert all(row["checksum_match"] for row in report["migrations"])

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "schema_migrations",
        "shopping_items",
        "inventory_items",
        "budget_cells",
        "presence_devices",
        "assistant_confirmations",
        "bank_transactions",
        "managed_services",
    } <= tables


def test_migrations_upgrade_legacy_routine_instance_columns(tmp_path: Path) -> None:
    database = tmp_path / "legacy-dashboard.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE recurring_routine_instances(
                id TEXT PRIMARY KEY,
                rule_id TEXT,
                title TEXT,
                due_at TEXT,
                completed INTEGER
            );
            INSERT INTO recurring_routine_instances(id,rule_id,title,due_at,completed)
            VALUES('legacy-1','rule-1','Legacy-rutin','2026-07-28',1);
            """
        )

    result = upgrade(database, ROOT / "migrations")

    assert result["ok"] is True
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(recurring_routine_instances)")}
        row = connection.execute(
            "SELECT scheduled_for,done FROM recurring_routine_instances WHERE id='legacy-1'"
        ).fetchone()
        index = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_routine_instances_due'"
        ).fetchone()
    assert {"scheduled_for", "done"} <= columns
    assert row == ("2026-07-28", 1)
    assert index == (1,)


def test_retired_legacy_endpoint_returns_replacement(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "dashboard.sqlite3"
    sqlite3.connect(database).close()
    upgrade(database, ROOT / "migrations")
    monkeypatch.setattr("app.main.settings", replace(settings, database_path=database, port=0))
    app = create_app()

    response = TestClient(app).get("/api/budget")

    assert response.status_code == 410
    assert response.json()["replacement"] == "/api/v2/budget/overview"
    assert response.headers["deprecation"] == "true"
