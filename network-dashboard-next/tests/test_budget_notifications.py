from __future__ import annotations

import json
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
            CREATE TABLE app_json_state(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
            CREATE TABLE budget_sheets(id INTEGER PRIMARY KEY, name TEXT, kind TEXT, sort_order INTEGER);
            CREATE TABLE budget_cells(sheet_id INTEGER,row_num INTEGER,col_num INTEGER,value TEXT,updated_at TEXT,PRIMARY KEY(sheet_id,row_num,col_num));
            CREATE TABLE push_subscriptions(id INTEGER PRIMARY KEY AUTOINCREMENT,endpoint TEXT UNIQUE,user TEXT,subscription TEXT,created_at TEXT);
            INSERT INTO budget_sheets VALUES(1,'Juli','month',7);
            INSERT INTO budget_cells VALUES(1,18,2,'Lön','',NULL);
            INSERT INTO budget_cells VALUES(1,18,3,'5000','',NULL);
            INSERT INTO budget_cells VALUES(1,18,5,'Boende','',NULL);
            INSERT INTO budget_cells VALUES(1,18,6,'1200','',NULL);
            INSERT INTO budget_cells VALUES(1,18,7,'1100','',NULL);
            INSERT INTO app_json_state VALUES('alerts','[]','');
            """.replace(",NULL", "")
        )


def test_budget_and_notifications(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "family.sqlite3"
    seed(database_path)
    monkeypatch.setattr(
        "app.main.settings",
        replace(default_settings, database_path=database_path, port=0, cookie_secure=False),
    )
    app = create_app()
    origin = {"Origin": "http://testserver"}

    with TestClient(app) as client:
        client.cookies.set("homelab_user", "johnny")
        budget = client.get("/api/v2/budget/overview?sheet=Juli")
        assert budget.status_code == 200
        assert budget.json()["budget"]["totals"]["balance_actual"] == 3900

        added = client.post(
            "/api/v2/budget/entries",
            headers=origin,
            json={"sheet": "Juli", "kind": "savings", "label": "Buffert", "value": 300},
        )
        assert added.status_code == 200

        subscription = {
            "subscription": {
                "endpoint": "https://push.example/subscription",
                "expirationTime": None,
                "keys": {"p256dh": "abc", "auth": "def"},
            }
        }
        assert client.post("/api/v2/notifications/subscriptions", headers=origin, json=subscription).status_code == 200

        with sqlite3.connect(database_path) as db:
            db.execute("INSERT INTO admin_sessions VALUES('token','',9999999999)")
            db.commit()
        client.cookies.set("homelab_session", "token")
        alert = client.post(
            "/api/v2/notifications/alerts",
            headers=origin,
            json={"type": "budget", "message": "Budgettest", "target": "johnny"},
        )
        assert alert.status_code == 200
        alert_id = alert.json()["id"]
        client.cookies.set("homelab_session", "")
        ack = client.post(f"/api/v2/notifications/alerts/{alert_id}/ack", headers=origin)
        assert ack.status_code == 200

    with sqlite3.connect(database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM push_subscriptions").fetchone()[0] == 1
        alerts = json.loads(db.execute("SELECT value FROM app_json_state WHERE key='alerts'").fetchone()[0])
        assert alerts[0]["acknowledged_at"]
