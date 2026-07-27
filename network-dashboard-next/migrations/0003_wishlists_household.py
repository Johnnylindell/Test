from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_index


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS wishlist_items(
            id TEXT PRIMARY KEY,
            member TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            price REAL,
            reserved_by TEXT NOT NULL DEFAULT '',
            purchased INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS household_places(
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            note TEXT NOT NULL DEFAULT '',
            info TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            updated_by TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS household_items(
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            info TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            updated_by TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS household_log(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Händelse',
            note TEXT NOT NULL DEFAULT '',
            actor TEXT NOT NULL DEFAULT '',
            created_at TEXT
        );
        """
    )
    ensure_index(connection, "idx_wishlist_member", "CREATE INDEX idx_wishlist_member ON wishlist_items(member,purchased,created_at)")
    ensure_index(connection, "idx_household_items_location", "CREATE INDEX idx_household_items_location ON household_items(location,name)")
    ensure_index(connection, "idx_household_log_created", "CREATE INDEX idx_household_log_created ON household_log(created_at DESC)")
