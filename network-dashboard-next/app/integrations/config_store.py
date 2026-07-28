from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from app.database.database import Database


@dataclass(frozen=True, slots=True)
class VariableDefinition:
    key: str
    label: str
    group: str
    secret: bool = True
    database_key: str = ""
    environment_names: tuple[str, ...] = ()
    help: str = ""
    restart_required: bool = False


VARIABLES: tuple[VariableDefinition, ...] = (
    VariableDefinition(
        "home_assistant_url",
        "Home Assistant URL",
        "home_assistant",
        secret=False,
        database_key="home_assistant_url",
        environment_names=("HOME_ASSISTANT_URL",),
        help="Basadress, till exempel https://homeassistant.example eller http://homeassistant.local:8123.",
    ),
    VariableDefinition(
        "home_assistant_token",
        "Home Assistant long-lived token",
        "home_assistant",
        database_key="home_assistant_token",
        environment_names=("HOME_ASSISTANT_TOKEN",),
        help="Long-lived access token från Home Assistant. Visas aldrig igen efter att den sparats.",
    ),
    VariableDefinition(
        "home_assistant_verify_tls",
        "Verifiera Home Assistant TLS",
        "home_assistant",
        secret=False,
        environment_names=("HOME_ASSISTANT_VERIFY_TLS",),
        help="true rekommenderas. false är ett uttryckligt kompatibilitetsläge för lokala självsignerade certifikat.",
    ),
    VariableDefinition(
        "home_assistant_ca_bundle",
        "Home Assistant CA-fil",
        "home_assistant",
        secret=False,
        environment_names=("HOME_ASSISTANT_CA_BUNDLE",),
        help="Absolut WSL-sökväg till en läsbar .pem- eller .crt-fil. Egen CA har företräde framför kompatibilitetsläget.",
    ),
    VariableDefinition(
        "discord_webhook_url",
        "Discord webhook",
        "notifications",
        database_key="discord_webhook_url",
        environment_names=("DISCORD_WEBHOOK_URL",),
        help="Valfri Discord-webhook för särskilt valda notifieringar.",
    ),
    VariableDefinition(
        "vapid_public_key",
        "VAPID public key",
        "notifications",
        secret=False,
        environment_names=("VAPID_PUBLIC_KEY",),
        help="Publik Web Push-nyckel. Kan genereras tillsammans med privatnyckeln i admin.",
    ),
    VariableDefinition(
        "vapid_private_key",
        "VAPID private key",
        "notifications",
        environment_names=("VAPID_PRIVATE_KEY",),
        help="Privat Web Push-nyckel. Lämnar aldrig servern.",
    ),
    VariableDefinition(
        "vapid_subject",
        "VAPID subject",
        "notifications",
        secret=False,
        environment_names=("VAPID_SUBJECT",),
        help="Kontakt för Web Push, vanligtvis mailto:adress@example.com.",
    ),
)

_BY_KEY = {definition.key: definition for definition in VARIABLES}
_SAFE_KEY = re.compile(r"^[a-z][a-z0-9_]{1,80}$")


