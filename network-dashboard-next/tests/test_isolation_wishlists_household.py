from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings as default_settings
from app.database.migrations import upgrade
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def _app(tmp_path: Path, monkeypatch, *, read_only: bool = False):
    database = tmp_path / "next.sqlite3"
    sqlite3.connect(database).close()
    upgrade(database, ROOT / "migrations")
    monkeypatch.setattr(
        "app.main.settings",
        replace(default_settings, database_path=database, port=0, cookie_secure=False, read_only=read_only),
    )
    return create_app(), database


def test_read_only_blocks_domain_writes(tmp_path: Path, monkeypatch) -> None:
    app, _ = _app(tmp_path, monkeypatch, read_only=True)
    response = TestClient(app).post(
        "/api/v2/wishlists/items",
        cookies={"homelab_user": "johnny"},
        headers={"origin": "http://testserver"},
        json={"member": "johnny", "title": "Test"},
    )
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "read_only_mode"


def test_wishlist_and_household_roundtrip(tmp_path: Path, monkeypatch) -> None:
    app, database = _app(tmp_path, monkeypatch)
    client = TestClient(app)
    cookies = {"homelab_user": "johnny"}
    headers = {"origin": "http://testserver"}

    wishlist = client.post(
        "/api/v2/wishlists/items",
        cookies=cookies,
        headers=headers,
        json={"member": "johnny", "title": "Ny cykel", "price": 500},
    )
    assert wishlist.status_code == 201
    wishlist_id = wishlist.json()["id"]
    assert client.patch(
        f"/api/v2/wishlists/items/{wishlist_id}",
        cookies=cookies,
        headers=headers,
        json={"reserved_by": "Kristina"},
    ).status_code == 200

    item = client.post(
        "/api/v2/household/items",
        cookies=cookies,
        headers=headers,
        json={"name": "Borrmaskin", "location": "Garage / Verktyg", "category": "Verktyg"},
    )
    assert item.status_code == 201
    assert client.put(
        "/api/v2/household/places",
        cookies=cookies,
        headers=headers,
        json={"path": "Förråd / Verktyg", "old_path": "Garage / Verktyg"},
    ).status_code == 200

    overview = client.get("/api/v2/household/overview", cookies=cookies).json()
    assert overview["items"][0]["location"] == "Förråd / Verktyg"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM wishlist_items").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM household_items").fetchone()[0] == 1
