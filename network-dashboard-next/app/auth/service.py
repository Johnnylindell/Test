from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.database.database import Database


@dataclass(frozen=True, slots=True)
class Identity:
    user: str
    admin: bool


class AuthService:
    FAMILY_USERS = {"johnny", "kristina", "viktor", "guest"}

    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

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
        fallback = os.getenv("HOMELAB_ADMIN_PASSWORD", "1234")
        return hmac.compare_digest(password, fallback)

    def create_admin_session(self) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        expires = now + self.settings.admin_session_seconds
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM admin_sessions WHERE expires_at_epoch <= ?", (now,))
            connection.execute(
                "INSERT OR REPLACE INTO admin_sessions(token,created_at,expires_at_epoch) "
                "VALUES(?,datetime('now'),?)",
                (token, expires),
            )
        return token

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
