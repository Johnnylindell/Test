from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings as default_settings
from app.database.migrations import upgrade
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_shopping_completion_inventory_placement_and_reopen(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "next.sqlite3"
    sqlite3.connect(database).close()
    upgrade(database, ROOT / "migrations")
    monkeypatch.setattr(
        "app.main.settings",
        replace(default_settings, database_path=database, port=0, cookie_secure=False, read_only=False),
    )
    client = TestClient(create_app())
    cookies = {"homelab_user": "johnny"}
    headers = {"origin": "http://testserver"}

    created = client.post(
        "/api/v2/shopping/items",
        cookies=cookies,
        headers=headers,
        json={"list_id": "shopping", "text": "2 kg Potatis", "quantity": 2, "unit": "kg"},
    )
    assert created.status_code == 200
    shopping_id = created.json()["item_id"]

    completed = client.patch(
        f"/api/v2/shopping/items/{shopping_id}/completion",
        cookies=cookies,
        headers=headers,
        json={"done": True},
    )
    assert completed.status_code == 200
    inventory = client.get("/api/v2/inventory/overview", cookies=cookies).json()
    assert len(inventory["inbox"]) == 1
    inbox_id = inventory["inbox"][0]["id"]

    placed = client.post(
        f"/api/v2/inventory/inbox/{inbox_id}/place",
        cookies=cookies,
        headers=headers,
        json={"location": "pantry", "shelf": "Potatis"},
    )
    assert placed.status_code == 200
    inventory_item_id = placed.json()["item_id"]

    reopened = client.patch(
        f"/api/v2/shopping/items/{shopping_id}/completion",
        cookies=cookies,
        headers=headers,
        json={"done": False},
    )
    assert reopened.status_code == 200

    with sqlite3.connect(database) as connection:
        quantity = connection.execute(
            "SELECT quantity FROM inventory_items WHERE id=?",
            (inventory_item_id,),
        ).fetchone()[0]
        placement = connection.execute(
            "SELECT reverted_at,revert_mode FROM inventory_placements WHERE shopping_item_id=?",
            (shopping_id,),
        ).fetchone()
    assert quantity == 0
    assert placement[0]
    assert placement[1] == "shopping_reopened"
