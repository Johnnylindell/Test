from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database.database import Database
from app.modules.budget.repository import BudgetRepository
from app.modules.notifications.repository import NotificationsRepository, now_iso


class _SafeValues(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class SmartNotificationEvaluator:
    def __init__(self, database: Database, repository: NotificationsRepository) -> None:
        self.database = database
        self.repository = repository

    @staticmethod
    def _parse(value: Any) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    def _candidates(self, now: datetime) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if self.database.table_exists("home_reminders"):
            for reminder in self.database.fetch_all(
                "SELECT id,title,owner,remind_at,note FROM home_reminders WHERE done=0"
            ):
                due = self._parse(reminder.get("remind_at"))
                if not due:
                    continue
                minutes = round((due - now).total_seconds() / 60)
                if -10 <= minutes <= 20:
                    when = "nu" if minutes <= 0 else f"om {minutes} min"
                    rows.append({
                        "event": "smart_calendar_soon",
                        "target": reminder.get("owner") or "all",
                        "title": reminder.get("title") or "Påminnelse",
                        "message": f"{reminder.get('title') or 'Påminnelse'} {when}",
                        "when": when,
                        "source_id": reminder.get("id"),
                    })
        if self.database.table_exists("recurring_routine_instances"):
            due_rows = self.database.fetch_all(
                "SELECT id,title,scheduled_for FROM recurring_routine_instances "
                "WHERE done=0 AND COALESCE(scheduled_for,'')<>''"
            )
            overdue = [row for row in due_rows if (self._parse(row.get("scheduled_for")) or now) <= now]
            if overdue:
                rows.append({
                    "event": "routine_due",
                    "target": "all",
                    "count": len(overdue),
                    "title": "Återkommande rutiner",
                    "message": f"{len(overdue)} rutin(er) är dags nu",
                })
        if self.database.table_exists("weekly_meals"):
            days = {(now + timedelta(days=offset)).date().isoformat() for offset in (0, 1)}
            meals = self.database.fetch_all(
                "SELECT week_start,day,title FROM weekly_meals WHERE TRIM(COALESCE(title,''))<>''"
            )
            planned = {str(row.get("day") or "")[:10] for row in meals}
            missing = sorted(days - planned)
            if missing:
                rows.append({
                    "event": "smart_meal_plan_missing",
                    "target": "all",
                    "days": ", ".join(missing),
                    "title": "Matplan saknas",
                    "message": "Matplan saknas för " + ", ".join(missing),
                })
        if self.database.table_exists("inventory_shopping_suggestions"):
            count = int(self.database.fetch_value(
                "SELECT COUNT(*) FROM inventory_shopping_suggestions "
                "WHERE COALESCE(dismissed_at,'')=''"
            ) or 0)
            if count >= 3:
                rows.append({
                    "event": "smart_shopping_suggestions",
                    "target": "all",
                    "count": count,
                    "title": "Smarta inköpsförslag",
                    "message": f"Det finns {count} smarta inköpsförslag att lägga till",
                })
        history = self.database.get_json_state("internet_history", [])
        latest = history[0] if isinstance(history, list) and history and isinstance(history[0], dict) else {}
        if latest and latest.get("ok") is False:
            rows.append({
                "event": "internet_down",
                "target": "all",
                "title": "Internet är nere",
                "message": "Internetkontrollen misslyckades.",
            })
        if self.database.table_exists("budget_sheets") and self.database.table_exists("budget_cells"):
            try:
                view = BudgetRepository(self.database).overview()
                for expense in view.get("expenses", []):
                    difference = float(expense.get("actual") or 0) - float(expense.get("budgeted") or 0)
                    if float(expense.get("budgeted") or 0) > 0 and difference > 0.5:
                        rows.append({
                            "event": "budget_over",
                            "target": "all",
                            "category": expense.get("category") or "Kategori",
                            "difference": round(difference, 2),
                            "title": "Budgetöverskridande",
                            "message": f"{expense.get('category')} är {difference:.2f} € över budget.",
                        })
            except RuntimeError:
                pass
        return rows

    def _recent(self, rule_id: str, message: str, cooldown_minutes: int, now: datetime) -> bool:
        cutoff = now - timedelta(minutes=max(0, cooldown_minutes))
        raw = self.database.get_json_state("alerts", [])
        for alert in raw if isinstance(raw, list) else []:
            if not isinstance(alert, dict):
                continue
            metadata = alert.get("metadata") if isinstance(alert.get("metadata"), dict) else {}
            if str(metadata.get("rule_id") or "") != rule_id or str(alert.get("message") or "") != message:
                continue
            created = self._parse(alert.get("created_at"))
            if created and created >= cutoff:
                return True
        return False

    def evaluate(self, *, trigger: str = "manual") -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        if trigger == "auto":
            last = self._parse(self.database.get_json_state("smart_alert_last_checked", ""))
            if last and (now - last).total_seconds() < 120:
                return {
                    "ok": True,
                    "trigger": trigger,
                    "created": [],
                    "created_count": 0,
                    "suggestions": [],
                    "checked_at": last.isoformat(),
                    "skipped": "cooldown",
                }
        self.database.set_json_state("smart_alert_last_checked", now.isoformat())
        rules = self.repository.rules()
        created: list[dict[str, Any]] = []
        candidates = self._candidates(now)
        for candidate in candidates:
            matching = [
                rule for rule in rules
                if rule.get("enabled", True)
                and str(rule.get("event") or rule.get("type") or "") == candidate["event"]
            ]
            for rule in matching:
                target = str(rule.get("target") or candidate.get("target") or "all")
                values = _SafeValues({key: str(value) for key, value in candidate.items()})
                template = str(rule.get("template") or rule.get("message_template") or "")
                message = template.format_map(values) if template else str(candidate["message"])
                cooldown = int(rule.get("cooldown_minutes") or 0)
                rule_id = str(rule.get("id") or candidate["event"])
                if self._recent(rule_id, message, cooldown, now):
                    continue
                alert = {
                    "id": secrets.token_urlsafe(12),
                    "type": candidate["event"],
                    "message": message[:500],
                    "target": target[:80],
                    "severity": str(rule.get("severity") or "normal")[:30],
                    "metadata": {
                        "rule_id": rule_id[:120],
                        "trigger": trigger,
                        "source_id": candidate.get("source_id"),
                    },
                    "created_at": now_iso(),
                    "acknowledged_at": None,
                    "created_by": "smart-check",
                }
                created.append(self.repository.create_alert(alert))
        return {
            "ok": True,
            "trigger": trigger,
            "created": created,
            "created_count": len(created),
            "suggestions": candidates,
            "checked_at": now.isoformat(),
        }
