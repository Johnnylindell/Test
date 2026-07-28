from __future__ import annotations

import sqlite3

from app.database.schema_helpers import ensure_columns, ensure_index, table_columns


def _upgrade_routine_instances(connection: sqlite3.Connection) -> None:
    """Normalize legacy routine instances before creating the due-state index."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS recurring_routine_instances(
        id TEXT PRIMARY KEY,
        rule_id TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL DEFAULT '',
        scheduled_for TEXT NOT NULL DEFAULT '',
        done INTEGER NOT NULL DEFAULT 0
        )"""
    )
    legacy_columns = table_columns(connection, "recurring_routine_instances")
    ensure_columns(
        connection,
        "recurring_routine_instances",
        (
            ("scheduled_for", "TEXT NOT NULL DEFAULT ''"),
            ("done", "INTEGER NOT NULL DEFAULT 0"),
        ),
    )

    for source in ("due_at", "date", "scheduled_at"):
        if source in legacy_columns:
            safe_source = source.replace('"', '""')
            connection.execute(
                f'''UPDATE recurring_routine_instances
                SET scheduled_for=CASE
                    WHEN scheduled_for IS NULL OR trim(scheduled_for)='' THEN COALESCE("{safe_source}", '')
                    ELSE scheduled_for
                END'''
            )
            break

    if "completed" in legacy_columns:
        connection.execute(
            """UPDATE recurring_routine_instances
            SET done=CASE
                WHEN lower(trim(CAST(completed AS TEXT))) IN ('1','true','yes','on') THEN 1
                ELSE done
            END"""
        )


def upgrade(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS shopping_lists(
            id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT,updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS shopping_items(
            id TEXT PRIMARY KEY,list_id TEXT NOT NULL,text TEXT NOT NULL,category TEXT NOT NULL DEFAULT '',
            store TEXT NOT NULL DEFAULT '',done INTEGER NOT NULL DEFAULT 0,sort_order INTEGER NOT NULL DEFAULT 0,
            owner TEXT NOT NULL DEFAULT '',quantity REAL NOT NULL DEFAULT 1,unit TEXT NOT NULL DEFAULT '',
            created_at TEXT,completed_at TEXT NOT NULL DEFAULT '',source TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(list_id) REFERENCES shopping_lists(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS inventory_items(
            id TEXT PRIMARY KEY,name TEXT NOT NULL,quantity REAL NOT NULL DEFAULT 0,unit TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT 'other',shelf TEXT NOT NULL DEFAULT '',usual_location TEXT NOT NULL DEFAULT '',
            usual_shelf TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',created_at TEXT,updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS inventory_inbox(
            id TEXT PRIMARY KEY,text TEXT NOT NULL DEFAULT '',created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS inventory_shelves(
            id TEXT PRIMARY KEY,location TEXT NOT NULL,name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory_shopping_suggestions(
            id TEXT PRIMARY KEY,item_id TEXT NOT NULL,text TEXT NOT NULL,quantity REAL NOT NULL DEFAULT 1,
            unit TEXT NOT NULL DEFAULT '',reason TEXT NOT NULL DEFAULT '',created_at TEXT,dismissed_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS weekly_meals(
            week_start TEXT NOT NULL,day TEXT NOT NULL,meal_id TEXT NOT NULL DEFAULT '',title TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',source TEXT NOT NULL DEFAULT '',updated_at TEXT,
            PRIMARY KEY(week_start,day)
        );
        CREATE TABLE IF NOT EXISTS saved_dinners(
            id TEXT PRIMARY KEY,title TEXT NOT NULL,source_url TEXT NOT NULL DEFAULT '',created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS budget_sheets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,kind TEXT NOT NULL DEFAULT 'month',
            sort_order INTEGER NOT NULL DEFAULT 0,max_row INTEGER NOT NULL DEFAULT 40,max_col INTEGER NOT NULL DEFAULT 12
        );
        CREATE TABLE IF NOT EXISTS budget_cells(
            sheet_id INTEGER NOT NULL,row_num INTEGER NOT NULL,col_num INTEGER NOT NULL,value TEXT NOT NULL DEFAULT '',updated_at TEXT,
            PRIMARY KEY(sheet_id,row_num,col_num),FOREIGN KEY(sheet_id) REFERENCES budget_sheets(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS push_subscriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,endpoint TEXT NOT NULL UNIQUE,user TEXT NOT NULL DEFAULT '',
            subscription TEXT NOT NULL,created_at TEXT
        );
        """
    )
    ensure_columns(connection, "shopping_items", (("quantity", "REAL NOT NULL DEFAULT 1"), ("unit", "TEXT NOT NULL DEFAULT ''"), ("completed_at", "TEXT NOT NULL DEFAULT ''"), ("source", "TEXT NOT NULL DEFAULT ''")))
    _upgrade_routine_instances(connection)
    ensure_index(connection, "idx_shopping_items_active", "CREATE INDEX idx_shopping_items_active ON shopping_items(list_id,done,sort_order)")
    ensure_index(connection, "idx_inventory_location", "CREATE INDEX idx_inventory_location ON inventory_items(location,shelf,name)")
    ensure_index(connection, "idx_routine_instances_due", "CREATE INDEX idx_routine_instances_due ON recurring_routine_instances(done,scheduled_for)")
    connection.execute("INSERT OR IGNORE INTO shopping_lists(id,title,created_at,updated_at) VALUES('shopping','Inköp',datetime('now'),datetime('now'))")
