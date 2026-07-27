from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings as default_settings
from app.main import create_app


def seed(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE admin_sessions(token TEXT PRIMARY KEY, created_at TEXT, expires_at_epoch REAL);
            CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
            CREATE TABLE shopping_lists(
                id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE shopping_items(
                id TEXT PRIMARY KEY, list_id TEXT, text TEXT, category TEXT, store TEXT,
                done INTEGER, sort_order INTEGER, owner TEXT, quantity REAL, unit TEXT,
                created_at TEXT, completed_at TEXT, source TEXT
            );
            CREATE TABLE inventory_items(
                id TEXT PRIMARY KEY, name TEXT, quantity REAL, unit TEXT, location TEXT,
                shelf TEXT, usual_location TEXT, usual_shelf TEXT, note TEXT,
                created_at TEXT, updated_at TEXT
            );
            CREATE TABLE inventory_inbox(
                id TEXT PRIMARY KEY, shopping_item_id TEXT, text TEXT, name TEXT,
                quantity REAL, unit TEXT, category TEXT, store TEXT,
                suggested_location TEXT, suggested_shelf TEXT, created_at TEXT
            );
            CREATE TABLE inventory_shelves(
                id TEXT PRIMARY KEY, location TEXT, name TEXT, created_at TEXT
            );
            CREATE TABLE inventory_shopping_suggestions(
                id TEXT PRIMARY KEY, item_id TEXT, text TEXT, quantity REAL,
                unit TEXT, reason TEXT, created_at TEXT, dismissed_at TEXT
            );
            CREATE TABLE weekly_meals(
                week_start TEXT, day TEXT, meal_id TEXT, title TEXT, url TEXT,
                source TEXT, updated_at TEXT, PRIMARY KEY(week_start, day)
            );
            CREATE TABLE saved_dinners(
                id TEXT PRIMARY KEY, title TEXT, url TEXT, source TEXT, created_at TEXT
            );
            INSERT INTO shopping_lists VALUES('shopping','Inköp','2026-07-27','2026-07-27');
            INSERT INTO shopping_items VALUES(
                'milk','shopping','Mjölk','Mejeri','Butik',0,1,'Johnny',1,'l',
                '2026-07-27','','Test'
            );
            INSERT INTO inventory_items VALUES(
                'rice','Ris',2,'kg','pantry','Hylla 1','pantry','Hylla 1','',
                '2026-07-27','2026-07-27'
            );
            INSERT INTO weekly_meals VALUES(
                '2026-07-27','monday','meal-1','Pasta','','Manuellt','2026-07-27'
            );
            INSERT INTO saved_dinners VALUES(
                'recipe-1','Pannkakor','','Manuellt','2026-07-27'
            );
            """
        )


def app_for(path: Path, monkeypatch):
    configured = replace(default_settings, database_path=path, port=0, cookie_secure=False)
    monkeypatch.setattr("app.main.settings", configured)
    return create_app()


def test_domain_overviews_and_mutations(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "family.sqlite3"
    seed(path)
    app = app_for(path, monkeypatch)
    headers = {"origin": "http://testserver"}

    with TestClient(app) as client:
        client.cookies.set("homelab_user", "johnny")
        shopping = client.get("/api/v2/shopping/overview")
        inventory = client.get("/api/v2/inventory/overview")
        food = client.get("/api/v2/food/overview")
        added = client.post(
            "/api/v2/shopping/items",
            headers=headers,
            json={"text": "Ägg", "quantity": 2, "unit": "st"},
        )
        adjusted = client.patch(
            "/api/v2/inventory/items/rice/quantity",
            headers=headers,
            json={"delta": -2},
        )
        meal = client.put(
            "/api/v2/food/meals",
            headers=headers,
            json={
                "week_start": "2026-07-27",
                "day": "tuesday",
                "title": "Soppa",
            },
        )

    assert shopping.status_code == 200
    assert shopping.json()["active"][0]["text"] == "Mjölk"
    assert inventory.status_code == 200
    assert inventory.json()["totals"]["items"] == 1
    assert food.status_code == 200
    assert food.json()["totals"]["recipes"] == 1
    assert added.status_code == 200
    assert any(item["text"] == "Ägg" for item in added.json()["view"]["active"])
    assert adjusted.status_code == 200
    assert adjusted.json()["quantity"] == 0
    assert adjusted.json()["view"]["totals"]["suggestions"] == 1
    assert meal.status_code == 200
    assert any(row["day"] == "tuesday" for row in meal.json()["view"]["meals"])


def test_food_write_permissions_and_same_origin(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "family.sqlite3"
    seed(path)
    app = app_for(path, monkeypatch)

    with TestClient(app) as client:
        client.cookies.set("homelab_user", "viktor")
        forbidden = client.put(
            "/api/v2/food/meals",
            headers={"origin": "http://testserver"},
            json={"week_start": "2026-07-27", "day": "wednesday", "title": "Pizza"},
        )
        no_origin = client.post("/api/v2/shopping/items", json={"text": "Bröd"})

    assert forbidden.status_code == 403
    assert no_origin.status_code == 403
