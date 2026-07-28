from __future__ import annotations

import sqlite3
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
            INSERT INTO admin_sessions VALUES('admin-token','2026-07-28',9999999999);
            INSERT INTO app_json_state VALUES('settings','{}','2026-07-28');
            INSERT INTO app_json_state VALUES('device_profiles','{"router":{"id":"router","name":"Router","host":"192.168.1.1","ports":[80,443]}}','2026-07-28');
            INSERT INTO app_json_state VALUES('integrations','{"home_assistant":true}','2026-07-28');
            INSERT INTO app_json_state VALUES('last_port_scan','{}','2026-07-28');
            INSERT INTO app_json_state VALUES('last_network_scan','{}','2026-07-28');
            INSERT INTO app_json_state VALUES('router_probe','{}','2026-07-28');
            INSERT INTO app_json_state VALUES('internet_history','[]','2026-07-28');
            INSERT INTO app_json_state VALUES('computer_agents','{}','2026-07-28');
            INSERT INTO app_json_state VALUES('events','[]','2026-07-28');
            """
        )


def build_app(tmp_path: Path, monkeypatch, *, read_only: bool = True, external: bool = False):
    database_path = tmp_path / "network-admin.sqlite3"
    seed_database(database_path)
    monkeypatch.setattr(
        "app.main.settings",
        replace(
            default_settings,
            database_path=database_path,
            port=0,
            cookie_secure=False,
            read_only=read_only,
            external_side_effects=external,
        ),
    )
    return create_app()


def test_toolbox_is_admin_only_and_does_not_probe_on_load(tmp_path: Path, monkeypatch) -> None:
    app = build_app(tmp_path, monkeypatch)
    calls = {"dns": 0}

    def dns(host: str) -> dict:
        calls["dns"] += 1
        return {"ok": True, "host": host, "addresses": ["192.168.1.1"]}

    app.state.network_tools.dns = dns
    with TestClient(app) as client:
        assert client.get("/api/v2/admin/homelab/toolbox/status").status_code == 403
        client.cookies.set("homelab_session", "admin-token")
        status_response = client.get("/api/v2/admin/homelab/toolbox/status")
        overview_response = client.get("/api/v2/admin/homelab/overview")
        assert calls == {"dns": 0}
        dns_response = client.get("/api/v2/admin/homelab/toolbox/dns", params={"host": "router.lan"})

    assert status_response.status_code == 200
    assert status_response.json()["live_probes_performed"] is False
    assert status_response.json()["policy"]["arbitrary_shell_exposed"] is False
    assert overview_response.json()["devices"]["profiles"][0]["name"] == "Router"
    assert dns_response.status_code == 200
    assert dns_response.json()["addresses"] == ["192.168.1.1"]
    assert calls == {"dns": 1}


def test_port_tool_validates_and_limits_the_port_list(tmp_path: Path, monkeypatch) -> None:
    app = build_app(tmp_path, monkeypatch)
    captured: dict[str, object] = {}

    def port_scan(host: str, ports: list[int]) -> dict:
        captured.update({"host": host, "ports": ports})
        return {"ok": True, "host": host, "ports_checked": ports, "open_ports": [443]}

    app.state.network_tools.port_scan = port_scan
    with TestClient(app) as client:
        client.cookies.set("homelab_session", "admin-token")
        response = client.get(
            "/api/v2/admin/homelab/toolbox/ports",
            params={"host": "192.168.1.5", "ports": "443,80,443"},
        )
        too_many = client.get(
            "/api/v2/admin/homelab/toolbox/ports",
            params={"host": "192.168.1.5", "ports": ",".join(str(value) for value in range(1, 32))},
        )
        invalid = client.get(
            "/api/v2/admin/homelab/toolbox/ports",
            params={"host": "192.168.1.5", "ports": "80,not-a-port"},
        )

    assert response.status_code == 200
    assert captured == {"host": "192.168.1.5", "ports": [80, 443]}
    assert too_many.status_code == 400
    assert invalid.status_code == 400


def test_active_network_actions_require_external_mode_and_confirmation(tmp_path: Path, monkeypatch) -> None:
    blocked_app = build_app(tmp_path, monkeypatch, read_only=False, external=False)
    with TestClient(blocked_app) as client:
        client.cookies.set("homelab_session", "admin-token")
        blocked = client.post(
            "/api/v2/admin/homelab/toolbox/subnet-scan",
            headers={"Origin": "http://testserver"},
            json={"network": "192.168.1.0/24", "ports": [80], "confirm": True},
        )
    assert blocked.status_code == 423

    enabled_path = tmp_path / "enabled"
    enabled_path.mkdir()
    enabled_app = build_app(enabled_path, monkeypatch, read_only=False, external=True)
    enabled_app.state.network_tools.subnet_scan = lambda network, ports: {
        "ok": True,
        "network": network,
        "ports": ports,
        "devices": [],
    }
    enabled_app.state.network_tools.wake_on_lan = lambda mac, broadcast, port: {
        "ok": True,
        "mac": mac,
        "broadcast": broadcast,
        "port": port,
    }
    with TestClient(enabled_app) as client:
        client.cookies.set("homelab_session", "admin-token")
        unconfirmed = client.post(
            "/api/v2/admin/homelab/toolbox/subnet-scan",
            headers={"Origin": "http://testserver"},
            json={"network": "192.168.1.0/24", "ports": [80], "confirm": False},
        )
        scanned = client.post(
            "/api/v2/admin/homelab/toolbox/subnet-scan",
            headers={"Origin": "http://testserver"},
            json={"network": "192.168.1.0/24", "ports": [80], "confirm": True},
        )
        woke = client.post(
            "/api/v2/admin/homelab/toolbox/wake-on-lan",
            headers={"Origin": "http://testserver"},
            json={"mac": "AA:BB:CC:DD:EE:FF", "broadcast": "192.168.1.255", "port": 9, "confirm": True},
        )

    assert unconfirmed.status_code == 400
    assert scanned.status_code == 200
    assert woke.status_code == 200


def test_network_admin_frontend_is_registered_and_keeps_delegated_handlers() -> None:
    index = Path("static/v2/index.html").read_text(encoding="utf-8")
    source = Path("static/v2/network-admin.js").read_text(encoding="utf-8")
    assert "/preview-v2/network-admin.css" in index
    assert "/preview-v2/network-admin.js" in index
    assert 'button.textContent = "Nätverk"' in source
    assert 'content.addEventListener("submit", handleSubmit)' in source
    assert 'content.addEventListener("click", handleClick)' in source
    assert "arbitrary_shell_exposed" in source
    assert "token" not in source.casefold()
