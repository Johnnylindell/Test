from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import settings as default_settings
from app.database.migrations import upgrade
from app.integrations.speech_transcription import SpeechTranscriptionAdapter
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def build_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, object]:
    database = tmp_path / "family_budget_next.sqlite3"
    sqlite3.connect(database).close()
    upgrade(database, ROOT / "migrations")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO admin_sessions(token,created_at,expires_at_epoch) "
            "VALUES('admin-token',datetime('now'),9999999999)"
        )
    monkeypatch.setattr(
        "app.main.settings",
        replace(
            default_settings,
            database_path=database,
            static_root=ROOT / "static",
            port=0,
            cookie_secure=False,
            read_only=True,
            external_side_effects=False,
            speech_transcription_enabled=False,
            speech_transcription_model="",
        ),
    )
    app = create_app()
    client = TestClient(app)
    client.cookies.set("homelab_session", "admin-token")
    return client, app


def test_advanced_overview_is_admin_only_and_sanitized(tmp_path: Path, monkeypatch) -> None:
    client, app = build_client(tmp_path, monkeypatch)
    app.state.cache.set("ha:status", {"ok": True}, 60)
    app.state.circuit_breaker.failure("home-assistant", "test failure")
    with client:
        client.cookies.clear()
        denied = client.get("/api/v2/admin/advanced/overview")
        client.cookies.set("homelab_session", "admin-token")
        response = client.get("/api/v2/admin/advanced/overview")
    assert denied.status_code == 403
    assert response.status_code == 200
    payload = response.json()
    assert payload["database"]["isolated_from_live"] is True
    assert payload["database"]["integrity"] == "ok"
    assert payload["migrations"]["pending"] == 0
    assert payload["cache"]["entries"] == 1
    assert payload["circuit_breakers"]["home-assistant"]["last_error"] == "test failure"
    assert payload["support_bundle"]["sensitive_values_exposed"] is False
    assert "token" not in str(payload["support_bundle"]).casefold()


def test_read_only_mode_allows_confirmed_in_memory_admin_controls(tmp_path: Path, monkeypatch) -> None:
    client, app = build_client(tmp_path, monkeypatch)
    app.state.cache.set("x", 1, 60)
    app.state.circuit_breaker.failure("example", "failure")
    headers = {"origin": "http://testserver"}
    with client:
        unconfirmed = client.post("/api/v2/admin/advanced/cache/clear", headers=headers, json={"confirm": False})
        cleared = client.post("/api/v2/admin/advanced/cache/clear", headers=headers, json={"confirm": True})
        reset = client.post("/api/v2/admin/advanced/breakers/reset", headers=headers, json={"confirm": True})
    assert unconfirmed.status_code == 400
    assert cleared.status_code == 200
    assert cleared.json()["removed"] == 1
    assert reset.status_code == 200
    assert reset.json()["removed"] == 1


def test_transcription_upload_is_same_origin_limited_and_not_persisted(tmp_path: Path, monkeypatch) -> None:
    client, app = build_client(tmp_path, monkeypatch)

    class FakeSpeech:
        max_bytes = 4

        @staticmethod
        def status() -> dict:
            return {"available": True, "audio_persisted": False, "sensitive_values_exposed": False}

        @staticmethod
        def transcribe(audio: bytes, *, suffix: str, language: str) -> dict:
            assert audio == b"abc"
            assert suffix == ".webm"
            assert language == "sv"
            return {"ok": True, "text": "hej världen", "audio_persisted": False}

    app.state.speech_transcription = FakeSpeech()
    with client:
        missing_origin = client.post(
            "/api/v2/assistant/transcribe",
            files={"file": ("voice.webm", b"abc", "audio/webm")},
        )
        unsupported = client.post(
            "/api/v2/assistant/transcribe",
            headers={"origin": "http://testserver"},
            files={"file": ("voice.txt", b"abc", "text/plain")},
        )
        too_large = client.post(
            "/api/v2/assistant/transcribe",
            headers={"origin": "http://testserver"},
            files={"file": ("voice.webm", b"abcde", "audio/webm")},
        )
        valid = client.post(
            "/api/v2/assistant/transcribe",
            headers={"origin": "http://testserver"},
            files={"file": ("voice.webm", b"abc", "audio/webm")},
        )
    assert missing_origin.status_code == 403
    assert unsupported.status_code == 415
    assert too_large.status_code == 413
    assert valid.status_code == 200
    assert valid.json()["text"] == "hej världen"


def test_local_transcriber_deletes_the_temporary_audio_file(monkeypatch) -> None:
    adapter = SpeechTranscriptionAdapter(enabled=True, model="model", max_bytes=1024)
    seen: dict[str, Path] = {}

    class FakeModel:
        @staticmethod
        def transcribe(path: str, **_: object):
            seen["path"] = Path(path)
            assert seen["path"].is_file()
            return [SimpleNamespace(text=" Hej från servern ")], SimpleNamespace(language="sv", duration=1.25)

    monkeypatch.setattr(adapter, "_load_model", lambda: FakeModel())
    result = adapter.transcribe(b"audio", suffix=".webm", language="sv")
    assert result["text"] == "Hej från servern"
    assert result["audio_persisted"] is False
    assert not seen["path"].exists()


def test_frontend_contracts_include_advanced_ui_and_media_recorder_fallback() -> None:
    advanced = (ROOT / "static" / "v2" / "advanced-admin.js").read_text(encoding="utf-8")
    assistant = (ROOT / "static" / "live" / "assistant.js").read_text(encoding="utf-8")
    index = (ROOT / "static" / "v2" / "index.html").read_text(encoding="utf-8")
    assert "data-advanced-view" in advanced
    assert "/api/v2/admin/advanced/overview" in advanced
    assert "support_bundle" in advanced
    assert "MediaRecorder" in assistant
    assert "/api/v2/assistant/transcribe" in assistant
    assert "advanced-admin.js" in index
