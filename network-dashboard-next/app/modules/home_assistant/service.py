from __future__ import annotations

from typing import Any

from app.database.database import Database
from app.integrations.home_assistant import HomeAssistantAdapter


_GROUPS = {
    "light": "Belysning",
    "switch": "Brytare",
    "cover": "Gardiner och portar",
    "climate": "Klimat",
    "fan": "Fläktar",
    "scene": "Scener",
    "script": "Skript",
    "automation": "Automationer",
}

_ACTIVE_STATES = {
    "light": {"on"},
    "switch": {"on"},
    "cover": {"open", "opening"},
    "climate": {"heat", "cool", "heat_cool", "auto", "fan_only", "dry"},
    "fan": {"on"},
    "scene": set(),
    "script": {"on"},
    "automation": {"on"},
}


class HomeLifeService:
    def __init__(self, database: Database, adapter: HomeAssistantAdapter) -> None:
        self.database = database
        self.adapter = adapter

    def favorites(self) -> list[str]:
        raw = self.database.get_json_state("home_assistant_favorites", [])
        if not isinstance(raw, list):
            return []
        values = []
        seen: set[str] = set()
        for item in raw[:100]:
            entity_id = str(item or "").strip()[:180]
            if entity_id and entity_id not in seen:
                seen.add(entity_id)
                values.append(entity_id)
        return values

    def save_favorites(self, entity_ids: list[str]) -> list[str]:
        normalized = []
        seen: set[str] = set()
        for item in entity_ids[:100]:
            entity_id = str(item or "").strip()[:180]
            if "." not in entity_id or entity_id in seen:
                continue
            domain = entity_id.split(".", 1)[0]
            if domain not in _GROUPS:
                continue
            seen.add(entity_id)
            normalized.append(entity_id)
        self.database.set_json_state("home_assistant_favorites", normalized)
        return normalized

    def overview(self, *, fresh: bool = False) -> dict[str, Any]:
        payload = self.adapter.entities(fresh=fresh)
        entities = list(payload.get("entities") or [])
        favorites = self.favorites()
        favorite_set = set(favorites)
        if favorite_set:
            entities.sort(key=lambda row: (row.get("entity_id") not in favorite_set, favorites.index(row["entity_id"]) if row.get("entity_id") in favorite_set else 999, row.get("name", "").casefold()))
        groups: dict[str, list[dict[str, Any]]] = {}
        active_count = 0
        for entity in entities[:120]:
            domain = str(entity.get("domain") or "")
            state = str(entity.get("state") or "")
            active = state in _ACTIVE_STATES.get(domain, set())
            active_count += int(active)
            groups.setdefault(domain, []).append({
                "entity_id": str(entity.get("entity_id") or "")[:180],
                "name": str(entity.get("name") or entity.get("entity_id") or "Enhet")[:160],
                "domain": domain,
                "state": state[:80],
                "active": active,
                "favorite": str(entity.get("entity_id") or "") in favorite_set,
                "services": self._services(domain),
            })
        return {
            "ok": bool(payload.get("ok")),
            "configured": bool(payload.get("configured")),
            "state": payload.get("state") or ("connected" if payload.get("ok") else "unavailable"),
            "message": str(payload.get("message") or "")[:240],
            "missing": [str(item) for item in (payload.get("missing") or []) if item in {"url", "token"}],
            "setup": {
                "url": bool((payload.get("setup") or {}).get("url")),
                "token": bool((payload.get("setup") or {}).get("token")),
            },
            "cache": payload.get("cache"),
            "summary": {
                "entities": sum(len(rows) for rows in groups.values()),
                "active": active_count,
                "favorites": len(favorite_set),
                "groups": len(groups),
            },
            "favorites": favorites,
            "groups": [
                {
                    "id": domain,
                    "label": _GROUPS.get(domain, domain.title()),
                    "entities": rows,
                }
                for domain, rows in sorted(groups.items(), key=lambda item: list(_GROUPS).index(item[0]))
            ],
            "sensitive_values_exposed": False,
        }

    @staticmethod
    def _services(domain: str) -> list[str]:
        if domain == "cover":
            return ["open_cover", "close_cover", "stop_cover"]
        if domain in {"light", "switch", "climate", "fan", "script", "automation"}:
            return ["turn_on", "turn_off", "toggle"]
        if domain == "scene":
            return ["turn_on"]
        return []
