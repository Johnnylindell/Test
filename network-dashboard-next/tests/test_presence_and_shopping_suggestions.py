from __future__ import annotations

import sqlite3
from pathlib import Path

from app.database.database import Database
from app.database.migrations import upgrade
from app.modules.presence.service import PresenceService
from app.modules.shopping.repository import ShoppingRepository
from app.modules.shopping.service import ShoppingService


def migrated_database(tmp_path: Path) -> Database:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "dashboard.sqlite3"
    sqlite3.connect(path).close()
    upgrade(path, Path(__file__).resolve().parents[1] / "migrations")
    return Database(path)


def test_presence_hashes_identifier_and_alerts_only_on_real_arrival(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    service = PresenceService(database, "hash-secret-for-tests")
    raw_identifier = "AA:BB:CC:DD:EE:FF"
    registered = service.register("Johnny", "Johnnys telefon", raw_identifier)
    assert registered["device"]["owner"] == "Johnny"

    stored = database.fetch_one("SELECT * FROM presence_devices")
    assert stored is not None
    assert raw_identifier not in str(stored)
    assert len(stored["source_hash"]) == 64

    first = service.observe(raw_identifier, True)
    assert first["transition"] is False
    assert first["alert"] is None

    departed = service.observe(raw_identifier, False)
    assert departed["transition"] is True
    assert departed["alert"] is None

    arrived = service.observe(raw_identifier, True)
    assert arrived["transition"] is True
    assert arrived["alert"]["message"] == "Johnny kom hem."
    overview = service.overview()
    assert overview["privacy"] == {
        "raw_identifiers_stored": False,
        "raw_network_values_exposed": False,
    }
    assert raw_identifier not in str(overview)


def test_arrival_cooldown_suppresses_repeated_alert(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    service = PresenceService(database, "hash-secret-for-tests")
    service.register("Kristina", "Telefon", "device-kristina")
    service.observe("device-kristina", False)
    first = service.observe("device-kristina", True, cooldown_minutes=60)
    service.observe("device-kristina", False)
    second = service.observe("device-kristina", True, cooldown_minutes=60)
    assert first["alert"] is not None
    assert second["alert"] is None


def test_completed_history_creates_nonduplicate_suggestions(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    repository = ShoppingRepository(database)
    service = ShoppingService(database)
    payload = {
        "list_id": "shopping",
        "text": "Mjölk",
        "quantity": 2,
        "unit": "l",
        "category": "Mejeri",
        "store": "Matbutiken",
    }
    first_id = repository.add(payload, "johnny")
    service.complete(first_id, True)
    second_id = repository.add(payload, "johnny")
    service.complete(second_id, True)

    suggestions = service.smart_suggestions()
    assert len(suggestions) == 1
    assert suggestions[0]["text"] == "Mjölk"
    assert suggestions[0]["purchases"] == 2

    added_id = service.add_suggestion(suggestions[0]["id"], "johnny")
    assert added_id
    assert service.smart_suggestions() == []
