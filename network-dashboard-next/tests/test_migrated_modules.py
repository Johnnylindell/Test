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
            CREATE TABLE family_profiles(id TEXT PRIMARY KEY, display_name TEXT, active INTEGER);
            CREATE TABLE family_lists(id TEXT PRIMARY KEY, title TEXT, sort_order INTEGER);
            CREATE TABLE family_list_items(
                id TEXT PRIMARY KEY, list_id TEXT, text TEXT, owner TEXT, done INTEGER, sort_order INTEGER
            );
            CREATE TABLE family_notes(id TEXT PRIMARY KEY, text TEXT, owner TEXT, created_at TEXT);
            CREATE TABLE home_reminders(id TEXT PRIMARY KEY, title TEXT, owner TEXT, due_at TEXT, done INTEGER);
            CREATE TABLE recurring_routine_rules(
                id TEXT PRIMARY KEY, title TEXT, owner TEXT, active INTEGER, schedule TEXT, sort_order INTEGER
            );
            CREATE TABLE recurring_routine_instances(
                id TEXT PRIMARY KEY, rule_id TEXT, title TEXT, scheduled_for TEXT, done INTEGER
            );
            CREATE TABLE home_checklist_items(
                id TEXT PRIMARY KEY, checklist_id TEXT, text TEXT, done INTEGER, sort_order INTEGER
            );
            INSERT INTO family_profiles VALUES('johnny','Johnny',1);
            INSERT INTO family_lists VALUES('todo','Att göra',1);
            INSERT INTO family_list_items VALUES('i1','todo','Testa nya appen','Johnny',0,1);
            INSERT INTO family_notes VALUES('n1','Kom ihåg testet','Johnny','2026-07-27T10:00:00Z');
            INSERT INTO home_reminders VALUES('r1','Betala räkning','Johnny','2026-07-28',0);
            INSERT INTO recurring_routine_rules VALUES('rr1','Vattna blommor','Johnny',1,'MO',1);
            INSERT INTO recurring_routine_instances VALUES('ri1','rr1','Vattna blommor','2026-07-27',0);
            INSERT INTO home_checklist_items VALUES('c1','morning','Lås dörren',0,1);
            """
        )


def test_migrated_api_contracts(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "family.sqlite3"
    seed_database(database_path)
    test_settings = replace(default_settings, database_path=database_path, port=0, cookie_secure=False)
    monkeypatch.setattr("app.main.settings", test_settings)
    app = create_app()

    with TestClient(app) as client:
        client.cookies.set("homelab_user", "johnny")
        home = client.get("/api/v2/home/summary")
        planning = client.get("/api/v2/planning/overview")
        family = client.get("/api/v2/family/overview")

    assert home.status_code == 200
    assert home.json()["totals"]["open_reminders"] == 1
    assert planning.status_code == 200
    assert planning.json()["totals"]["active_routines"] == 1
    assert family.status_code == 200
    assert family.json()["totals"]["open_items"] == 1
    assert family.json()["lists"][0]["items"][0]["text"] == "Testa nya appen"
