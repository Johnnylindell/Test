from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BackupService:
    def __init__(self, database_path: Path, backup_dir: Path) -> None:
        self.database_path = database_path.expanduser().resolve()
        self.backup_dir = backup_dir.expanduser().resolve()

    def _ensure_dir(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_name(self, name: str) -> Path:
        candidate = (self.backup_dir / Path(name).name).resolve()
        if candidate.parent != self.backup_dir or candidate.suffix != ".sqlite3":
            raise ValueError("Ogiltigt backupnamn")
        return candidate

    @staticmethod
    def _integrity(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(path)
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=20) as connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0])

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def create(self, label: str = "manual") -> dict[str, Any]:
        if not self.database_path.is_file():
            raise FileNotFoundError(self.database_path)
        self._ensure_dir()
        clean_label = "".join(ch for ch in label.strip().lower() if ch.isalnum() or ch in "-_")[:40]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.backup_dir / f"{self.database_path.stem}-{clean_label or 'manual'}-{stamp}.sqlite3"
        with sqlite3.connect(self.database_path, timeout=30) as source:
            with sqlite3.connect(target, timeout=30) as destination:
                source.backup(destination)
        integrity = self._integrity(target)
        if integrity != "ok":
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Backupverifieringen misslyckades: {integrity}")
        return self.describe(target)

    def describe(self, path: Path) -> dict[str, Any]:
        stat = path.stat()
        return {
            "name": path.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "sha256": self._sha256(path),
        }

    def list(self) -> list[dict[str, Any]]:
        self._ensure_dir()
        rows = []
        for path in sorted(self.backup_dir.glob("*.sqlite3"), key=lambda value: value.stat().st_mtime, reverse=True):
            try:
                rows.append(self.describe(path))
            except OSError:
                continue
        return rows[:200]

    def verify(self, name: str) -> dict[str, Any]:
        path = self._resolve_name(name)
        integrity = self._integrity(path)
        return {"ok": integrity == "ok", "integrity": integrity, "backup": self.describe(path)}

    def delete(self, name: str) -> bool:
        path = self._resolve_name(name)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def restore(self, name: str) -> dict[str, Any]:
        source_path = self._resolve_name(name)
        integrity = self._integrity(source_path)
        if integrity != "ok":
            raise RuntimeError(f"Backupen är skadad: {integrity}")
        safety = self.create("pre-restore")
        temporary = self.database_path.with_suffix(self.database_path.suffix + ".restore")
        temporary.unlink(missing_ok=True)
        with sqlite3.connect(source_path, timeout=30) as source:
            with sqlite3.connect(temporary, timeout=30) as destination:
                source.backup(destination)
        restored_integrity = self._integrity(temporary)
        if restored_integrity != "ok":
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Återställningskopian är skadad: {restored_integrity}")
        temporary.replace(self.database_path)
        return {
            "ok": True,
            "restored_from": source_path.name,
            "safety_backup": safety,
            "integrity": restored_integrity,
        }
