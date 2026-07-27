from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

import httpx

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker
from app.database.database import Database

_ALLOWED_DOMAINS = {"light", "switch", "cover", "climate", "fan", "scene", "script", "automation"}
_ALLOWED_SERVICES = {"turn_on", "turn_off", "toggle", "open_cover", "close_cover", "stop_cover"}


class HomeAssistantAdapter:
    def __init__(self, database: Database, cache: TTLCache, breaker: CircuitBreaker) -> None:
        self.database = database
        self.cache = cache
        self.breaker = breaker

    def _config(self) -> tuple[str, str]:
        settings = self.database.get_json_state("settings", {})
        if not isinstance(settings, dict):
            settings = {}
        base = str(settings.get("home_assistant_url") or "").strip().rstrip("/")
        token = str(settings.get("home_assistant_token") or "").strip()
        return base, token

    @staticmethod
    def _validated_base(base: str) -> str:
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Ogiltig Home Assistant-URL")
        host = parsed.hostname
        try:
            address = ipaddress.ip_address(host)
            if not (address.is_private or address.is_loopback):
                raise ValueError("Home Assistant måste använda en privat eller lokal adress")
        except ValueError as exc:
            if str(exc) == "Home Assistant måste använda en privat eller lokal adress":
                raise
            if not (host.endswith(".local") or host.endswith(".ts.net") or host in {"localhost"}):
                raise ValueError("Home Assistant-värdnamnet är inte tillåtet") from exc
        return base

    def configured(self) -> bool:
        base, token = self._config()
        return bool(base and token)

    def _request(self, path: str, method: str = "GET", payload: dict | None = None) -> dict:
        base, token = self._config()
        if not base or not token:
            return {"configured": False, "ok": False, "state": "setup_required"}
        base = self._validated_base(base)
        if not self.breaker.allow("home-assistant"):
            return {
                "configured": True,
                "ok": False,
                "state": "circuit_open",
                "breaker": self.breaker.status("home-assistant"),
            }
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0), verify=False) as client:
                response = client.request(
                    method,
                    base + path,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
            response.raise_for_status()
            self.breaker.success("home-assistant")
            return {
                "configured": True,
                "ok": True,
                "status": response.status_code,
                "data": response.json() if response.content else None,
            }
        except (httpx.HTTPError, ValueError) as exc:
            self.breaker.failure("home-assistant")
            return {
                "configured": True,
                "ok": False,
                "state": "unavailable",
                "error": str(exc)[:240],
                "breaker": self.breaker.status("home-assistant"),
            }

    def status(self, *, fresh: bool = False) -> dict:
        if fresh:
            self.cache.invalidate("ha:status")
        result, cached = self.cache.get_or_set("ha:status", 20, lambda: self._request("/api/"))
        return {
            "configured": bool(result.get("configured")),
            "ok": bool(result.get("ok")),
            "state": "connected" if result.get("ok") else result.get("state", "unavailable"),
            "cache": "hit" if cached else "miss",
            "breaker": self.breaker.status("home-assistant"),
            "sensitive_values_exposed": False,
        }

    def entities(self, *, fresh: bool = False) -> dict:
        if fresh:
            self.cache.invalidate("ha:entities")
        result, cached = self.cache.get_or_set("ha:entities", 15, lambda: self._request("/api/states"))
        if not result.get("ok"):
            return {**self.status(), "entities": [], "cache": "hit" if cached else "miss"}
        entities = []
        for row in result.get("data") or []:
            entity_id = str(row.get("entity_id") or "")
            domain = entity_id.split(".", 1)[0]
            if domain not in _ALLOWED_DOMAINS:
                continue
            attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
            entities.append({
                "entity_id": entity_id,
                "domain": domain,
                "name": str(attrs.get("friendly_name") or entity_id)[:160],
                "state": str(row.get("state") or "")[:80],
            })
        entities.sort(key=lambda row: (row["domain"], row["name"].casefold()))
        return {"configured": True, "ok": True, "entities": entities[:120], "cache": "hit" if cached else "miss"}

    def call_service(self, entity_id: str, service: str) -> dict:
        if service not in _ALLOWED_SERVICES:
            raise ValueError("Otillåten Home Assistant-åtgärd")
        if "." not in entity_id:
            raise ValueError("Ogiltig entity_id")
        domain = entity_id.split(".", 1)[0]
        if domain not in _ALLOWED_DOMAINS:
            raise ValueError("Entitetsdomänen är inte tillåten")
        service_domain = "homeassistant" if service in {"turn_on", "turn_off", "toggle"} else domain
        result = self._request(
            f"/api/services/{service_domain}/{service}",
            method="POST",
            payload={"entity_id": entity_id},
        )
        if result.get("ok"):
            self.cache.invalidate("ha:")
        return {**result, "entity_id": entity_id, "service": service}
