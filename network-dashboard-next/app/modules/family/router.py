from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import current_identity
from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository
from app.modules.family.service import FamilyService

router = APIRouter(prefix="/api/v2/family", tags=["family"])


def get_service(request: Request) -> FamilyService:
    return FamilyService(FamilyRepository(request.app.state.database))


@router.get("/overview")
def family_overview(
    identity: Identity = Depends(current_identity),
    service: FamilyService = Depends(get_service),
) -> dict:
    return service.overview(identity)
