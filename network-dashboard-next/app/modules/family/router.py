from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.family.repository import FamilyRepository
from app.modules.family.schemas import AddFamilyListItem, CompleteFamilyListItem, DayMessageUpdate, FamilyNoteCreate
from app.modules.family.service import FamilyService

router = APIRouter(prefix="/api/v2/family", tags=["family"])


def get_repository(request: Request) -> FamilyRepository:
    return FamilyRepository(request.app.state.database)


def get_service(repo: FamilyRepository = Depends(get_repository)) -> FamilyService:
    return FamilyService(repo)


@router.get("/overview")
def family_overview(identity: Identity = Depends(require_login), service: FamilyService = Depends(get_service)) -> dict:
    return service.overview(identity)


@router.post("/list-items", dependencies=[Depends(require_same_origin)])
def add_family_list_item(command: AddFamilyListItem, identity: Identity = Depends(require_login), service: FamilyService = Depends(get_service)) -> dict:
    return service.add_item(identity, command)


@router.patch("/list-items/{item_id}", dependencies=[Depends(require_same_origin)])
def complete_family_list_item(item_id: str, command: CompleteFamilyListItem, _: Identity = Depends(require_login), service: FamilyService = Depends(get_service)) -> dict:
    return service.set_item_done(item_id, command.done)


@router.post("/notes", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_note(payload: FamilyNoteCreate, identity: Identity = Depends(require_login), repo: FamilyRepository = Depends(get_repository)) -> dict:
    owner = payload.owner.strip() or identity.user
    return {"ok": True, "id": repo.add_note(payload.text, owner)}


@router.delete("/notes/{note_id}", dependencies=[Depends(require_same_origin)])
def delete_note(note_id: str, _: Identity = Depends(require_login), repo: FamilyRepository = Depends(get_repository)) -> dict:
    try:
        repo.delete_note(note_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/day-message", dependencies=[Depends(require_same_origin)])
def set_day_message(payload: DayMessageUpdate, identity: Identity = Depends(require_login), repo: FamilyRepository = Depends(get_repository)) -> dict:
    repo.set_day_message(payload.message, identity.user)
    return {"ok": True, "message": repo.day_message()}
