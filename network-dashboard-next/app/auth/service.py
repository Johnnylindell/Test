from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import Settings
from app.database.database import Database


@dataclass(frozen=True, slots=True)
class Identity:
    user: str
    admin: bool


class AuthService:
    FAMILY_USERS = {"johnny", "kristina", "viktor", "alfred", "guest"}
    LOGIN_WINDOW_SECONDS = 600
    LOGIN_ATTEMPT_LIMIT = 5

    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 8:
            raise ValueError("Lösenordet måste vara minst åtta tecken")
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            200_000,
        ).hex()
        return f"pbkdf2_sha256${salt}${digest}"

    @staticmethod
    def _verify_pbkdf2(password: str, stored_hash: str) -> bool:
        try:
            scheme, salt, digest = stored_hash.split("$", 2)
            if scheme != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("ascii"),
                200_000,
            ).hex()
            return hmac.compare_digest(actual, digest)
        except (ValueError, UnicodeError):
            return False

    def verify_admin_password(self, password: str) -> bool:
        stored_hash = str(self.database.get_setting("admin_password_hash", "") or "")
        if stored_hash:
            return self._verify_pbkdf2(password, stored_hash)
        fallback = os.getenv("HOMELAB_ADMIN_PASSWORD", "")
        return bool(fallback) and hmac.compare_digest(password, fallback)

    def admin_password_configured(self) -> bool:
        return bool(
            str(self.database.get_setting("admin_password_hash", "") or "")
            or os.getenv("HOMELAB_ADMIN_PASSWORD", "")
        )

    def set_admin_password(self, password: str) -> None:
        password_hash = self.hash_password(password)
        self.database.execute(
            "INSERT INTO app_settings(key,value,updated_at) VALUES('admin_password_hash',?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (password_hash, datetime.now(timezone.utc).isoformat()),
        )

    def login_allowed(self, source: str) -> tuple[bool, int]:
        if not self.database.table_exists("login_attempts"):
            return True, 0
        cutoff = time.time() - self.LOGIN_WINDOW_SECONDS
        failures = int(
            self.database.fetch_value(
                "SELECT COUNT(*) FROM login_attempts WHERE source=? AND attempted_at_epoch>=? AND success=0",
                (source, cutoff),
                0,
            )
            or 0
        )
        if failures < self.LOGIN_ATTEMPT_LIMIT:
            return True, 0
        oldest = float(
            self.database.fetch_value(
                "SELECT MIN(attempted_at_epoch) FROM login_attempts WHERE source=? AND attempted_at_epoch>=? AND success=0",
                (source, cutoff),
                time.time(),
            )
            or time.time()
        )
        return False, max(1, int(oldest + self.LOGIN_WINDOW_SECONDS - time.time()))

    def record_login_attempt(self, source: str, success: bool) -> None:
        if not self.database.table_exists("login_attempts"):
            return
        now = time.time()
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM login_attempts WHERE attempted_at_epoch<?", (now - 86400,))
            connection.execute(
                "INSERT INTO login_attempts(source,attempted_at_epoch,success) VALUES(?,?,?)",
                (source[:200], now, 1 if success else 0),
            )
            if success:
                connection.execute("DELETE FROM login_attempts WHERE source=? AND success=0", (source[:200],))

    def create_admin_session(self) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        expires = now + self.settings.admin_session_seconds
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM admin_sessions WHERE expires_at_epoch <= ?", (now,))
            connection.execute(
                "INSERT OR REPLACE INTO admin_sessions(token,created_at,expires_at_epoch) VALUES(?,datetime('now'),?)",
                (token, expires),
            )
        return token

    def sessions(self) -> list[dict[str, object]]:
        if not self.database.table_exists("admin_sessions"):
            return []
        now = time.time()
        rows = self.database.fetch_all(
            "SELECT token,created_at,expires_at_epoch FROM admin_sessions WHERE expires_at_epoch>? ORDER BY created_at DESC",
            (now,),
        )
        return [
            {
                "token_hint": str(row["token"])[:6] + "…",
                "created_at": row.get("created_at"),
                "expires_at_epoch": row.get("expires_at_epoch"),
                "expires_at": datetime.fromtimestamp(
                    float(row.get("expires_at_epoch") or 0),
                    tz=timezone.utc,
                ).isoformat(),
                "current": False,
            }
            for row in rows
        ]

    def revoke_all_sessions(self, except_token: str | None = None) -> int:
        before = self.database.count("admin_sessions")
        if except_token:
            self.database.execute("DELETE FROM admin_sessions WHERE token<>?", (except_token,))
        else:
            self.database.execute("DELETE FROM admin_sessions")
        return max(0, before - self.database.count("admin_sessions"))

    def admin_session_valid(self, token: str | None) -> bool:
        if not token:
            return False
        row = self.database.fetch_one(
            "SELECT token FROM admin_sessions WHERE token=? AND expires_at_epoch > ?",
            (token, time.time()),
        )
        return bool(row)

    def revoke_admin_session(self, token: str | None) -> None:
        if token:
            self.database.execute("DELETE FROM admin_sessions WHERE token=?", (token,))

    def normalize_family_user(self, user: str | None) -> str:
        normalized = str(user or "").strip().lower()
        return normalized if normalized in self.FAMILY_USERS else "guest"

    def identity(self, admin_token: str | None, family_user: str | None) -> Identity:
        if self.admin_session_valid(admin_token):
            return Identity(user="admin", admin=True)
        return Identity(user=self.normalize_family_user(family_user), admin=False)
