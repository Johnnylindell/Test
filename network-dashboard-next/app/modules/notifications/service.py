from __future__ import annotations

import secrets
from typing import Any

from app.auth.service import Identity
from app.modules.notifications.repository import NotificationsRepository, now_iso


class NotificationsService:
    def __init__(self, repository: NotificationsRepository) -> None:
        self.repository = repository

    def overview(self, identity: Identity) -> dict:
        items = self.repository.alerts(identity.user)
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "items": items,
            "unread": sum(not item["read"] for item in items),
        }

    def subscribe(self, identity: Identity, subscription: dict[str, Any]) -> dict:
        self.repository.upsert_subscription(identity.user, subscription)
        return {"ok": True}

    def create_alert(self, identity: Identity, payload: dict[str, Any]) -> dict:
        alert = {
            "id": secrets.token_urlsafe(12),
            "type": payload["type"],
            "message": payload["message"],
            "target": payload["target"],
            "severity": payload["severity"],
            "metadata": payload.get("metadata") or {},
            "created_at": now_iso(),
            "acknowledged_at": None,
            "created_by": identity.user,
        }
        return self.repository.create_alert(alert)
