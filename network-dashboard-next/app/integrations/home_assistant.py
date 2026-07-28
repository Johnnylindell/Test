from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker
from app.integrations.config_store import IntegrationConfigStore

_ALLOWED_DOMAINS = {"light", "switch", "cover", "climate", "fan", "scene", "script", "automation"}
_ALLOWED_SERVICES = {"turn_on", "turn_off", "toggle", "open_cover", "close_cover", "stop_cover"}


class HomeAssistantAdapter:
    def __init__(
        self,
        config: IntegrationConfigStore,
        cache: TTLCache,
        breaker: CircuitBreaker,
        *,
        verify_tls: bool = True,
        ca_bundle: Path | None = None,
    ) -> None:
        self.config = config
        self.cache = cache
        self.breaker = breaker
        self.verify_tls = bool(verify_tls)
        self.ca_bundle = Path(ca_bundle).expanduser() if ca_bundle else None

    def _config(self) -> tuple[str, str]:
        base = self.config.get("home_assistant_url").strip().rstrip("/")
        token = self.config.get("home_assistant_token").strip()
        return base, token

    def _configuration_status(self) -> dict:
        url_status = self.config.status("home_assistant_url")
        token_status = self.config.status("home_assistant_token")
        components = {
            "url": bool(url_status["configured"]),
            "token": bool(token_status["configured"]),
        }
        missing = [name for name, configured in components.items() if not configured]
        return {
            "configured": not missing,
            "missing": missing,
            "components": components,
            "sources": {
                "url": url_status["source"],
                "token": token_status["source"],
            },
        }

    @staticmethod
    def _setup_message(missing: list[str]) -> str:
        if set(missing) == {"url", "token"}:
            return "Home Assistant URL och token saknas"
        if "token" in missing:
            return "Home Assistant-token saknas"
        if "url" in missing:
            return "Home Assistant URL saknas"
        return "Home Assistant-konfigurationen behöver granskas"

    @staticmethod
    def _validated_base(base: str) -> str:
        parsed = urlparse(base)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
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

    def _tls_configuration(self) -> tuple[bool, Path | None, dict[str, str]]:
        verify_value, verify_source = self.config.resolve("home_assistant_verify_tls")
        ca_value, ca_source = self.config.resolve("home_assistant_ca_bundle")
        verify = self.verify_tls
        if verify_value:
            verify = verify_value.casefold() in {"true", "1", "yes", "on"}
        ca_bundle = Path(ca_value).expanduser() if ca_value else self.ca_bundle
        return verify, ca_bundle, {"verification": verify_source, "ca_bundle": ca_source}

    def _verify(self) -> bool | str:
        verify, ca_bundle, _ = self._tls_configuration()
        if ca_bundle:
            if not ca_bundle.is_file():
                raise ValueError("Konfigurerad Home Assistant CA-fil saknas")
            return str(ca_bundle)
        return verify

    def configured(self) -> bool:
        return bool(self._configuration_status()["configured"])

    def _request(self, path: str, method: str = "GET", payload: dict | None = None) -> dict:
        configuration = self._configuration_status()
        if not configuration["configured"]:
            return {
                "configured": False,
                "ok": False,
                "state": "setup_required",
                "missing": configuration["missing"],
                "message": self._setup_message(configuration["missing"]),
            }
        base, token = self._config()
        base = self._validated_base(base)
        if not self.breaker.allow("home-assistant"):
            return {
                "configured": True,
                "ok": False,
                "state": "circuit_open",
                "breaker": self.breaker.status("home-assistant"),
            }
        try:
            with httpx.Client(
                timeout=httpx.Timeout(5.0, connect=2.0),
                verify=self._verify(),
                follow_redirects=False,
            ) as client:
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
            self.breaker.failure("home-assistant", exc)
            return {
                "configured": True,
                "ok": False,
                "state": "unavailable",
                "error": str(exc)[:240],
                "breaker": self.breaker.status("home-assistant"),
            }

    def _tls_status(self) -> dict:
        verify, ca_bundle, sources = self._tls_configuration()
        custom_ca = bool(ca_bundle)
        return {
            "verification_enabled": bool(custom_ca or verify),
            "custom_ca_configured": custom_ca,
            "custom_ca_readable": bool(ca_bundle and ca_bundle.is_file()),
            "compatibility_mode": not verify and not custom_ca,
            "sources": sources,
        }

    def _status_payload(self, result: dict, *, cached: bool) -> dict:
        configuration = self._configuration_status()
        missing = list(result.get("missing") or configuration["missing"])
        return {
            "configured": bool(configuration["configured"]),
            "ok": bool(result.get("ok")),
            "state": "connected" if result.get("ok") else result.get("state", "unavailable"),
            "message": result.get("message") or (self._setup_message(missing) if missing else ""),
            "missing": missing,
            "setup": configuration["components"],
            "cache": "hit" if cached else "miss",
            "breaker": self.breaker.status("home-assistant"),
            "tls": self._tls_status(),
            "credential_sources": configuration["sources"],
            "sensitive_values_exposed": False,
        }

    def status(self, *, fresh: bool = False) -> dict:
        if fresh:
            self.cache.invalidate("ha:status")
        result, cached = self.cache.get_or_set("ha:status", 20, lambda: self._request("/api/"))
        return self._status_payload(result, cached=cached)

    def entities(self, *, fresh: bool = False) -> dict:
        if fresh:
            self.cache.invalidate("ha:entities")
        result, cached = self.cache.get_or_set("ha:entities", 15, lambda: self._request("/api/states"))
        if not result.get("ok"):
            return {**self._status_payload(result, cached=cached), "entities": []}
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
        return {
            **self._status_payload(result, cached=cached),
            "entities": entities[:120],
        }

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
