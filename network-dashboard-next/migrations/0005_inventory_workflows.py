from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_columns, ensure_index


def upgrade(connection: sqlite3.Connection) -> None:
    ensure_columns(
        connection,
        "inventory_inbox",
        (
            ("shopping_item_id", "TEXT NOT NULL DEFAULT ''"),
            ("name", "TEXT NOT NULL DEFAULT ''"),
            ("quantity", "REAL NOT NULL DEFAULT 1"),
            ("unit", "TEXT NOT NULL DEFAULT ''"),
            ("category", "TEXT NOT NULL DEFAULT ''"),
            ("store", "TEXT NOT NULL DEFAULT ''"),
            ("suggested_location", "TEXT NOT NULL DEFAULT 'other'"),
            ("suggested_shelf", "TEXT NOT NULL DEFAULT ''"),
        ),
    )
    ensure_columns(connection, "inventory_shelves", (("created_at", "TEXT"),))
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_placements(
            id TEXT PRIMARY KEY,
            shopping_item_id TEXT NOT NULL DEFAULT '',
            inventory_item_id TEXT NOT NULL DEFAULT '',
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT '',
            placed_at TEXT,
            reverted_at TEXT NOT NULL DEFAULT '',
            revert_mode TEXT NOT NULL DEFAULT ''
        )
        """
    )
    ensure_index(
        connection,
        "idx_inventory_inbox_shopping",
        "CREATE INDEX idx_inventory_inbox_shopping ON inventory_inbox(shopping_item_id)",
    )
    ensure_index(
        connection,
        "idx_inventory_placements_shopping",
        "CREATE INDEX idx_inventory_placements_shopping ON inventory_placements(shopping_item_id,reverted_at)",
    )
