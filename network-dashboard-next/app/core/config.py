from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


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
    read_only: bool
    allow_legacy_writes: bool
    external_side_effects: bool
    presence_hash_secret: str
    presence_ingest_token: str
    assistant_signing_secret: str
    integration_secrets_path: Path
    notification_scheduler_enabled: bool
    notification_scheduler_seconds: int
    google_token_path: Path
    google_client_secrets_path: Path
    home_assistant_verify_tls: bool
    home_assistant_ca_bundle: Path | None
    speech_transcription_enabled: bool
    speech_transcription_model: str
    speech_transcription_device: str
    speech_transcription_compute_type: str
    speech_transcription_max_bytes: int
    speech_transcription_allow_model_download: bool


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[2]
    config_root = Path.home() / ".config" / "network-dashboard-next"
    ca_value = os.getenv("HOME_ASSISTANT_CA_BUNDLE", "").strip()
    return Settings(
        app_name=os.getenv("DASHBOARD_APP_NAME", "Lindells app Next"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "0")),
        legacy_origin=os.getenv("LEGACY_ORIGIN", "http://127.0.0.1:8792").rstrip("/"),
        database_path=Path(
            os.getenv(
                "DASHBOARD_DB_PATH",
                str(Path.home() / ".hermes" / "state" / "family_budget_next.sqlite3"),
            )
        ).expanduser(),
        static_root=Path(os.getenv("DASHBOARD_STATIC_ROOT", str(root / "static"))).expanduser(),
        admin_session_seconds=max(
            300,
            min(8 * 3600, int(os.getenv("HOMELAB_ADMIN_SESSION_SECONDS", "7200"))),
        ),
        cookie_secure=_flag("COOKIE_SECURE", True),
        read_only=_flag("DASHBOARD_READ_ONLY", False),
        allow_legacy_writes=_flag("ALLOW_LEGACY_WRITES", False),
        external_side_effects=_flag("EXTERNAL_SIDE_EFFECTS", False),
        presence_hash_secret=os.getenv("PRESENCE_HASH_SECRET", ""),
        presence_ingest_token=os.getenv("PRESENCE_INGEST_TOKEN", ""),
        assistant_signing_secret=os.getenv("ASSISTANT_SIGNING_SECRET", ""),
        integration_secrets_path=Path(
            os.getenv("INTEGRATION_SECRETS_PATH", str(config_root / "integration-secrets.json"))
        ).expanduser(),
        notification_scheduler_enabled=_flag("NOTIFICATION_SCHEDULER_ENABLED", False),
        notification_scheduler_seconds=max(
            60,
            min(86400, int(os.getenv("NOTIFICATION_SCHEDULER_SECONDS", "300"))),
        ),
        google_token_path=Path(
            os.getenv("GOOGLE_TOKEN_PATH", str(config_root / "google_token.json"))
        ).expanduser(),
        google_client_secrets_path=Path(
            os.getenv("GOOGLE_CLIENT_SECRETS_PATH", str(config_root / "google_client_secret.json"))
        ).expanduser(),
        home_assistant_verify_tls=_flag("HOME_ASSISTANT_VERIFY_TLS", True),
        home_assistant_ca_bundle=Path(ca_value).expanduser() if ca_value else None,
        speech_transcription_enabled=_flag("SPEECH_TRANSCRIPTION_ENABLED", False),
        speech_transcription_model=os.getenv("SPEECH_TRANSCRIPTION_MODEL", "").strip(),
        speech_transcription_device=os.getenv("SPEECH_TRANSCRIPTION_DEVICE", "cpu").strip() or "cpu",
        speech_transcription_compute_type=(
            os.getenv("SPEECH_TRANSCRIPTION_COMPUTE_TYPE", "int8").strip() or "int8"
        ),
        speech_transcription_max_bytes=max(
            64 * 1024,
            min(
                50 * 1024 * 1024,
                int(os.getenv("SPEECH_TRANSCRIPTION_MAX_BYTES", str(8 * 1024 * 1024))),
            ),
        ),
        speech_transcription_allow_model_download=_flag(
            "SPEECH_TRANSCRIPTION_ALLOW_MODEL_DOWNLOAD",
            False,
        ),
    )


settings = load_settings()
