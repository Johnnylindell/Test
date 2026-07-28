from __future__ import annotations

import pytest

from app.auth.service import Identity
from app.database.database import Database
from app.modules.assistant.service import AssistantService


SECRET = "assistant-test-secret-" + "a" * 40


def database(tmp_path) -> Database:
    db = Database(tmp_path / "assistant.sqlite3")
    with db.transaction() as connection:
        connection.executescript(
            """
            CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT);
            CREATE TABLE assistant_confirmations(
                token_hash TEXT PRIMARY KEY,user TEXT NOT NULL,action TEXT NOT NULL,consumed_at TEXT NOT NULL
            );
            CREATE TABLE shopping_lists(
                id TEXT PRIMARY KEY,title TEXT,created_at TEXT,updated_at TEXT
            );
            CREATE TABLE shopping_items(
                id TEXT PRIMARY KEY,list_id TEXT,text TEXT,category TEXT,store TEXT,
                done INTEGER,sort_order INTEGER,owner TEXT,quantity REAL,unit TEXT,
                created_at TEXT,completed_at TEXT DEFAULT '',source TEXT
            );
            """
        )
    return db


def identity(user: str, *sections: str) -> Identity:
    return Identity(
        user=user,
        admin=False,
        sections=frozenset(sections),
        readonly=False,
        selected=True,
    )


def test_query_creates_signed_proposal_without_writing(tmp_path) -> None:
    db = database(tmp_path)
    assistant = AssistantService(db, SECRET)
    johnny = identity("johnny", "app", "shopping")
    before = db.count("assistant_confirmations")
    result = assistant.query("Lägg mjölk på inköpslistan", johnny)
    assert result["requires_confirmation"] is True
    assert result["network_model_used"] is False
    assert result["proposal"]["token"].count(".") == 1
    assert db.count("assistant_confirmations") == before
    assert db.count("shopping_items") == 0


def test_confirmation_is_user_bound_and_one_time(tmp_path) -> None:
    db = database(tmp_path)
    assistant = AssistantService(db, SECRET)
    johnny = identity("johnny", "app", "shopping")
    kristina = identity("kristina", "app", "shopping")
    token = assistant.query("Köp mjölk", johnny)["proposal"]["token"]

    with pytest.raises(ValueError, match="annan profil"):
        assistant.confirm(token, kristina)
    result = assistant.confirm(token, johnny)
    assert result["action"] == "shopping.add"
    assert db.count("shopping_items") == 1
    with pytest.raises(ValueError, match="redan använts"):
        assistant.confirm(token, johnny)
    assert db.count("shopping_items") == 1


def test_tampered_confirmation_is_rejected(tmp_path) -> None:
    db = database(tmp_path)
    assistant = AssistantService(db, SECRET)
    johnny = identity("johnny", "app", "shopping")
    token = assistant.query("Köp kaffe", johnny)["proposal"]["token"]
    encoded, signature = token.split(".", 1)
    tampered = encoded[:-1] + ("A" if encoded[-1] != "A" else "B") + "." + signature
    with pytest.raises(ValueError, match="manipulerats"):
        assistant.confirm(tampered, johnny)


def test_revoked_permission_blocks_an_existing_confirmation(tmp_path) -> None:
    db = database(tmp_path)
    assistant = AssistantService(db, SECRET)
    permitted = identity("johnny", "app", "shopping")
    token = assistant.query("Köp kaffe", permitted)["proposal"]["token"]
    revoked = identity("johnny", "app")

    with pytest.raises(PermissionError, match="behörighet"):
        assistant.confirm(token, revoked)
    assert db.count("shopping_items") == 0
    assert db.count("assistant_confirmations") == 0


def test_profile_without_section_gets_no_mutation_proposal(tmp_path) -> None:
    db = database(tmp_path)
    assistant = AssistantService(db, SECRET)
    result = assistant.query("Köp kaffe", identity("guest", "app"))
    assert result["intent"] == "access_denied"
    assert result["requires_confirmation"] is False
    assert result["proposal"] is None


def test_help_queries_do_not_require_confirmation(tmp_path) -> None:
    db = database(tmp_path)
    assistant = AssistantService(db, SECRET)
    result = assistant.query("Vad kan du göra", identity("johnny", "app"))
    assert result["intent"] == "help"
    assert result["requires_confirmation"] is False
