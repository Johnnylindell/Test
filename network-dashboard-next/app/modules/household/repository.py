from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_path(value: str) -> str:
    return " / ".join(part.strip() for part in str(value or "").split("/") if part.strip())[:240]


def place_id(path: str) -> str:
    return "place-" + hashlib.sha256(path.casefold().encode()).hexdigest()[:16]


class HouseholdRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def overview(self, query: str = "") -> dict[str, Any]:
        if not self.database.table_exists("household_items"):
            return {"ok": False, "items": [], "places": [], "log": [], "reason": "schema_missing"}
        items = self.database.fetch_all("SELECT * FROM household_items ORDER BY name COLLATE NOCASE")
        q = query.strip().casefold()
        if q:
            items = [row for row in items if q in " ".join(str(row.get(key) or "") for key in ("name", "location", "category", "owner", "note", "info")).casefold()]
        places = self.database.fetch_all("SELECT * FROM household_places ORDER BY path COLLATE NOCASE")
        log = self.database.fetch_all("SELECT * FROM household_log ORDER BY created_at DESC LIMIT 120")
        for row in places:
            path = str(row.get("path") or "")
            row["item_count"] = sum(str(item.get("location") or "") == path or str(item.get("location") or "").startswith(path + " / ") for item in items)
            row["direct_item_count"] = sum(str(item.get("location") or "") == path for item in items)
        return {"ok": True, "items": items[:500], "places": places[:500], "log": log, "totals": {"items": len(items), "places": len(places), "log": len(log)}}

    def upsert_place(self, data: dict[str, Any], actor: str) -> str:
        path = canonical_path(data["path"])
        if not path:
            raise ValueError("Plats krävs")
        old_path = canonical_path(data.get("old_path", ""))
        pid = place_id(path)
        now = _now()
        with self.database.transaction() as connection:
            if old_path and old_path != path:
                old_prefix = old_path + " / "
                rows = connection.execute("SELECT id,location FROM household_items").fetchall()
                for row in rows:
                    location = str(row[1] or "")
                    if location == old_path:
                        new_location = path
                    elif location.startswith(old_prefix):
                        new_location = path + " / " + location[len(old_prefix):]
                    else:
                        continue
                    connection.execute("UPDATE household_items SET location=?,updated_at=?,updated_by=? WHERE id=?", (new_location, now, actor, row[0]))
                connection.execute("DELETE FROM household_places WHERE path=?", (old_path,))
            name = path.split(" / ")[-1]
            connection.execute(
                "INSERT INTO household_places(id,name,path,note,info,image_url,created_at,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(path) DO UPDATE SET name=excluded.name,note=excluded.note,info=excluded.info,image_url=excluded.image_url,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
                (pid, name, path, data.get("note", ""), data.get("info", ""), data.get("image_url", ""), now, now, actor),
            )
        return pid

    def delete_place(self, path: str) -> None:
        target = canonical_path(path)
        with self.database.transaction() as connection:
            exists = connection.execute("SELECT 1 FROM household_items WHERE location=? OR location LIKE ?", (target, target + " / %")).fetchone()
            if exists:
                raise ValueError("Platsen innehåller saker")
            cursor = connection.execute("DELETE FROM household_places WHERE path=?", (target,))
            if cursor.rowcount != 1:
                raise ValueError("Platsen finns inte")

    def add_item(self, data: dict[str, Any], actor: str) -> str:
        location = canonical_path(data["location"])
        item_id = secrets.token_hex(8)
        now = _now()
        self.upsert_place({"path": location}, actor)
        self.database.execute(
            "INSERT INTO household_items(id,name,location,category,owner,note,info,image_url,created_at,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (item_id, data["name"].strip(), location, data.get("category", ""), data.get("owner", ""), data.get("note", ""), data.get("info", ""), data.get("image_url", ""), now, now, actor),
        )
        return item_id

    def update_item(self, item_id: str, changes: dict[str, Any], actor: str) -> None:
        allowed = {key: value for key, value in changes.items() if value is not None and key in {"name", "location", "category", "owner", "note", "info", "image_url"}}
        if "location" in allowed:
            allowed["location"] = canonical_path(allowed["location"])
            self.upsert_place({"path": allowed["location"]}, actor)
        allowed["updated_at"] = _now()
        allowed["updated_by"] = actor
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE household_items SET {assignments} WHERE id=?", (*allowed.values(), item_id))
            if cursor.rowcount != 1:
                raise ValueError("Saken finns inte")

    def delete_item(self, item_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM household_items WHERE id=?", (item_id,))
            if cursor.rowcount != 1:
                raise ValueError("Saken finns inte")

    def add_log(self, data: dict[str, Any], actor: str) -> str:
        entry_id = secrets.token_hex(8)
        self.database.execute(
            "INSERT INTO household_log(id,title,category,note,actor,created_at) VALUES(?,?,?,?,?,?)",
            (entry_id, data["title"].strip(), data.get("category", "Händelse"), data.get("note", ""), actor, _now()),
        )
        return entry_id

    def delete_log(self, entry_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM household_log WHERE id=?", (entry_id,))
            if cursor.rowcount != 1:
                raise ValueError("Loggposten finns inte")
