from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.auth.service import Identity
from app.database.database import Database
from app.modules.family.repository import FamilyRepository
from app.modules.food.repository import FoodRepository
from app.modules.planning.repository import PlanningRepository
from app.modules.shopping.repository import ShoppingRepository

APP_TZ = ZoneInfo("Europe/Mariehamn")


class HomeCompassService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.family = FamilyRepository(database)
        self.food = FoodRepository(database)
        self.planning = PlanningRepository(database)
        self.shopping = ShoppingRepository(database)

    @staticmethod
    def _mode(hour: int) -> dict[str, str]:
        if 5 <= hour < 10:
            return {"id": "morning", "emoji": "🌅", "title": "Morgonläge", "tone": "Starta lugnt"}
        if 10 <= hour < 16:
            return {"id": "day", "emoji": "🧭", "title": "Dagsläge", "tone": "Nästa bästa steg"}
        if 16 <= hour < 21:
            return {"id": "evening", "emoji": "🌙", "title": "Kvällsläge", "tone": "Gör kvällen lättare"}
        return {"id": "quiet", "emoji": "🛋️", "title": "Lugnläge", "tone": "Inget stort behövs"}

    @staticmethod
    def _allowed(identity: Identity, section: str) -> bool:
        return identity.admin or section in identity.sections

    def overview(
        self,
        identity: Identity,
        *,
        weather: dict[str, Any] | None = None,
        presence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(APP_TZ)
        reminders = []
        if self._allowed(identity, "planning"):
            reminders = [row for row in self.planning.reminders(limit=30) if not row.get("done")]
        shopping = self.shopping.overview().get("active") or [] if self._allowed(identity, "shopping") else []
        meals = self.food.weekly_meals() if self._allowed(identity, "food") else []
        lists = self.family.lists() if self._allowed(identity, "family") else []
        assigned = []
        for family_list in lists:
            for item in family_list.get("items") or []:
                owner = str(item.get("owner") or "").casefold()
                if not item.get("done") and (
                    not owner or owner in {identity.user.casefold(), "all", "family", "alla"}
                ):
                    assigned.append({**item, "list_title": family_list.get("title")})

        actions: list[dict[str, Any]] = []

        def add(action_id: str, title: str, detail: str, emoji: str, view: str, weight: int) -> None:
            actions.append({
                "id": action_id,
                "title": title,
                "detail": detail,
                "emoji": emoji,
                "view": view,
                "weight": weight,
            })

        if reminders:
            reminder = reminders[0]
            add(
                "reminder-now",
                "Kolla första påminnelsen",
                str(reminder.get("title") or "Det finns något aktuellt att komma ihåg."),
                "🔔",
                "planning",
                0,
            )
        if assigned:
            item = assigned[0]
            add(
                "my-first-task",
                "Ta din minsta uppgift",
                str(item.get("text") or item.get("title") or "Bocka av en liten sak."),
                "✅",
                "dashboard",
                5,
            )

        today_names = {now.date().isoformat(), str(now.weekday()), now.strftime("%A").casefold()}
        today_meal = next(
            (
                row
                for row in meals
                if str(row.get("day") or "").casefold() in today_names
                or str(row.get("date") or "")[:10] == now.date().isoformat()
            ),
            None,
        )
        if self._allowed(identity, "food"):
            if not today_meal and now.hour >= 13:
                add(
                    "meal-decision",
                    "Ta middagsbeslutet nu",
                    "Välj en enkel middag — perfekt behöver den inte vara.",
                    "🍽️",
                    "food",
                    8,
                )
            elif today_meal and now.hour >= 15:
                add(
                    "meal-prep-compass",
                    "Förbered två minuter mat",
                    f"Dagens mat: {today_meal.get('title') or 'planerad rätt'}. Ta fram något redan nu.",
                    "🥘",
                    "food",
                    12,
                )

        if shopping:
            sample = ", ".join(str(item.get("text") or "") for item in shopping[:2] if item.get("text"))
            add(
                "shopping-glance",
                "Snabbkolla inköp",
                sample or f"{len(shopping)} saker kvar på listan.",
                "🛒",
                "shopping",
                18,
            )

        current_weather = (weather or {}).get("current") or {}
        precipitation = current_weather.get("precipitation")
        temperature = current_weather.get("temperature") or current_weather.get("temperature_2m")
        if precipitation not in (None, "", 0, 0.0, "0"):
            add(
                "weather-rain-compass",
                "Regngrej vid dörren",
                f"Nederbörd syns i vädret ({precipitation} mm).",
                "🌧️",
                "more",
                15,
            )
        elif temperature not in (None, "") and (now.hour < 10 or now.hour >= 16):
            add(
                "weather-clothes-compass",
                "Kläder efter väder",
                f"Just nu cirka {temperature} °C — rätt jacka nära dörren?",
                "🧥",
                "more",
                25,
            )

        people_home = [row for row in (presence or []) if row.get("present")]
        if self._allowed(identity, "family") and len(people_home) >= 2:
            names = ", ".join(
                str(row.get("name") or row.get("owner") or "någon")
                for row in people_home[:3]
            )
            add(
                "family-touchpoint",
                "30 sekunders familjekoll",
                f"Hemma: {names}. Fråga om någon behöver hjälp med nästa steg.",
                "👨‍👩‍👧‍👦",
                "family",
                30,
            )

        if not actions:
            add(
                "clear-one-surface",
                "Gör en yta 10 % bättre",
                "Välj bord, diskbänk eller hall och förbättra den i två minuter.",
                "🧽",
                "home",
                50,
            )

        actions.sort(key=lambda row: (int(row.get("weight") or 50), str(row.get("id") or "")))
        summary = []
        if reminders:
            summary.append(f"{len(reminders)} påminnelse(r)")
        if shopping:
            summary.append(f"{len(shopping)} inköp")
        if assigned:
            summary.append(f"{len(assigned)} egna uppgifter")
        if people_home:
            summary.append(f"{len(people_home)} hemma")
        return {
            "ok": True,
            "mode": self._mode(now.hour),
            "summary": " · ".join(summary) if summary else "Lugnt läge — välj bara ett litet nästa steg.",
            "actions": actions[:4],
            "updated_at": now.isoformat(),
        }
