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


def build_client(tmp_path: Path, monkeypatch) -> TestClient:
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
            (json.dumps({
                "home_assistant_url": "http://homeassistant.local:8123",
                "home_assistant_token": "never-return-this-home-assistant-token-1234567890",
            }),),
        )
    monkeypatch.setattr(
        "app.main.settings",
        replace(
            default_settings,
            database_path=database,
            port=0,
            cookie_secure=False,
            read_only=True,
            external_side_effects=False,
            integration_secrets_path=tmp_path / "integration-secrets.json",
            google_client_secrets_path=tmp_path / "google-client.json",
            google_token_path=tmp_path / "google-token.json",
        ),
    )
    client = TestClient(create_app())
    client.cookies.set("homelab_session", "admin-token")
    return client


def test_embed_settings_are_admin_only_same_origin_and_safe_in_read_only(tmp_path: Path, monkeypatch) -> None:
    client = build_client(tmp_path, monkeypatch)
    client.cookies.clear()
    assert client.get("/api/v2/admin/home-assistant-embed/overview").status_code == 403
    client.cookies.set("homelab_session", "admin-token")

    missing_origin = client.put(
        "/api/v2/admin/home-assistant-embed/settings",
        json={"enabled": True, "path": "/lovelace/default_view", "confirm": True},
    )
    assert missing_origin.status_code == 403

    saved = client.put(
        "/api/v2/admin/home-assistant-embed/settings",
        headers={"Origin": "http://testserver"},
        json={"enabled": True, "path": "/lovelace/default_view", "confirm": True},
    )
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["ready"] is True
    assert payload["frame_url"] == "http://homeassistant.local:8123/lovelace/default_view"
    assert payload["policy"]["family_url_exposed"] is False
    assert payload["policy"]["access_token_exposed"] is False
    assert "never-return-this" not in json.dumps(payload)


def test_embed_rejects_absolute_traversal_query_and_unconfirmed_paths(tmp_path: Path, monkeypatch) -> None:
    client = build_client(tmp_path, monkeypatch)
    headers = {"Origin": "http://testserver"}
    for path in ("https://example.com/lovelace", "//evil.example/path", "/lovelace/../config", "/lovelace?x=1"):
        response = client.put(
            "/api/v2/admin/home-assistant-embed/settings",
            headers=headers,
            json={"enabled": True, "path": path, "confirm": True},
        )
        assert response.status_code == 400
    unconfirmed = client.put(
        "/api/v2/admin/home-assistant-embed/settings",
        headers=headers,
        json={"enabled": True, "path": "/lovelace", "confirm": False},
    )
    assert unconfirmed.status_code == 400


def test_embed_frontend_is_admin_registered_and_sandboxed() -> None:
    index = (ROOT / "static" / "v2" / "index.html").read_text(encoding="utf-8")
    source = (ROOT / "static" / "v2" / "home-assistant-embed-admin.js").read_text(encoding="utf-8")
    assert "/preview-v2/home-assistant-embed-admin.css" in index
    assert "/preview-v2/home-assistant-embed-admin.js" in index
    assert 'button.textContent = "HA Embed"' in source
    assert 'sandbox="allow-forms allow-modals allow-popups allow-same-origin allow-scripts"' in source
    assert 'referrerpolicy="no-referrer"' in source
    assert "home_assistant_token" not in source
