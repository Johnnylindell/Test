from pathlib import Path

from fastapi.testclient import TestClient

from app.database.database import Database
from app.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    database_path = tmp_path / "dashboard.sqlite3"
    database = Database(database_path)
    with database.transaction() as connection:
        connection.execute("CREATE TABLE app_json_state(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
        connection.execute(
            "CREATE TABLE admin_sessions(token TEXT PRIMARY KEY,created_at TEXT,expires_at_epoch REAL)"
        )
        connection.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)")
    app = create_app()
    app.state.database = database
    app.state.auth_service.database = database
    return TestClient(app)


def test_live_shell_and_shared_assets(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.cookies.set("homelab_user", "johnny")
    page = client.get("/")
    assert page.status_code == 200
    assert "Familjens vardag, samlad" in page.text
    assert "/live/app.js" in page.text
    assert "/live/pwa.js" in page.text
    assert "/manifest.webmanifest" in page.text
    assert 'data-view="home"' in page.text
    assert 'data-view="more"' in page.text

    script = client.get("/live/app.js")
    assert script.status_code == 200
    assert "application/javascript" in script.headers["content-type"] or "text/javascript" in script.headers["content-type"]
    assert "/api/v2/home/summary" in script.text
    assert "/api/v2/experience/compass" in script.text

    shared = client.get("/assets/api.js")
    assert shared.status_code == 200
    assert "same-origin" in shared.text


def test_profile_selector_contains_all_family_profiles(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    page = client.get("/choose-user")
    assert page.status_code == 200
    for user in ("johnny", "kristina", "viktor", "alfred", "guest"):
        assert f'value="{user}"' in page.text
    assert "/assets/entry.css" in page.text


def test_pwa_assets_and_service_worker_scope(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.cookies.set("homelab_user", "johnny")
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert "application/manifest+json" in manifest.headers["content-type"]
    assert manifest.json()["display"] == "standalone"

    worker = client.get("/sw.js")
    assert worker.status_code == 200
    assert worker.headers["service-worker-allowed"] == "/"
    assert "no-store" in worker.headers["cache-control"]
    assert 'url.pathname.startsWith("/api/")' in worker.text


def test_version_two_assets_require_admin(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.cookies.set("homelab_user", "johnny")
    assert client.get("/preview-v2", follow_redirects=False).status_code == 403
    assert client.get("/preview-v2/app.js", follow_redirects=False).status_code == 403


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.cookies.set("homelab_user", "johnny")
    response = client.get("/assets/../live/index.html", follow_redirects=False)
    assert response.status_code in {404, 307}
