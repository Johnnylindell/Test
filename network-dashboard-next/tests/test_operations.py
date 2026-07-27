from __future__ import annotations

import hashlib

import pytest

from app.database.database import Database
from app.modules.operations.service import OperationsService


def schema(database: Database) -> None:
    with database.transaction() as connection:
        connection.executescript(
            """
            CREATE TABLE managed_services(
                id TEXT PRIMARY KEY,label TEXT,unit_name TEXT UNIQUE,active INTEGER,
                created_at TEXT,updated_at TEXT
            );
            CREATE TABLE computer_agents_v2(
                id TEXT PRIMARY KEY,name TEXT,token_hash TEXT UNIQUE,active INTEGER,
                last_seen TEXT,status_json TEXT,created_at TEXT,updated_at TEXT
            );
            CREATE TABLE agent_commands_v2(
                id TEXT PRIMARY KEY,agent_id TEXT,command_type TEXT,payload_json TEXT,status TEXT,
                created_by TEXT,created_at TEXT,claimed_at TEXT,completed_at TEXT,result_json TEXT
            );
            CREATE TABLE homelab_baselines_v2(
                id TEXT PRIMARY KEY,label TEXT,snapshot_json TEXT,created_by TEXT,created_at TEXT
            );
            """
        )


def test_agent_token_is_returned_once_and_only_hash_is_stored(tmp_path) -> None:
    database = Database(tmp_path / "operations.sqlite3")
    schema(database)
    service = OperationsService(database)
    created = service.create_agent("Testdator")
    stored = database.fetch_one("SELECT token_hash FROM computer_agents_v2 WHERE id=?", (created["id"],))
    assert stored is not None
    assert created["token"] not in stored["token_hash"]
    assert stored["token_hash"] == hashlib.sha256(created["token"].encode()).hexdigest()
    assert service.authenticate_agent(created["token"])["id"] == created["id"]
    assert "token" not in service.agents()[0]


def test_agent_commands_are_allowlisted_and_claimed_once(tmp_path) -> None:
    database = Database(tmp_path / "commands.sqlite3")
    schema(database)
    service = OperationsService(database)
    agent = service.create_agent("Testdator")
    command_id = service.queue_command(agent["id"], "notify", {"message": "Hej"}, "admin")
    first = service.claim_commands(agent["id"])
    second = service.claim_commands(agent["id"])
    assert [row["id"] for row in first] == [command_id]
    assert second == []
    assert service.complete_command(agent["id"], command_id, "completed", {"ok": True}) is True
    assert service.complete_command(agent["id"], command_id, "completed", {"ok": True}) is False
    with pytest.raises(ValueError, match="inte tillåtet"):
        service.queue_command(agent["id"], "shell", {"command": "rm -rf /"}, "admin")


def test_notify_command_strips_unapproved_payload_fields(tmp_path) -> None:
    database = Database(tmp_path / "payload.sqlite3")
    schema(database)
    service = OperationsService(database)
    agent = service.create_agent("Testdator")
    service.queue_command(
        agent["id"],
        "notify",
        {"message": "Hej", "command": "shutdown", "url": "file:///etc/passwd"},
        "admin",
    )
    command = service.claim_commands(agent["id"])[0]
    assert command["payload"] == {"message": "Hej"}


def test_service_allowlist_rejects_shell_syntax(tmp_path) -> None:
    database = Database(tmp_path / "services.sqlite3")
    schema(database)
    service = OperationsService(database)
    with pytest.raises(ValueError, match="Ogiltigt"):
        service.add_service("Bad", "x.service;rm -rf /")
    service_id = service.add_service("Watcher", "hermes-lan-watch.service")
    row = database.fetch_one("SELECT unit_name FROM managed_services WHERE id=?", (service_id,))
    assert row["unit_name"] == "hermes-lan-watch.service"


def test_operations_overview_never_exposes_shell_scan_or_tokens(tmp_path) -> None:
    database = Database(tmp_path / "overview.sqlite3")
    schema(database)
    service = OperationsService(database)
    service.create_agent("Testdator")
    overview = service.overview()
    assert overview["arbitrary_shell_exposed"] is False
    assert overview["active_network_scan_exposed"] is False
    assert overview["agent_token_exposed"] is False
    assert "token" not in str(overview["agents"]).casefold()
