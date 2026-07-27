from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    host: str
    port: int
    legacy_origin: str
    database_path: Path
    static_root: Path
    admin_session_seconds: int
    cookie_secure: bool


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[2]
    return Settings(
        app_name=os.getenv("DASHBOARD_APP_NAME", "Lindells app Next"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "0")),
        legacy_origin=os.getenv("LEGACY_ORIGIN", "http://127.0.0.1:8792").rstrip("/"),
        database_path=Path(
            os.getenv(
                "DASHBOARD_DB_PATH",
                str(Path.home() / ".hermes" / "state" / "family_budget.sqlite3"),
            )
        ).expanduser(),
        static_root=Path(os.getenv("DASHBOARD_STATIC_ROOT", str(root / "static"))).expanduser(),
        admin_session_seconds=max(
            300,
            min(8 * 3600, int(os.getenv("HOMELAB_ADMIN_SESSION_SECONDS", "7200"))),
        ),
        cookie_secure=os.getenv("COOKIE_SECURE", "true").lower() not in {"0", "false", "no"},
    )


settings = load_settings()
