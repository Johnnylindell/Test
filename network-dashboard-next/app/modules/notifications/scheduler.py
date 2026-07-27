from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from app.database.database import Database
from app.integrations.notification_delivery import NotificationDeliveryAdapter
from app.modules.notifications.evaluator import SmartNotificationEvaluator
from app.modules.notifications.repository import NotificationsRepository

logger = logging.getLogger("network-dashboard-next.notifications")


class NotificationScheduler:
    def __init__(
        self,
        database: Database,
        delivery: NotificationDeliveryAdapter,
        interval_seconds: int = 300,
    ) -> None:
        self.database = database
        self.delivery = delivery
        self.interval_seconds = max(60, min(int(interval_seconds), 86400))
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="notification-scheduler")

    async def stop(self) -> None:
        self._stop.set()
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        repository = NotificationsRepository(self.database)
        evaluator = SmartNotificationEvaluator(self.database, repository)
        while not self._stop.is_set():
            try:
                result = await asyncio.to_thread(evaluator.evaluate, trigger="auto")
                for alert in result.get("created", []):
                    await asyncio.to_thread(
                        self.delivery.deliver,
                        title="Lindells app",
                        message=str(alert.get("message") or ""),
                        target=str(alert.get("target") or "all"),
                        severity=str(alert.get("severity") or "normal"),
                        send_push=True,
                        send_discord=False,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduled notification evaluation failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