class IntegrationConfigStore:
    def __init__(self, database: Database, path: Path) -> None:
        self.database = database
        self.path = Path(path).expanduser()
        self._lock = RLock()

    @staticmethod
    def definitions() -> tuple[VariableDefinition, ...]:
        return VARIABLES

    def _read_file(self) -> dict[str, str]:
        with self._lock:
            if not self.path.is_file():
                return {}
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {}
            values = payload.get("values") if isinstance(payload, dict) else None
            if not isinstance(values, dict):
                return {}
            return {
                str(key): str(value)
                for key, value in values.items()
                if isinstance(key, str) and isinstance(value, (str, int, float))
            }

    def _write_file(self, values: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"format": "network-dashboard-integration-secrets-v1", "values": values},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        with self._lock:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=self.path.name + ".",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )
            temporary = Path(temporary_name)
            try:
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.replace(self.path)
                os.chmod(self.path, 0o600)
            finally:
                temporary.unlink(missing_ok=True)

    def _legacy_database_value(self, definition: VariableDefinition) -> str:
        if definition.key.startswith("vapid_"):
            keys = self.database.get_json_state("vapid_keys", {})
            if isinstance(keys, dict):
                aliases = {
                    "vapid_public_key": ("public", "public_key"),
                    "vapid_private_key": ("private", "private_key"),
                    "vapid_subject": ("subject",),
                }[definition.key]
                for alias in aliases:
                    value = str(keys.get(alias) or "").strip()
                    if value:
                        return value
            return ""
        if not definition.database_key:
            return ""
        legacy_settings = self.database.get_json_state("settings", {})
        if isinstance(legacy_settings, dict):
            value = str(legacy_settings.get(definition.database_key) or "").strip()
            if value:
                return value
        return str(self.database.get_setting(definition.database_key, "") or "").strip()

    def resolve(self, key: str) -> tuple[str, str]:
        definition = self.definition(key)
        saved = str(self._read_file().get(key) or "").strip()
        if saved:
            return saved, "next_secret_file"
        legacy = self._legacy_database_value(definition)
        if legacy:
            return legacy, "legacy_database"
        for name in definition.environment_names:
            value = str(os.getenv(name, "") or "").strip()
            if value:
                return value, f"environment:{name}"
        return "", "missing"

    def get(self, key: str, default: str = "") -> str:
        value, _ = self.resolve(key)
        return value or default

    def definition(self, key: str) -> VariableDefinition:
        normalized = str(key or "").strip().lower()
        if not _SAFE_KEY.fullmatch(normalized) or normalized not in _BY_KEY:
            raise KeyError("Okänd integrationsvariabel")
        return _BY_KEY[normalized]

    @staticmethod
    def _mask(value: str, secret: bool) -> str:
        if not value:
            return ""
        if not secret:
            if len(value) <= 70:
                return value
            return value[:36] + "…" + value[-20:]
        if len(value) <= 8:
            return "•" * len(value)
        return "•" * min(12, max(6, len(value) - 4)) + value[-4:]

    def status(self, key: str) -> dict[str, Any]:
        definition = self.definition(key)
        value, source = self.resolve(key)
        return {
            "key": definition.key,
            "label": definition.label,
            "group": definition.group,
            "secret": definition.secret,
            "configured": bool(value),
            "source": source,
            "masked": self._mask(value, definition.secret),
            "help": definition.help,
            "restart_required": definition.restart_required,
        }

    def overview(self) -> dict[str, Any]:
        rows = [self.status(definition.key) for definition in VARIABLES]
        return {
            "ok": True,
            "path_configured": bool(self.path),
            "file_exists": self.path.is_file(),
            "file_permissions": oct(self.path.stat().st_mode & 0o777) if self.path.is_file() else "",
            "variables": rows,
            "configured": sum(1 for row in rows if row["configured"]),
            "missing": sum(1 for row in rows if not row["configured"]),
            "sensitive_values_exposed": False,
        }

    def set(self, key: str, value: str) -> dict[str, Any]:
        return self.set_many({key: value})[0]

    def set_many(self, updates: dict[str, str]) -> list[dict[str, Any]]:
        if not updates:
            return []
        normalized: dict[str, str] = {}
        definitions: list[VariableDefinition] = []
        for key, value in updates.items():
            definition = self.definition(key)
            definitions.append(definition)
            normalized[definition.key] = self._validate(definition, value)
        values = self._read_file()
        values.update(normalized)
        self._write_file(values)
        return [self.status(definition.key) for definition in definitions]

    def clear(self, key: str) -> dict[str, Any]:
        definition = self.definition(key)
        values = self._read_file()
        values.pop(definition.key, None)
        self._write_file(values)
        return self.status(definition.key)

    def adopt_legacy(self, *, overwrite: bool = False) -> dict[str, Any]:
        values = self._read_file()
        adopted: list[str] = []
        skipped: list[str] = []
        for definition in VARIABLES:
            if values.get(definition.key) and not overwrite:
                skipped.append(definition.key)
                continue
            legacy = self._legacy_database_value(definition)
            if not legacy:
                skipped.append(definition.key)
                continue
            values[definition.key] = self._validate(definition, legacy)
            adopted.append(definition.key)
        if adopted:
            self._write_file(values)
        return {
            "ok": True,
            "adopted": adopted,
            "skipped": skipped,
            "sensitive_values_exposed": False,
        }

    @staticmethod
    def _validate(definition: VariableDefinition, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Värdet får inte vara tomt")
        if len(normalized) > 10_000:
            raise ValueError("Värdet är för långt")
        if definition.key == "home_assistant_url":
            parsed = urlparse(normalized)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("Home Assistant URL måste vara en fullständig http- eller https-adress")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("Home Assistant URL får inte innehålla inloggning, query eller fragment")
            return normalized.rstrip("/")
        if definition.key == "home_assistant_token" and len(normalized) < 20:
            raise ValueError("Home Assistant-token verkar vara för kort")
        if definition.key == "home_assistant_verify_tls":
            lowered = normalized.casefold()
            if lowered not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
                raise ValueError("TLS-verifiering måste anges som true eller false")
            return "true" if lowered in {"true", "1", "yes", "on"} else "false"
        if definition.key == "home_assistant_ca_bundle":
            path = Path(normalized).expanduser()
            if not path.is_absolute():
                raise ValueError("CA-sökvägen måste vara absolut i WSL")
            if path.suffix.casefold() not in {".pem", ".crt", ".cer"}:
                raise ValueError("CA-filen måste vara .pem, .crt eller .cer")
            if not path.is_file() or not os.access(path, os.R_OK):
                raise ValueError("CA-filen finns inte eller kan inte läsas")
            return str(path.resolve())
        if definition.key == "discord_webhook_url":
            parsed = urlparse(normalized)
            allowed_hosts = {"discord.com", "www.discord.com", "discordapp.com", "www.discordapp.com"}
            if parsed.scheme != "https" or parsed.hostname not in allowed_hosts or "/api/webhooks/" not in parsed.path:
                raise ValueError("Discord-webhooken måste vara en giltig HTTPS webhook-adress")
        if definition.key == "vapid_subject" and not (
            normalized.startswith("mailto:") or normalized.startswith("https://")
        ):
            raise ValueError("VAPID subject måste börja med mailto: eller https://")
        if definition.key in {"vapid_public_key", "vapid_private_key"} and len(normalized) < 30:
            raise ValueError("VAPID-nyckeln verkar vara för kort")
        return normalized
