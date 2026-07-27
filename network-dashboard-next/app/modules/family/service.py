from __future__ import annotations

from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository


class FamilyService:
    def __init__(self, repository: FamilyRepository) -> None:
        self.repository = repository

    def overview(self, identity: Identity) -> dict:
        lists = self.repository.lists()
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "profiles": self.repository.profiles(),
            "lists": lists,
            "notes": self.repository.notes(),
            "totals": {
                "lists": len(lists),
                "open_items": sum(item["open_count"] for item in lists),
            },
        }
