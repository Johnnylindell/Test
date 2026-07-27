from __future__ import annotations

from app.auth.service import Identity
from app.modules.planning.repository import PlanningRepository


class PlanningService:
    def __init__(self, repository: PlanningRepository) -> None:
        self.repository = repository

    def overview(self, identity: Identity) -> dict:
        reminders = self.repository.reminders()
        routines = self.repository.routine_rules()
        instances = self.repository.routine_instances()
        checklist_items = self.repository.checklist_items()
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "reminders": reminders,
            "routine_rules": routines,
            "routine_instances": instances,
            "checklist_items": checklist_items,
            "totals": {
                "open_reminders": sum(not row["done"] for row in reminders),
                "active_routines": sum(row["active"] for row in routines),
                "open_routine_instances": sum(not row["done"] for row in instances),
                "open_checklist_items": sum(not row["done"] for row in checklist_items),
            },
        }
