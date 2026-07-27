from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database

MEMBERS = {"johnny", "kristina", "viktor", "alfred"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WishlistRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def overview(self, member: str = "") -> dict[str, Any]:
        if not self.database.table_exists("wishlist_items"):
            return {"ok": False, "members": sorted(MEMBERS), "items": [], "reason": "schema_missing"}
        selected = member.lower().strip() if member.lower().strip() in MEMBERS else ""
        if selected:
            items = self.database.fetch_all(
                "SELECT * FROM wishlist_items WHERE member=? ORDER BY purchased,created_at DESC",
                (selected,),
            )
        else:
            items = self.database.fetch_all(
                "SELECT * FROM wishlist_items ORDER BY member,purchased,created_at DESC"
            )
        return {
            "ok": True,
            "members": sorted(MEMBERS),
            "selected_member": selected,
            "items": items,
            "totals": {
                "items": len(items),
                "open": sum(not bool(row.get("purchased")) for row in items),
                "reserved": sum(bool(row.get("reserved_by")) and not bool(row.get("purchased")) for row in items),
            },
        }

    def add(self, data: dict[str, Any]) -> str:
        member = str(data["member"]).lower().strip()
        if member not in MEMBERS:
            raise ValueError("Ogiltig familjemedlem")
        item_id = secrets.token_hex(8)
        now = _now()
        self.database.execute(
            "INSERT INTO wishlist_items(id,member,title,url,note,price,reserved_by,purchased,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,0,?,?)",
            (
                item_id,
                member,
                data["title"].strip(),
                str(data.get("url") or ""),
                data.get("note", "").strip(),
                data.get("price"),
                "",
                now,
                now,
            ),
        )
        return item_id

    def update(self, item_id: str, changes: dict[str, Any]) -> None:
        allowed = {
            key: value for key, value in changes.items()
            if value is not None and key in {"title", "url", "note", "price", "reserved_by", "purchased"}
        }
        if not allowed:
            return
        if "url" in allowed:
            allowed["url"] = str(allowed["url"] or "")
        if "purchased" in allowed:
            allowed["purchased"] = 1 if allowed["purchased"] else 0
        allowed["updated_at"] = _now()
        assignments = ",".join(f'"{key}"=?' for key in allowed)
        params = [*allowed.values(), item_id]
        with self.database.transaction() as connection:
            cursor = connection.execute(f"UPDATE wishlist_items SET {assignments} WHERE id=?", params)
            if cursor.rowcount != 1:
                raise ValueError("Önskningen finns inte")

    def delete(self, item_id: str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute("DELETE FROM wishlist_items WHERE id=?", (item_id,))
            if cursor.rowcount != 1:
                raise ValueError("Önskningen finns inte")
