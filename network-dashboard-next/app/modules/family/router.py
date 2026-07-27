from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import current_identity, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository
from app.modules.family.schemas import AddFamilyListItem, CompleteFamilyListItem
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


@router.post("/list-items", dependencies=[Depends(require_same_origin)])
def add_family_list_item(
    command: AddFamilyListItem,
    identity: Identity = Depends(require_login),
    service: FamilyService = Depends(get_service),
) -> dict:
    return service.add_item(identity, command)


@router.patch("/list-items/{item_id}", dependencies=[Depends(require_same_origin)])
def complete_family_list_item(
    item_id: str,
    command: CompleteFamilyListItem,
    _: Identity = Depends(require_login),
    service: FamilyService = Depends(get_service),
) -> dict:
    return service.set_item_done(item_id, command.done)
