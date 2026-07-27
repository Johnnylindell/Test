from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.integrations.notification_delivery import NotificationDeliveryAdapter
from app.modules.backups.service import BackupService


def test_backup_create_verify_and_restore(tmp_path: Path) -> None:
    database = tmp_path / "next.sqlite3"
    backup_dir = tmp_path / "backups"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE values_table(value TEXT NOT NULL)")
        connection.execute("INSERT INTO values_table(value) VALUES('before')")

    service = BackupService(database, backup_dir)
    backup = service.create("test")
    assert service.verify(backup["name"])["ok"] is True

    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE values_table SET value='after'")

    restored = service.restore(backup["name"])
    assert restored["ok"] is True
    assert restored["safety_backup"]["name"] != backup["name"]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM values_table").fetchone()[0] == "before"


def test_backup_rejects_paths_outside_directory(tmp_path: Path) -> None:
    database = tmp_path / "next.sqlite3"
    sqlite3.connect(database).close()
    service = BackupService(database, tmp_path / "backups")

    with pytest.raises(ValueError):
        service.verify("../outside.sqlite3")


def test_notification_delivery_requires_vapid_key(tmp_path: Path) -> None:
    database = tmp_path / "next.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT);
            CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT);
            CREATE TABLE push_subscriptions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL UNIQUE,
                user TEXT NOT NULL DEFAULT '',
                subscription TEXT NOT NULL,
                created_at TEXT
            );
            """
        )

    from app.database.database import Database

    adapter = NotificationDeliveryAdapter(Database(database))
    result = adapter.deliver(title="Test", message="Meddelande", send_push=True)
    assert result["ok"] is False
    assert "VAPID" in result["push"]["error"]
