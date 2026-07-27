from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database

SECTIONS = {
    "home", "planning", "week", "shopping", "inventory", "meals", "family", "mine",
    "wishlists", "lists", "household", "homeassistant", "weather", "calendar", "alerts",
    "ai", "budget",
}
USERS = {"johnny", "kristina", "viktor", "alfred", "guest"}


class AdminSecurityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def access_profiles(self) -> dict[str, Any]:
        raw = self.database.get_json_state("user_access", {})
        profiles = raw.get("profiles", {}) if isinstance(raw, dict) else {}
        result = []
        for user in sorted(USERS):
            profile = profiles.get(user, {}) if isinstance(profiles.get(user), dict) else {}
            sections = [value for value in profile.get("sections", []) if value in SECTIONS]
            result.append({"user": user, "sections": sections, "readonly": bool(profile.get("readonly", False))})
        return {"profiles": result, "choices": sorted(SECTIONS)}

    def set_access_profile(self, user: str, sections: list[str], readonly: bool) -> dict[str, Any]:
        user = user.strip().lower()
        if user not in USERS:
            raise ValueError("Okänd profil")
        clean_sections = [value for value in sections if value in SECTIONS]

        def updater(current: Any) -> dict[str, Any]:
            state = dict(current) if isinstance(current, dict) else {}
            profiles = dict(state.get("profiles")) if isinstance(state.get("profiles"), dict) else {}
            profiles[user] = {"sections": clean_sections, "readonly": bool(readonly)}
            state["profiles"] = profiles
            return state

        self.database.update_json_state("user_access", updater, default={})
        return self.access_profiles()

    def audit(self, actor: str, action: str, target: str = "", detail: dict[str, Any] | None = None) -> None:
        if not self.database.table_exists("admin_audit_log"):
            return
        self.database.execute(
            "INSERT INTO admin_audit_log(actor,action,target,detail_json,created_at) VALUES(?,?,?,?,?)",
            (
                actor[:80],
                action[:120],
                target[:200],
                json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":")),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def audit_log(self, limit: int = 200) -> list[dict[str, Any]]:
        if not self.database.table_exists("admin_audit_log"):
            return []
        rows = self.database.fetch_all(
            "SELECT id,actor,action,target,detail_json,created_at FROM admin_audit_log ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        )
        for row in rows:
            try:
                row["detail"] = json.loads(row.pop("detail_json"))
            except (TypeError, json.JSONDecodeError):
                row["detail"] = {}
        return rows
