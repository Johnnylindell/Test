from __future__ import annotations

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS budget_sync_state(
            id INTEGER PRIMARY KEY CHECK(id=1),
            source_path TEXT NOT NULL DEFAULT '',
            auto_sync INTEGER NOT NULL DEFAULT 0,
            poll_seconds INTEGER NOT NULL DEFAULT 60,
            conflict_policy TEXT NOT NULL DEFAULT 'review',
            last_import_at TEXT NOT NULL DEFAULT '',
            last_export_at TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS budget_sync_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            direction TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            changed_cells INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO budget_sync_state(id) VALUES(1);
        """
    )
