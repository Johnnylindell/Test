from __future__ import annotations

import hashlib
import importlib.util
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    name: str
    checksum: str
    module: ModuleType
    path: Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover(directory: Path) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("[0-9][0-9][0-9][0-9]_*.py")):
        version, _, name = path.stem.partition("_")
        content = path.read_bytes()
        spec = importlib.util.spec_from_file_location(f"dashboard_migration_{version}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Kan inte ladda migration {path.name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not callable(getattr(module, "upgrade", None)):
            raise RuntimeError(f"Migration {path.name} saknar upgrade(connection)")
        migrations.append(Migration(version, name, hashlib.sha256(content).hexdigest(), module, path))
    return migrations


def ensure_journal(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations(
        version TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        checksum TEXT NOT NULL,
        started_at TEXT NOT NULL,
        applied_at TEXT,
        status TEXT NOT NULL,
        error TEXT NOT NULL DEFAULT ''
        )"""
    )


def status(database_path: Path, directory: Path) -> dict:
    migrations = discover(directory)
    with sqlite3.connect(database_path, timeout=20) as connection:
        connection.row_factory = sqlite3.Row
        ensure_journal(connection)
        applied = {row["version"]: dict(row) for row in connection.execute("SELECT * FROM schema_migrations")}
    rows = []
    for migration in migrations:
        saved = applied.get(migration.version)
        rows.append({
            "version": migration.version,
            "name": migration.name,
            "checksum": migration.checksum,
            "status": saved.get("status") if saved else "pending",
            "checksum_match": not saved or saved.get("checksum") == migration.checksum,
            "applied_at": saved.get("applied_at") if saved else None,
        })
    return {"migrations": rows, "pending": sum(row["status"] != "applied" for row in rows)}


def upgrade(database_path: Path, directory: Path) -> dict:
    applied_versions: list[str] = []
    with sqlite3.connect(database_path, timeout=30) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        ensure_journal(connection)
        for migration in discover(directory):
            existing = connection.execute(
                "SELECT checksum,status FROM schema_migrations WHERE version=?",
                (migration.version,),
            ).fetchone()
            if existing and existing[1] == "applied":
                if existing[0] != migration.checksum:
                    raise RuntimeError(f"Checksumma ändrad för tillämpad migration {migration.version}")
                continue
            started = _now()
            connection.execute(
                "INSERT INTO schema_migrations(version,name,checksum,started_at,status,error) VALUES(?,?,?,?,?,'') "
                "ON CONFLICT(version) DO UPDATE SET name=excluded.name,checksum=excluded.checksum,started_at=excluded.started_at,status=excluded.status,error=''",
                (migration.version, migration.name, migration.checksum, started, "running"),
            )
            connection.commit()
            try:
                connection.execute("BEGIN IMMEDIATE")
                migration.module.upgrade(connection)
                connection.execute(
                    "UPDATE schema_migrations SET status='applied',applied_at=?,error='' WHERE version=?",
                    (_now(), migration.version),
                )
                connection.commit()
                applied_versions.append(migration.version)
            except Exception as exc:
                connection.rollback()
                connection.execute(
                    "UPDATE schema_migrations SET status='failed',error=? WHERE version=?",
                    (str(exc)[:1000], migration.version),
                )
                connection.commit()
                raise
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    return {"ok": integrity == "ok", "integrity": integrity, "applied": applied_versions}
