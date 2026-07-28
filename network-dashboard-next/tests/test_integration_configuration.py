from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.database.database import Database
from app.integrations.config_store import IntegrationConfigStore
from app.modules.admin_integrations.router import _validate_google_client, _validate_google_token


HA_TOKEN = "legacy-home-assistant-token-1234567890"
DISCORD = "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"
VAPID_PUBLIC = "B" + "p" * 86
VAPID_PRIVATE = "-----BEGIN PRIVATE KEY-----\n" + "k" * 90 + "\n-----END PRIVATE KEY-----"


def legacy_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "legacy.sqlite3")
    with database.transaction() as connection:
        connection.executescript(
            """
            CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT);
            CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT);
            """
        )
        connection.execute(
            "INSERT INTO app_json_state(key,value,updated_at) VALUES('settings',?,datetime('now'))",
            (json.dumps({
                "home_assistant_url": "http://homeassistant.local:8123",
                "home_assistant_token": HA_TOKEN,
            }),),
        )
        connection.execute(
            "INSERT INTO app_json_state(key,value,updated_at) VALUES('vapid_keys',?,datetime('now'))",
            (json.dumps({
                "public": VAPID_PUBLIC,
                "private": VAPID_PRIVATE,
                "subject": "mailto:family@example.com",
            }),),
        )
        connection.execute(
            "INSERT INTO app_settings(key,value,updated_at) VALUES('discord_webhook_url',?,datetime('now'))",
            (json.dumps(DISCORD),),
        )
    return database


def test_legacy_settings_and_app_settings_are_resolved(tmp_path: Path) -> None:
    store = IntegrationConfigStore(legacy_database(tmp_path), tmp_path / "secrets.json")
    assert store.resolve("home_assistant_url") == (
        "http://homeassistant.local:8123",
        "legacy_database",
    )
    assert store.resolve("home_assistant_token") == (HA_TOKEN, "legacy_database")
    assert store.resolve("discord_webhook_url") == (DISCORD, "legacy_database")
    assert store.resolve("vapid_public_key") == (VAPID_PUBLIC, "legacy_database")


def test_status_and_overview_never_expose_secret_values(tmp_path: Path) -> None:
    store = IntegrationConfigStore(legacy_database(tmp_path), tmp_path / "secrets.json")
    status = store.status("home_assistant_token")
    assert status["configured"] is True
    assert status["source"] == "legacy_database"
    assert HA_TOKEN not in json.dumps(status)
    overview = json.dumps(store.overview(), ensure_ascii=False)
    assert HA_TOKEN not in overview
    assert DISCORD not in overview
    assert VAPID_PRIVATE not in overview
    assert overview.count("sensitive_values_exposed") == 1


def test_adopt_legacy_writes_private_file_and_changes_source(tmp_path: Path) -> None:
    secrets = tmp_path / "private" / "integration-secrets.json"
    store = IntegrationConfigStore(legacy_database(tmp_path), secrets)
    result = store.adopt_legacy()
    assert "home_assistant_token" in result["adopted"]
    assert "discord_webhook_url" in result["adopted"]
    assert secrets.is_file()
    assert stat.S_IMODE(secrets.stat().st_mode) == 0o600
    assert store.status("home_assistant_token")["source"] == "next_secret_file"
    payload = json.loads(secrets.read_text(encoding="utf-8"))
    assert payload["format"] == "network-dashboard-integration-secrets-v1"
    assert payload["values"]["home_assistant_token"] == HA_TOKEN


def test_next_value_overrides_and_clear_falls_back_to_legacy(tmp_path: Path) -> None:
    store = IntegrationConfigStore(legacy_database(tmp_path), tmp_path / "secrets.json")
    replacement = "replacement-home-assistant-token-0987654321"
    store.set("home_assistant_token", replacement)
    assert store.resolve("home_assistant_token") == (replacement, "next_secret_file")
    store.clear("home_assistant_token")
    assert store.resolve("home_assistant_token") == (HA_TOKEN, "legacy_database")


def test_environment_is_used_only_when_file_and_database_are_missing(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "empty.sqlite3")
    with database.transaction() as connection:
        connection.execute("CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
        connection.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", DISCORD)
    store = IntegrationConfigStore(database, tmp_path / "secrets.json")
    assert store.resolve("discord_webhook_url") == (DISCORD, "environment:DISCORD_WEBHOOK_URL")


def test_variable_validation_rejects_unsafe_values(tmp_path: Path) -> None:
    store = IntegrationConfigStore(legacy_database(tmp_path), tmp_path / "secrets.json")
    with pytest.raises(ValueError, match="fullständig"):
        store.set("home_assistant_url", "homeassistant.local:8123")
    with pytest.raises(ValueError, match="inloggning"):
        store.set("home_assistant_url", "http://user:pass@homeassistant.local:8123")
    with pytest.raises(ValueError, match="Discord"):
        store.set("discord_webhook_url", "https://example.com/api/webhooks/1/token")
    with pytest.raises(KeyError):
        store.set("unknown_secret", "value")


def test_google_file_validators_accept_expected_shapes() -> None:
    client = {
        "installed": {
            "client_id": "id.apps.googleusercontent.com",
            "client_secret": "secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    token = {
        "client_id": "id.apps.googleusercontent.com",
        "client_secret": "secret",
        "refresh_token": "refresh",
        "token": "access",
    }
    assert _validate_google_client(client) is client
    assert _validate_google_token(token)["type"] == "authorized_user"
    with pytest.raises(HTTPException):
        _validate_google_client({"installed": {"client_id": "missing-the-rest"}})
    with pytest.raises(HTTPException):
        _validate_google_token({"client_id": "missing-the-rest"})


def test_legacy_import_and_frontend_contracts_do_not_print_secrets() -> None:
    root = Path(__file__).resolve().parents[1]
    importer = (root / "scripts" / "import_legacy_config.py").read_text(encoding="utf-8")
    frontend = (root / "static" / "v2" / "configuration.js").read_text(encoding="utf-8")
    installer = (root / "scripts" / "install_parallel.sh").read_text(encoding="utf-8")
    assert '"sensitive_values_exposed": False' in importer
    assert "print(value" not in importer
    assert "masked" in frontend
    assert 'variable.secret ? "password" : "text"' in frontend
    assert "INTEGRATION_SECRETS_PATH" in installer
    assert "import_legacy_config.py" in installer
    assert "chmod 600 \"$INTEGRATION_SECRETS_PATH\"" in installer
