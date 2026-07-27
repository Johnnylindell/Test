from __future__ import annotations

from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository
from app.modules.family.schemas import AddFamilyListItem


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
            "day_message": self.repository.day_message(),
            "totals": {
                "lists": len(lists),
                "open_items": sum(item["open_count"] for item in lists),
            },
        }

    def add_item(self, identity: Identity, command: AddFamilyListItem) -> dict:
        owner = command.owner.strip() or identity.user
        item_id = self.repository.add_list_item(command.list_id, command.text.strip(), owner)
        return {"ok": True, "item_id": item_id, "list_id": command.list_id}

    def set_item_done(self, item_id: str, done: bool) -> dict:
        self.repository.set_item_done(item_id, done)
        return {"ok": True, "item_id": item_id, "done": done}
