from __future__ import annotations

from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository
from app.modules.planning.repository import PlanningRepository


class HomeService:
    def __init__(
        self,
        family_repository: FamilyRepository,
        planning_repository: PlanningRepository,
    ) -> None:
        self.family_repository = family_repository
        self.planning_repository = planning_repository

    def summary(self, identity: Identity) -> dict:
        lists = self.family_repository.lists()
        reminders = self.planning_repository.reminders(limit=20)
        routine_instances = self.planning_repository.routine_instances(limit=20)
        checklist_items = self.planning_repository.checklist_items()
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "family": {
                "profiles": self.family_repository.profiles(),
                "open_list_items": sum(row["open_count"] for row in lists),
            },
            "planning": {
                "reminders": reminders,
                "routine_instances": routine_instances,
                "checklist_items": checklist_items,
            },
            "totals": {
                "open_reminders": sum(not row["done"] for row in reminders),
                "open_routines": sum(not row["done"] for row in routine_instances),
                "open_checklist_items": sum(not row["done"] for row in checklist_items),
            },
        }
