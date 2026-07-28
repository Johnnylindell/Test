from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.auth.service import ACCESS_SECTIONS, Identity
from app.database.database import Database
from app.database.migrations import upgrade
from app.modules.experience.compass import HomeCompassService


def migrated_database(tmp_path: Path) -> Database:
    path = tmp_path / "dashboard.sqlite3"
    sqlite3.connect(path).close()
    upgrade(path, Path(__file__).resolve().parents[1] / "migrations")
    return Database(path)


def johnny() -> Identity:
    return Identity(
        user="johnny",
        admin=False,
        sections=ACCESS_SECTIONS,
        readonly=False,
        selected=True,
    )


def test_compass_prioritizes_due_reminder(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    now = datetime.now(timezone.utc)
    database.execute(
        "INSERT INTO home_reminders(id,title,owner,remind_at,note,done,created_at) "
        "VALUES(?,?,?,?,?,0,?)",
        ("r1", "Hämta paket", "johnny", (now + timedelta(minutes=10)).isoformat(), "", now.isoformat()),
    )
    result = HomeCompassService(database).overview(
        johnny(),
        weather={"current": {"temperature": 12, "precipitation": 0}},
        presence=[],
    )
    assert result["ok"] is True
    assert result["actions"][0]["id"] == "reminder-now"
    assert "Hämta paket" in result["actions"][0]["detail"]
    assert len(result["actions"]) <= 4


def test_compass_never_exposes_presence_identifiers(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    result = HomeCompassService(database).overview(
        johnny(),
        weather={},
        presence=[
            {
                "name": "Kristina",
                "owner": "kristina",
                "present": True,
                "mac": "aa:bb:cc:dd:ee:ff",
                "ip": "192.168.1.23",
            },
            {
                "name": "Johnny",
                "owner": "johnny",
                "present": True,
                "mac": "11:22:33:44:55:66",
                "ip": "192.168.1.24",
            },
        ],
    )
    serialized = str(result)
    assert "aa:bb:cc" not in serialized
    assert "192.168." not in serialized
    family_action = next(row for row in result["actions"] if row["id"] == "family-touchpoint")
    assert "Kristina" in family_action["detail"]
    assert "Johnny" in family_action["detail"]
