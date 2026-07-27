from __future__ import annotations

import sqlite3
from collections.abc import Iterable


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(connection, table):
        return set()
    safe = table.replace('"', '""')
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{safe}")')}


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column in table_columns(connection, table):
        return
    safe_table = table.replace('"', '""')
    safe_column = column.replace('"', '""')
    connection.execute(f'ALTER TABLE "{safe_table}" ADD COLUMN "{safe_column}" {definition}')


def ensure_columns(
    connection: sqlite3.Connection,
    table: str,
    columns: Iterable[tuple[str, str]],
) -> None:
    for name, definition in columns:
        ensure_column(connection, table, name, definition)


def ensure_index(connection: sqlite3.Connection, name: str, sql: str) -> None:
    existing = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    if not existing:
        connection.execute(sql)
