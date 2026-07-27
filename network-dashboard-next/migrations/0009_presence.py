from __future__ import annotations

import sqlite3


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS presence_devices(
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            source_hash TEXT NOT NULL UNIQUE,
            notify_arrival INTEGER NOT NULL DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            initialized INTEGER NOT NULL DEFAULT 0,
            present INTEGER NOT NULL DEFAULT 0,
            last_seen TEXT NOT NULL DEFAULT '',
            last_checked TEXT NOT NULL DEFAULT '',
            last_transition_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_presence_devices_owner
            ON presence_devices(owner, active, present);

        CREATE TABLE IF NOT EXISTS presence_events(
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            owner TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(device_id) REFERENCES presence_devices(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_presence_events_owner_time
            ON presence_events(owner, created_at DESC);
        """
    )
