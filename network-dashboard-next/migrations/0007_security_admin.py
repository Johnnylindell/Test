from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_index


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS login_attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            attempted_at_epoch REAL NOT NULL,
            success INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS admin_audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL DEFAULT 'admin',
            action TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        """
    )
    ensure_index(
        connection,
        "idx_login_attempts_source_time",
        "CREATE INDEX idx_login_attempts_source_time ON login_attempts(source,attempted_at_epoch)",
    )
    ensure_index(
        connection,
        "idx_admin_audit_created",
        "CREATE INDEX idx_admin_audit_created ON admin_audit_log(created_at DESC)",
    )
