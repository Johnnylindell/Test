from __future__ import annotations

from typing import Any

from app.database.database import Database


class HomelabRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def _state(self, key: str, default: Any) -> Any:
        value = self.database.get_json_state(key, default)
        return value if isinstance(value, type(default)) else default

    def overview(self) -> dict:
        settings = self._state("settings", {})
        devices = self._state("device_profiles", {})
        last_scan = self._state("last_port_scan", {})
        router = self._state("router_probe", {})
        integrations = self._state("integrations", {})
        internet_history = self._state("internet_history", [])
        events = self._state("events", [])
        safe_settings = {
            key: value
            for key, value in settings.items()
            if not any(secret in key.casefold() for secret in ("password", "token", "secret", "key", "webhook"))
        }
        integration_profiles = [
            {
                "id": str(name)[:80],
                "name": str(name)[:80],
                "configured": bool(value),
            }
            for name, value in list(integrations.items())[:100]
        ]
        device_profiles = [
            {
                "id": str(identifier)[:120],
                "name": str(row.get("name") or row.get("label") or identifier)[:160]
                if isinstance(row, dict)
                else str(identifier)[:160],
                "host": str(row.get("host") or "")[:253] if isinstance(row, dict) else "",
                "ports": [
                    int(port)
                    for port in list(row.get("ports") or [])[:30]
                    if isinstance(port, int) and 1 <= port <= 65535
                ]
                if isinstance(row, dict)
                else [],
                "trusted": bool(row.get("trusted")) if isinstance(row, dict) else False,
                "mac_configured": bool(row.get("mac")) if isinstance(row, dict) else False,
            }
            for identifier, row in list(devices.items())[:300]
        ]
        return {
            "ok": True,
            "settings": safe_settings,
            "integrations": integration_profiles,
            "devices": {
                "configured": len(device_profiles),
                "profiles": device_profiles,
            },
            "device_profiles": device_profiles,
            "network": {
                "last_port_scan": last_scan,
                "router": router,
                "internet_latest": internet_history[0] if internet_history else None,
            },
            "events": events[:100],
            "sensitive_values_exposed": False,
            "live_probes_performed": False,
        }

    def system_counts(self) -> dict:
        return {
            "database_integrity": self.database.integrity_check(),
            "tables": int(self.database.fetch_value("SELECT COUNT(*) FROM sqlite_master WHERE type='table'", default=0) or 0),
            "admin_sessions": self.database.count("admin_sessions"),
            "push_subscriptions": self.database.count("push_subscriptions"),
            "budget_months": self.database.count("budget_sheets", "kind='month'"),
        }
