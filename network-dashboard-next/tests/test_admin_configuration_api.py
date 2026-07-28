from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings as default_settings
from app.database.migrations import upgrade
from app.main import create_app


ROOT = Path(__file__).resolve().parents[1]
HA_TOKEN = "admin-config-home-assistant-token-1234567890"


def client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Path, Path, Path]:
    database = tmp_path / "next.sqlite3"
    sqlite3.connect(database).close()
    upgrade(database, ROOT / "migrations")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO admin_sessions(token,created_at,expires_at_epoch) VALUES('admin-token',datetime('now'),9999999999)"
        )
        connection.execute(
            "INSERT INTO app_json_state(key,value,updated_at) VALUES('settings',?,datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (json.dumps({"home_assistant_url": "http://homeassistant.local:8123"}),),
        )
    secrets = tmp_path / "integration-secrets.json"
    google_client = tmp_path / "google-client.json"
    google_token = tmp_path / "google-token.json"
    monkeypatch.setattr(
        "app.main.settings",
        replace(
            default_settings,
            database_path=database,
            port=0,
            cookie_secure=False,
            read_only=True,
            external_side_effects=False,
            integration_secrets_path=secrets,
            google_client_secrets_path=google_client,
            google_token_path=google_token,
        ),
    )
    app = create_app()
    result = TestClient(app)
    result.cookies.set("homelab_session", "admin-token")
    return result, secrets, google_client, google_token


def test_configuration_overview_is_masked(tmp_path: Path, monkeypatch) -> None:
    api, _, _, _ = client(tmp_path, monkeypatch)
    response = api.get("/api/v2/admin/integrations/configuration")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sensitive_values_exposed"] is False
    variables = {row["key"]: row for row in payload["variables"]}
    assert variables["home_assistant_url"]["source"] == "legacy_database"
    assert variables["home_assistant_url"]["configured"] is True
    assert variables["home_assistant_token"]["configured"] is False
    serialized = json.dumps(payload)
    assert HA_TOKEN not in serialized
    assert "values" not in payload


def test_read_only_preview_allows_only_confirmed_same_origin_setup(tmp_path: Path, monkeypatch) -> None:
    api, secrets, _, _ = client(tmp_path, monkeypatch)
    endpoint = "/api/v2/admin/integrations/configuration/home_assistant_token"

    missing_origin = api.put(endpoint, json={"value": HA_TOKEN, "confirm": True})
    assert missing_origin.status_code == 403
    assert not secrets.exists()

    unconfirmed = api.put(
        endpoint,
        headers={"origin": "http://testserver"},
        json={"value": HA_TOKEN, "confirm": False},
    )
    assert unconfirmed.status_code == 400
    assert not secrets.exists()

    saved = api.put(
        endpoint,
        headers={"origin": "http://testserver"},
        json={"value": HA_TOKEN, "confirm": True},
    )
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["sensitive_values_exposed"] is False
    assert payload["variable"]["source"] == "next_secret_file"
    assert payload["variable"]["masked"].endswith(HA_TOKEN[-4:])
    assert HA_TOKEN not in json.dumps(payload)
    assert secrets.is_file()
    assert oct(secrets.stat().st_mode & 0o777) == "0o600"

    # A normal domain mutation remains blocked by the global read-only gate.
    blocked = api.post(
        "/api/v2/shopping/items",
        headers={"origin": "http://testserver"},
        json={"list_id": "shopping", "text": "Ska inte sparas", "quantity": 1, "unit": ""},
    )
    assert blocked.status_code == 423
    assert blocked.json()["error"]["code"] == "read_only_mode"


def test_clearing_next_value_falls_back_to_legacy_source(tmp_path: Path, monkeypatch) -> None:
    api, _, _, _ = client(tmp_path, monkeypatch)
    headers = {"origin": "http://testserver"}
    endpoint = "/api/v2/admin/integrations/configuration/home_assistant_url"
    saved = api.put(
        endpoint,
        headers=headers,
        json={"value": "http://localhost:8123", "confirm": True},
    )
    assert saved.status_code == 200
    assert saved.json()["variable"]["source"] == "next_secret_file"

    cleared = api.delete(endpoint + "?confirm=true", headers=headers)
    assert cleared.status_code == 200
    variable = cleared.json()["variable"]
    assert variable["source"] == "legacy_database"
    assert variable["masked"] == "http://homeassistant.local:8123"


def test_google_upload_is_validated_and_private(tmp_path: Path, monkeypatch) -> None:
    api, _, google_client, google_token = client(tmp_path, monkeypatch)
    headers = {"origin": "http://testserver"}

    invalid = api.post(
        "/api/v2/admin/integrations/google/client-secret",
        headers=headers,
        files={"file": ("invalid.json", b'{"installed":{"client_id":"only"}}', "application/json")},
    )
    assert invalid.status_code == 400
    assert not google_client.exists()

    client_payload = {
        "installed": {
            "client_id": "client.apps.googleusercontent.com",
            "client_secret": "client-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    uploaded = api.post(
        "/api/v2/admin/integrations/google/client-secret",
        headers=headers,
        files={
            "file": (
                "client.json",
                json.dumps(client_payload).encode(),
                "application/json",
            )
        },
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["sensitive_values_exposed"] is False
    assert google_client.is_file()
    assert oct(google_client.stat().st_mode & 0o777) == "0o600"

    token_payload = {
        "client_id": "client.apps.googleusercontent.com",
        "client_secret": "client-secret",
        "refresh_token": "refresh-token",
        "token": "access-token",
    }
    token_response = api.post(
        "/api/v2/admin/integrations/google/token",
        headers=headers,
        files={"file": ("token.json", json.dumps(token_payload).encode(), "application/json")},
    )
    assert token_response.status_code == 200
    assert google_token.is_file()
    assert oct(google_token.stat().st_mode & 0o777) == "0o600"
    assert "refresh-token" not in json.dumps(token_response.json())
