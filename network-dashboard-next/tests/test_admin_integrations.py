from __future__ import annotations

import sqlite3
import time
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings as default_settings
from app.main import create_app


def seed_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE admin_sessions(token TEXT PRIMARY KEY, created_at TEXT, expires_at_epoch REAL);
            CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
            CREATE TABLE app_json_state(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
            CREATE TABLE push_subscriptions(id INTEGER PRIMARY KEY, endpoint TEXT, user TEXT, subscription TEXT, created_at TEXT);
            CREATE TABLE budget_sheets(id INTEGER PRIMARY KEY, name TEXT, kind TEXT, sort_order INTEGER);
            INSERT INTO admin_sessions VALUES('admin-token','2026-07-27',9999999999);
            INSERT INTO app_json_state VALUES('settings','{}','2026-07-27');
            INSERT INTO app_json_state VALUES('device_profiles','{"phone":{"name":"Telefon","trusted":true}}','2026-07-27');
            INSERT INTO app_json_state VALUES('integrations','{"calendar":true}','2026-07-27');
            INSERT INTO app_json_state VALUES('last_port_scan','{"devices":[],"scanned_at":"2026-07-27"}','2026-07-27');
            INSERT INTO app_json_state VALUES('router_probe','{"probes":[],"best":null}','2026-07-27');
            INSERT INTO app_json_state VALUES('internet_history','[]','2026-07-27');
            INSERT INTO app_json_state VALUES('events','[]','2026-07-27');
            """
        )


def test_admin_routes_are_protected_and_local_overview_does_not_probe(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "family.sqlite3"
    seed_database(database_path)
    monkeypatch.setattr(
        "app.main.settings",
        replace(default_settings, database_path=database_path, port=0, cookie_secure=False),
    )
    app = create_app()

    calls = {"ha": 0, "tailscale": 0}

    def ha_status(*, fresh: bool = False) -> dict:
        calls["ha"] += 1
        return {"configured": False, "ok": False, "state": "setup_required"}

    def tailscale_status(*, fresh: bool = False) -> dict:
        calls["tailscale"] += 1
        return {"installed": False, "running": False, "state": "not_installed"}

    app.state.home_assistant.status = ha_status
    app.state.tailscale.status = tailscale_status

    with TestClient(app) as client:
        assert client.get("/api/v2/admin/homelab/overview").status_code == 403
        client.cookies.set("homelab_session", "admin-token")
        local = client.get("/api/v2/admin/homelab/overview")
        ha = client.get("/api/v2/admin/integrations/home-assistant/status")
        tailscale = client.get("/api/v2/admin/integrations/tailscale/status")

    assert local.status_code == 200
    assert local.json()["live_probes_performed"] is False
    assert local.json()["sensitive_values_exposed"] is False
    assert calls == {"ha": 1, "tailscale": 1}
    assert ha.status_code == 200
    assert tailscale.status_code == 200


def test_cache_and_circuit_breaker_behaviour() -> None:
    from app.core.cache import TTLCache
    from app.core.circuit_breaker import CircuitBreaker

    cache = TTLCache()
    value, cached = cache.get_or_set("x", 10, lambda: {"value": 1})
    second, second_cached = cache.get_or_set("x", 10, lambda: {"value": 2})
    assert value == second == {"value": 1}
    assert cached is False and second_cached is True

    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=0.01)
    breaker.failure("integration")
    assert breaker.allow("integration") is True
    breaker.failure("integration")
    assert breaker.allow("integration") is False
    time.sleep(0.02)
    assert breaker.allow("integration") is True
