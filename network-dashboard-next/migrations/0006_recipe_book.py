from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_columns, ensure_index


def upgrade(connection: sqlite3.Connection) -> None:
    ensure_columns(
        connection,
        "saved_dinners",
        (
            ("source_name", "TEXT NOT NULL DEFAULT ''"),
            ("image_url", "TEXT NOT NULL DEFAULT ''"),
            ("ingredients_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("steps_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("tags_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("servings", "TEXT NOT NULL DEFAULT ''"),
            ("favorite", "INTEGER NOT NULL DEFAULT 1"),
            ("manual", "INTEGER NOT NULL DEFAULT 0"),
            ("updated_at", "TEXT"),
        ),
    )
    ensure_index(
        connection,
        "idx_saved_dinners_favorite",
        "CREATE INDEX idx_saved_dinners_favorite ON saved_dinners(favorite,created_at)",
    )
