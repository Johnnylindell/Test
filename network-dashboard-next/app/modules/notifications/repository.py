from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.database.database import Database


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def _require_push_schema(self) -> None:
        if not self.database.table_exists("push_subscriptions"):
            raise RuntimeError("push_subscriptions saknas; kör databasmigreringen först")

    def subscriptions(self) -> list[dict[str, Any]]:
        self._require_push_schema()
        rows = self.database.fetch_all(
            "SELECT endpoint,user,subscription,created_at FROM push_subscriptions ORDER BY created_at DESC"
        )
        result = []
        for row in rows:
            try:
                subscription = json.loads(row["subscription"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(subscription, dict) and subscription.get("endpoint"):
                result.append({"user": row.get("user") or "", "created_at": row.get("created_at") or "", "subscription": subscription})
        return result

    def upsert_subscription(self, user: str, subscription: dict[str, Any]) -> None:
        self._require_push_schema()
        payload = json.dumps(subscription, ensure_ascii=False, separators=(",", ":"))
        self.database.execute(
            "INSERT INTO push_subscriptions(endpoint,user,subscription,created_at) VALUES(?,?,?,?) "
            "ON CONFLICT(endpoint) DO UPDATE SET user=excluded.user,subscription=excluded.subscription,created_at=excluded.created_at",
            (subscription["endpoint"], user, payload, now_iso()),
        )

    def delete_subscription(self, endpoint: str) -> None:
        self._require_push_schema()
        self.database.execute("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))

    def delete_invalid_subscriptions(self, endpoints: list[str]) -> int:
        if not endpoints:
            return 0
        self._require_push_schema()
        placeholders = ",".join("?" for _ in endpoints)
        before = self.database.count("push_subscriptions")
        self.database.execute(f"DELETE FROM push_subscriptions WHERE endpoint IN ({placeholders})", tuple(endpoints))
        return max(0, before - self.database.count("push_subscriptions"))

    def alerts(self, user: str, limit: int = 120) -> list[dict[str, Any]]:
        raw = self.database.get_json_state("alerts", [])
        rows = []
        user_key = user.strip().lower()
        for item in reversed(raw if isinstance(raw, list) else []):
            if not isinstance(item, dict):
                continue
            target = str(item.get("target") or "").strip().lower()
            if target not in {"", "all", "family", user_key}:
                continue
            if not item.get("id") or not str(item.get("message") or "").strip():
                continue
            rows.append({
                "id": str(item["id"])[:120],
                "type": str(item.get("type") or "info")[:60],
                "message": str(item.get("message") or "")[:500],
                "severity": str(item.get("severity") or "normal")[:30],
                "target": target or "family",
                "created_at": str(item.get("created_at") or "")[:80],
                "read": bool(item.get("acknowledged_at")),
                "acknowledged_at": item.get("acknowledged_at"),
            })
            if len(rows) >= max(1, min(limit, 200)):
                break
        return rows

    def create_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        def updater(current: Any) -> list[dict[str, Any]]:
            rows = list(current) if isinstance(current, list) else []
            rows.append(alert)
            return rows[-500:]

        self.database.update_json_state("alerts", updater, default=[])
        return alert

    def acknowledge(self, alert_id: str) -> dict[str, Any] | None:
        acknowledged: dict[str, Any] | None = None

        def updater(current: Any) -> list[dict[str, Any]]:
            nonlocal acknowledged
            rows = list(current) if isinstance(current, list) else []
            for row in rows:
                if isinstance(row, dict) and str(row.get("id")) == alert_id:
                    if not row.get("acknowledged_at"):
                        row["acknowledged_at"] = now_iso()
                    acknowledged = dict(row)
                    break
            return rows

        self.database.update_json_state("alerts", updater, default=[])
        return acknowledged
