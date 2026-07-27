#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.database.migrations import status, upgrade


def backup_database(database: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{database.stem}-{stamp}.sqlite3"
    with sqlite3.connect(database, timeout=30) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target


def restore_database(database: Path, backup: Path) -> None:
    if not backup.is_file():
        raise FileNotFoundError(backup)
    with sqlite3.connect(backup, timeout=30) as source:
        integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Backupen är skadad: {integrity}")
    temporary = database.with_suffix(database.suffix + ".restore")
    shutil.copy2(backup, temporary)
    temporary.replace(database)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("status", "backup", "upgrade", "restore"))
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--migrations", type=Path, default=Path(__file__).resolve().parents[1] / "migrations")
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / ".local" / "share" / "network-dashboard-next" / "backups")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()

    database = args.database.expanduser().resolve()
    if args.command != "restore" and not database.is_file():
        raise FileNotFoundError(database)

    if args.command == "status":
        result = status(database, args.migrations)
    elif args.command == "backup":
        result = {"ok": True, "backup": str(backup_database(database, args.backup_dir))}
    elif args.command == "upgrade":
        backup = backup_database(database, args.backup_dir)
        try:
            result = upgrade(database, args.migrations) | {"backup": str(backup)}
        except Exception:
            restore_database(database, backup)
            raise
    else:
        if args.backup is None:
            parser.error("restore kräver --backup")
        restore_database(database, args.backup.expanduser().resolve())
        result = {"ok": True, "restored": str(args.backup), "database": str(database)}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
