from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.auth.service import Identity
from app.database.database import Database
from app.database.migrations import upgrade
from app.modules.experience.compass import HomeCompassService
from app.modules.experience.service import ExperienceService
from app.modules.family.repository import FamilyRepository
from app.modules.home.service import HomeService
from app.modules.planning.repository import PlanningRepository


ROOT = Path(__file__).resolve().parents[1]


def migrated_database(tmp_path: Path) -> Database:
    path = tmp_path / "profile-security.sqlite3"
    sqlite3.connect(path).close()
    upgrade(path, ROOT / "migrations")
    return Database(path)


def guest_identity() -> Identity:
    return Identity(
        user="guest",
        admin=False,
        sections=frozenset({"app", "family", "food", "weather"}),
        readonly=True,
        selected=True,
    )


def test_home_summary_does_not_query_hidden_planning_data(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    database.execute(
        "INSERT INTO home_reminders(id,title,owner,remind_at,note,done,created_at) "
        "VALUES('private-reminder','Privat tandläkartid','johnny','','',0,datetime('now'))"
    )
    summary = HomeService(FamilyRepository(database), PlanningRepository(database)).summary(guest_identity())
    assert summary["planning"]["available"] is False
    assert summary["planning"]["reminders"] == []
    assert summary["totals"]["open_reminders"] == 0
    assert "planning" not in summary["identity"]["sections"]


def test_experience_search_only_returns_allowed_domains(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    database.execute(
        "INSERT INTO home_reminders(id,title,owner,remind_at,note,done,created_at) "
        "VALUES('r1','Hemlig planering','johnny','','',0,datetime('now'))"
    )
    database.execute(
        "INSERT INTO shopping_lists(id,title,created_at,updated_at) "
        "VALUES('shopping','Inköp',datetime('now'),datetime('now'))"
    )
    database.execute(
        "INSERT INTO shopping_items(id,list_id,text,category,store,done,sort_order,owner,quantity,unit,created_at,completed_at,source) "
        "VALUES('s1','shopping','Hemlig inköpsvara','','',0,1,'johnny',1,'',datetime('now'),'','manual')"
    )
    service = ExperienceService(database)
    assert service.search("Hemlig planering", guest_identity())["results"] == []
    assert service.search("Hemlig inköpsvara", guest_identity())["results"] == []


def test_compass_does_not_offer_hidden_views(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    database.execute(
        "INSERT INTO home_reminders(id,title,owner,remind_at,note,done,created_at) "
        "VALUES('r1','Privat påminnelse','johnny','','',0,datetime('now'))"
    )
    database.execute(
        "INSERT INTO shopping_lists(id,title,created_at,updated_at) "
        "VALUES('shopping','Inköp',datetime('now'),datetime('now'))"
    )
    database.execute(
        "INSERT INTO shopping_items(id,list_id,text,category,store,done,sort_order,owner,quantity,unit,created_at,completed_at,source) "
        "VALUES('s1','shopping','Privat inköp','','',0,1,'johnny',1,'',datetime('now'),'','manual')"
    )
    compass = HomeCompassService(database).overview(guest_identity(), weather={}, presence=[])
    assert all(action["view"] not in {"planning", "shopping", "inventory"} for action in compass["actions"])
    assert "Privat" not in compass["summary"]


def test_personal_item_cannot_be_changed_by_another_profile(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    service = ExperienceService(database)
    johnny = Identity("johnny", False, frozenset({"app"}), False, True)
    kristina = Identity("kristina", False, frozenset({"app"}), False, True)
    item_id = service.add_forget_item(
        {"title": "Johnnys privata post", "note": "", "due_at": "", "owner": "kristina"},
        johnny,
    )
    stored = database.fetch_one("SELECT owner FROM forget_items WHERE id=?", (item_id,))
    assert stored["owner"] == "johnny"

    with pytest.raises(PermissionError):
        service.update_forget_item(item_id, {"title": "Ändrad"}, kristina)
    with pytest.raises(PermissionError):
        service.delete_forget_item(item_id, kristina)

    service.update_forget_item(item_id, {"title": "Min ändring"}, johnny)
    assert database.fetch_value("SELECT title FROM forget_items WHERE id=?", (item_id,)) == "Min ändring"
