from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_index


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS forget_items(
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            due_at TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            completed_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS home_quest_completions(
            quest_date TEXT NOT NULL,
            quest_id TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT '',
            completed_at TEXT,
            PRIMARY KEY(quest_date,quest_id,owner)
        );
        """
    )
    ensure_index(connection, "idx_forget_items_owner", "CREATE INDEX idx_forget_items_owner ON forget_items(owner,done,due_at)")
