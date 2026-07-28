from dataclasses import replace
from pathlib import Path

from app.auth.service import AuthService
from app.core.config import Settings, settings as default_settings
from app.database.database import Database


def _settings(path: Path) -> Settings:
    return replace(
        default_settings,
        app_name="test",
        host="127.0.0.1",
        port=0,
        legacy_origin="http://127.0.0.1:8792",
        database_path=path,
        static_root=path.parent / "static",
        admin_session_seconds=600,
        cookie_secure=False,
        integration_secrets_path=path.parent / "integration-secrets.json",
        google_token_path=path.parent / "google-token.json",
        google_client_secrets_path=path.parent / "google-client.json",
    )


def test_admin_session_lifecycle(tmp_path: Path) -> None:
    path = tmp_path / "app.sqlite3"
    database = Database(path)
    database.execute(
        "CREATE TABLE admin_sessions(token TEXT PRIMARY KEY, created_at TEXT, expires_at_epoch REAL)"
    )
    database.execute(
        "CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
    )
    auth = AuthService(database, _settings(path))

    token = auth.create_admin_session()
    assert auth.admin_session_valid(token)
    auth.revoke_admin_session(token)
    assert not auth.admin_session_valid(token)


def test_family_user_is_allowlisted(tmp_path: Path) -> None:
    path = tmp_path / "app.sqlite3"
    auth = AuthService(Database(path), _settings(path))
    assert auth.normalize_family_user("Johnny") == "johnny"
    assert auth.normalize_family_user("unknown") == "guest"
