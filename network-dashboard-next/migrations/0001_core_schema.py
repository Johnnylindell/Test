from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_columns


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS app_settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS app_json_state(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS admin_sessions(
            token TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            expires_at_epoch REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS family_profiles(
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS family_lists(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS family_list_items(
            id TEXT PRIMARY KEY,
            list_id TEXT NOT NULL,
            text TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(list_id) REFERENCES family_lists(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS family_notes(
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT '',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS home_reminders(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT '',
            remind_at TEXT,
            note TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS home_checklist_items(
            id TEXT PRIMARY KEY,
            checklist_id TEXT NOT NULL DEFAULT 'home',
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS recurring_routine_rules(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            assigned_to TEXT NOT NULL DEFAULT '',
            schedule TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS recurring_routine_instances(
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            title TEXT NOT NULL,
            scheduled_for TEXT,
            done INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    ensure_columns(connection, "family_list_items", (("owner", "TEXT NOT NULL DEFAULT ''"), ("done", "INTEGER NOT NULL DEFAULT 0"), ("sort_order", "INTEGER NOT NULL DEFAULT 0")))
    ensure_columns(connection, "admin_sessions", (("expires_at_epoch", "REAL NOT NULL DEFAULT 0"),))
