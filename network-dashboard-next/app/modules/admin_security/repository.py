from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.auth.service import ACCESS_SECTIONS, DEFAULT_ACCESS
from app.database.database import Database


USERS = frozenset(DEFAULT_ACCESS)


class AdminSecurityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def access_profiles(self) -> dict[str, Any]:
        raw = self.database.get_json_state("user_access", {})
        stored = raw.get("profiles", {}) if isinstance(raw, dict) else {}
        result = []
        for user in sorted(USERS):
            default_sections, default_readonly = DEFAULT_ACCESS[user]
            profile: dict[str, Any] = {}
            if isinstance(stored, dict) and isinstance(stored.get(user), dict):
                profile = stored[user]
            elif isinstance(stored, list):
                profile = next(
                    (
                        item
                        for item in stored
                        if isinstance(item, dict)
                        and str(item.get("user") or "").strip().lower() == user
                    ),
                    {},
                )
            configured = {
                str(value).strip().lower()
                for value in profile.get("sections", [])
                if str(value).strip().lower() in ACCESS_SECTIONS
            }
            sections = sorted(configured or default_sections)
            result.append({
                "user": user,
                "sections": sections,
                "readonly": bool(profile.get("readonly", default_readonly)),
            })
        return {"profiles": result, "choices": sorted(ACCESS_SECTIONS)}

    def set_access_profile(self, user: str, sections: list[str], readonly: bool) -> dict[str, Any]:
        user = user.strip().lower()
        if user not in USERS:
            raise ValueError("Okänd profil")
        clean_sections = sorted({value.strip().lower() for value in sections if value.strip().lower() in ACCESS_SECTIONS})
        if not clean_sections:
            raise ValueError("Minst en sektion måste väljas")

        def updater(current: Any) -> dict[str, Any]:
            state = dict(current) if isinstance(current, dict) else {}
            current_profiles = state.get("profiles")
            profiles: dict[str, Any] = {}
            if isinstance(current_profiles, dict):
                profiles.update(current_profiles)
            elif isinstance(current_profiles, list):
                for item in current_profiles:
                    if not isinstance(item, dict):
                        continue
                    item_user = str(item.get("user") or "").strip().lower()
                    if item_user in USERS:
                        profiles[item_user] = {
                            "sections": item.get("sections", []),
                            "readonly": bool(item.get("readonly", False)),
                        }
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
