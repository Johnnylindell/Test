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
    identity: Identity = Depends(current_identity),
    service: HomeService = Depends(get_service),
) -> dict:
    return service.summary(identity)
