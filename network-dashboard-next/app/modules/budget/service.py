from __future__ import annotations

from fastapi import HTTPException, status

from app.auth.service import Identity
from app.modules.budget.repository import BudgetRepository


class BudgetService:
    def __init__(self, repository: BudgetRepository) -> None:
        self.repository = repository

    @staticmethod
    def require_adult(identity: Identity) -> None:
        if identity.user not in {"johnny", "kristina", "admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budgeten är endast tillgänglig för vuxna")

    def overview(self, identity: Identity, sheet: str = "") -> dict:
        self.require_adult(identity)
        return {
            "ok": True,
            "identity": {"user": identity.user, "admin": identity.admin},
            "budget": self.repository.overview(sheet),
            "bank_integration": {"included": False, "reason": "Bankkopplingar hanteras i separat integrationsmodul"},
        }
