from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import current_identity
from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository
from app.modules.home.service import HomeService
from app.modules.planning.repository import PlanningRepository

router = APIRouter(prefix="/api/v2/home", tags=["home"])


def get_service(request: Request) -> HomeService:
    database = request.app.state.database
    return HomeService(
        FamilyRepository(database),
        PlanningRepository(database),
    )


@router.get("/summary")
def home_summary(
    request: Request,
    identity: Identity = Depends(current_identity),
    service: HomeService = Depends(get_service),
) -> dict:
    summary = service.summary(identity)
    summary["runtime"] = {
        "read_only": bool(request.app.state.settings.read_only),
        "external_side_effects": bool(request.app.state.settings.external_side_effects),
        "database_isolated": request.app.state.settings.database_path.name != "family_budget.sqlite3",
    }
    return summary
