from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.database.database import Database
from app.main import create_app


def make_client(tmp_path: Path, profiles: list[dict]) -> TestClient:
    database = Database(tmp_path / "access.sqlite3")
    with database.transaction() as connection:
        connection.executescript(
            """
            CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT);
            CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT);
            CREATE TABLE admin_sessions(token TEXT PRIMARY KEY,created_at TEXT,expires_at_epoch REAL);
            """
        )
        connection.execute(
            "INSERT INTO app_json_state(key,value,updated_at) VALUES('user_access',?,datetime('now'))",
            (json.dumps({"profiles": profiles}),),
        )
    app = create_app()
    app.state.database = database
    app.state.auth_service.database = database
    return TestClient(app)


def test_missing_section_is_rejected_before_router_execution(tmp_path: Path) -> None:
    client = make_client(
        tmp_path,
        [{"user": "viktor", "sections": ["app", "shopping"], "readonly": False}],
    )
    client.cookies.set("homelab_user", "viktor")
    response = client.get("/api/v2/budget/overview")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "section_forbidden"


def test_profile_readonly_blocks_mutations_but_not_safe_preview(tmp_path: Path) -> None:
    client = make_client(
        tmp_path,
        [{"user": "viktor", "sections": ["shopping", "budget"], "readonly": True}],
    )
    client.cookies.set("homelab_user", "viktor")
    mutation = client.post("/api/v2/shopping/items", json={})
    assert mutation.status_code == 423
    assert mutation.json()["error"]["code"] == "profile_read_only"

    # Excel preview is explicitly non-writing. Validation may reject the empty
    # request, but the access middleware must not reject it as a profile write.
    preview = client.post("/api/v2/budget/excel/preview")
    assert preview.status_code != 423


def test_access_control_returns_resolved_sections(tmp_path: Path) -> None:
    client = make_client(
        tmp_path,
        [{"user": "alfred", "sections": ["app", "food", "wishlists"], "readonly": True}],
    )
    client.cookies.set("homelab_user", "alfred")
    payload = client.get("/api/access-control").json()
    assert payload["user"] == "alfred"
    assert payload["sections"] == ["app", "food", "wishlists"]
    assert payload["readonly"] is True


def test_empty_configured_sections_do_not_remove_safe_defaults(tmp_path: Path) -> None:
    client = make_client(
        tmp_path,
        [{"user": "guest", "sections": [], "readonly": True}],
    )
    client.cookies.set("homelab_user", "guest")
    payload = client.get("/api/access-control").json()
    assert "app" in payload["sections"]
    assert payload["readonly"] is True
