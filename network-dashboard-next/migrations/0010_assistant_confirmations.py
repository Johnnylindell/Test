from __future__ import annotations

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS assistant_confirmations(
            token_hash TEXT PRIMARY KEY,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            consumed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_assistant_confirmations_consumed
            ON assistant_confirmations(consumed_at DESC);
        """
    )
