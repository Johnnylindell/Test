from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.planning.repository import PlanningRepository
from app.modules.planning.schemas import CompletionUpdate, ReminderCreate, ReminderUpdate, RoutineRuleCreate, RoutineRuleUpdate
from app.modules.planning.service import PlanningService

router = APIRouter(prefix="/api/v2/planning", tags=["planning"])


def get_repository(request: Request) -> PlanningRepository:
    return PlanningRepository(request.app.state.database)


def get_service(repo: PlanningRepository = Depends(get_repository)) -> PlanningService:
    return PlanningService(repo)


@router.get("/overview")
def planning_overview(identity: Identity = Depends(require_login), service: PlanningService = Depends(get_service)) -> dict:
    return service.overview(identity)


@router.post("/reminders", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_reminder(payload: ReminderCreate, identity: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    return {"ok": True, "id": repo.add_reminder(payload.model_dump(), identity.user)}


@router.patch("/reminders/{reminder_id}", dependencies=[Depends(require_same_origin)])
def update_reminder(reminder_id: str, payload: ReminderUpdate, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    try:
        repo.update_reminder(reminder_id, payload.model_dump(exclude_unset=True))
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/reminders/{reminder_id}", dependencies=[Depends(require_same_origin)])
def delete_reminder(reminder_id: str, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    try:
        repo.delete_reminder(reminder_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/routines", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_routine(payload: RoutineRuleCreate, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    return {"ok": True, "id": repo.add_routine_rule(payload.model_dump())}


@router.patch("/routines/{rule_id}", dependencies=[Depends(require_same_origin)])
def update_routine(rule_id: str, payload: RoutineRuleUpdate, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    try:
        repo.update_routine_rule(rule_id, payload.model_dump(exclude_unset=True))
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/routines/{rule_id}", dependencies=[Depends(require_same_origin)])
def delete_routine(rule_id: str, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    try:
        repo.delete_routine_rule(rule_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/routine-instances/{instance_id}", dependencies=[Depends(require_same_origin)])
def complete_instance(instance_id: str, payload: CompletionUpdate, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    try:
        repo.set_instance_done(instance_id, payload.done)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/checklist-items/{item_id}", dependencies=[Depends(require_same_origin)])
def complete_checklist(item_id: str, payload: CompletionUpdate, _: Identity = Depends(require_login), repo: PlanningRepository = Depends(get_repository)) -> dict:
    try:
        repo.set_checklist_done(item_id, payload.done)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
