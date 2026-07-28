from __future__ import annotations

import json
from typing import Any

import httpx
from pywebpush import WebPushException, webpush

from app.integrations.config_store import IntegrationConfigStore
from app.modules.notifications.repository import NotificationsRepository


class NotificationDeliveryAdapter:
    def __init__(self, repository: NotificationsRepository, config: IntegrationConfigStore) -> None:
        self.repository = repository
        self.config = config

    def _vapid(self) -> tuple[str, str]:
        private_key = self.config.get("vapid_private_key")
        subject = self.config.get("vapid_subject", "mailto:admin@localhost")
        if not private_key:
            raise RuntimeError("VAPID private key saknas")
        return private_key, subject

    def push(self, payload: dict[str, Any], target: str = "all") -> dict[str, Any]:
        private_key, subject = self._vapid()
        sent = 0
        failed = 0
        stale: list[str] = []
        details = []
        target_key = target.strip().lower()
        for row in self.repository.subscriptions():
            user = str(row.get("user") or "").strip().lower()
            if target_key not in {"", "all", "family"} and user != target_key:
                continue
            subscription = row["subscription"]
            endpoint = str(subscription.get("endpoint") or "")
            try:
                webpush(
                    subscription_info=subscription,
                    data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    vapid_private_key=private_key,
                    vapid_claims={"sub": subject},
                    ttl=300,
                )
                sent += 1
            except WebPushException as exc:
                failed += 1
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in {404, 410} and endpoint:
                    stale.append(endpoint)
                details.append({
                    "user": user,
                    "status": status_code or 0,
                    "error": str(exc)[:240],
                })
            except Exception as exc:
                failed += 1
                details.append({"user": user, "status": 0, "error": str(exc)[:240]})
        deleted = self.repository.delete_invalid_subscriptions(stale)
        return {
            "ok": failed == 0,
            "sent": sent,
            "failed": failed,
            "stale_deleted": deleted,
            "details": details[:50],
        }

    def discord(self, message: str) -> dict[str, Any]:
        webhook = self.config.get("discord_webhook_url").strip()
        if not webhook:
            raise RuntimeError("Discord-webhook saknas")
        response = httpx.post(
            webhook,
            json={"content": message[:1900]},
            timeout=10,
            follow_redirects=False,
        )
        return {
            "ok": response.is_success,
            "status": response.status_code,
        }

    def deliver(
        self,
        *,
        title: str,
        message: str,
        target: str = "all",
        severity: str = "normal",
        send_push: bool = True,
        send_discord: bool = False,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": True,
            "target": target,
            "push": {"skipped": True},
            "discord": {"skipped": True},
        }
        if send_push:
            try:
                result["push"] = self.push(
                    {
                        "title": title[:120],
                        "body": message[:500],
                        "severity": severity[:30],
                        "target": target[:80],
                    },
                    target,
                )
            except Exception as exc:
                result["push"] = {"ok": False, "error": str(exc)[:240]}
        if send_discord:
            try:
                result["discord"] = self.discord(f"**{title[:120]}**\n{message[:1800]}")
            except Exception as exc:
                result["discord"] = {"ok": False, "error": str(exc)[:240]}
        attempted = [value for value in (result["push"], result["discord"]) if not value.get("skipped")]
        result["ok"] = bool(attempted) and all(value.get("ok") for value in attempted)
        return result
