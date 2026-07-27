from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.experience.compass import HomeCompassService
from app.modules.experience.schemas import ForgetItemCreate, ForgetItemUpdate, QuestCompletion
from app.modules.experience.service import ExperienceService
from app.modules.presence.service import PresenceService

router = APIRouter(prefix="/api/v2/experience", tags=["experience"])


def service(request: Request) -> ExperienceService:
    return ExperienceService(request.app.state.database)


@router.get("/overview")
def overview(identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    return experience.overview(identity)


@router.get("/my-dashboard")
def my_dashboard(identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    return experience.personal_dashboard(identity)


@router.get("/compass")
def compass(request: Request, identity: Identity = Depends(require_login)) -> dict:
    forecast = request.app.state.weather.forecast()
    current = forecast.get("current") if isinstance(forecast, dict) else {}
    normalized_weather = {
        "current": {
            "temperature": (current or {}).get("temperature_c"),
            "precipitation": (current or {}).get("precip_mm"),
        }
    }
    presence: list[dict] = []
    secret = str(request.app.state.settings.presence_hash_secret or "")
    if secret and request.app.state.database.table_exists("presence_devices"):
        try:
            presence = PresenceService(request.app.state.database, secret).overview().get("people", [])
        except Exception:
            # Home Compass remains available even when the optional presence module
            # has incomplete data during migration or first startup.
            presence = []
    return HomeCompassService(request.app.state.database).overview(
        identity,
        weather=normalized_weather,
        presence=presence,
    )


@router.get("/search")
def search(q: str, identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    return experience.search(q, identity)


@router.get("/forget-items")
def forget_items(identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    return {"ok": True, "items": experience.forget_items(identity.user)}


@router.post("/forget-items", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_forget_item(payload: ForgetItemCreate, identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    return {"ok": True, "id": experience.add_forget_item(payload.model_dump(), identity.user)}


@router.patch("/forget-items/{item_id}", dependencies=[Depends(require_same_origin)])
def update_forget_item(item_id: str, payload: ForgetItemUpdate, _: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    try:
        experience.update_forget_item(item_id, payload.model_dump(exclude_unset=True))
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/forget-items/{item_id}", dependencies=[Depends(require_same_origin)])
def delete_forget_item(item_id: str, _: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    try:
        experience.delete_forget_item(item_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/quests")
def quests(identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    return experience.quests(identity)


@router.put("/quests/{quest_id}", dependencies=[Depends(require_same_origin)])
def set_quest(quest_id: str, payload: QuestCompletion, identity: Identity = Depends(require_login), experience: ExperienceService = Depends(service)) -> dict:
    experience.set_quest_done(quest_id, identity.user, payload.done)
    return {"ok": True, "quests": experience.quests(identity)["quests"]}
