from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import current_identity
from app.auth.service import Identity
from app.modules.planning.repository import PlanningRepository
from app.modules.planning.service import PlanningService

router = APIRouter(prefix="/api/v2/planning", tags=["planning"])


def get_service(request: Request) -> PlanningService:
    return PlanningService(PlanningRepository(request.app.state.database))


@router.get("/overview")
def planning_overview(
    identity: Identity = Depends(current_identity),
    service: PlanningService = Depends(get_service),
) -> dict:
    return service.overview(identity)
