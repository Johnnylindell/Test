from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            connection = sqlite3.connect(
                f"file:{self.path}?mode=ro",
                uri=True,
                timeout=20,
                check_same_thread=False,
            )
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=20, check_same_thread=False)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA busy_timeout=20000")
            connection.execute("PRAGMA foreign_keys=ON")
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        with self._connect(readonly=True) as connection:
            row = connection.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self._connect(readonly=True) as connection:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def fetch_value(self, sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
        with self._connect(readonly=True) as connection:
            row = connection.execute(sql, params).fetchone()
            return row[0] if row else default

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(sql, params)
            return int(cursor.lastrowid or 0)

    def executemany(self, sql: str, rows: Iterable[Sequence[Any]]) -> None:
        with self.transaction() as connection:
            connection.executemany(sql, rows)

    def table_exists(self, table: str) -> bool:
        row = self.fetch_one(
            "SELECT 1 AS present FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return bool(row)

    def table_columns(self, table: str) -> set[str]:
        if not self.table_exists(table):
            return set()
        safe_table = table.replace('"', '""')
        with self._connect(readonly=True) as connection:
            return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{safe_table}")')}

    def count(self, table: str, where: str = "", params: Sequence[Any] = ()) -> int:
        if not self.table_exists(table):
            return 0
        safe_table = table.replace('"', '""')
        sql = f'SELECT COUNT(*) FROM "{safe_table}"'
        if where:
            sql += f" WHERE {where}"
        return int(self.fetch_value(sql, params, 0) or 0)

    def get_setting(self, key: str, default: Any = None) -> Any:
        if not self.table_exists("app_settings"):
            return default
        row = self.fetch_one("SELECT value FROM app_settings WHERE key=?", (key,))
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            return row["value"]

    def get_json_state(self, key: str, default: Any = None) -> Any:
        if not self.table_exists("app_json_state"):
            return default
        row = self.fetch_one("SELECT value FROM app_json_state WHERE key=?", (key,))
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            return default

    def set_json_state(self, key: str, value: Any) -> None:
        if not self.table_exists("app_json_state"):
            raise RuntimeError("app_json_state saknas; kör databasmigreringen först")
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO app_json_state(key,value,updated_at) VALUES(?,?,datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (key, payload),
            )

    def update_json_state(self, key: str, updater: Callable[[Any], Any], default: Any = None) -> Any:
        if not self.table_exists("app_json_state"):
            raise RuntimeError("app_json_state saknas; kör databasmigreringen först")
        with self.transaction() as connection:
            row = connection.execute("SELECT value FROM app_json_state WHERE key=?", (key,)).fetchone()
            current = default
            if row:
                try:
                    current = json.loads(row[0])
                except (TypeError, json.JSONDecodeError):
                    current = default
            updated = updater(current)
            payload = json.dumps(updated, ensure_ascii=False, separators=(",", ":"))
            connection.execute(
                "INSERT INTO app_json_state(key,value,updated_at) VALUES(?,?,datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (key, payload),
            )
            return updated

    def integrity_check(self) -> str:
        with self._connect(readonly=True) as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
            return str(row[0]) if row else "unknown"
