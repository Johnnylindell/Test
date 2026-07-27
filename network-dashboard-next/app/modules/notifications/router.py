from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.schemas import AlertCreate, PushSubscriptionRequest
from app.modules.notifications.service import NotificationsService

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])


def repository(request: Request) -> NotificationsRepository:
    return NotificationsRepository(request.app.state.database)


def service(repo: NotificationsRepository = Depends(repository)) -> NotificationsService:
    return NotificationsService(repo)


@router.get("/overview")
def overview(
    identity: Identity = Depends(require_login),
    notifications: NotificationsService = Depends(service),
) -> dict:
    return notifications.overview(identity)


@router.post("/subscriptions", dependencies=[Depends(require_same_origin)])
def subscribe(
    payload: PushSubscriptionRequest,
    identity: Identity = Depends(require_login),
    notifications: NotificationsService = Depends(service),
) -> dict:
    return notifications.subscribe(identity, payload.subscription.model_dump(mode="json"))


@router.delete("/subscriptions", dependencies=[Depends(require_same_origin)])
def unsubscribe(
    endpoint: str,
    _: Identity = Depends(require_login),
    repo: NotificationsRepository = Depends(repository),
) -> dict:
    repo.delete_subscription(endpoint)
    return {"ok": True}


@router.post("/alerts", dependencies=[Depends(require_same_origin)])
def create_alert(
    payload: AlertCreate,
    identity: Identity = Depends(require_admin),
    notifications: NotificationsService = Depends(service),
) -> dict:
    return notifications.create_alert(identity, payload.model_dump())


@router.post("/alerts/{alert_id}/ack", dependencies=[Depends(require_same_origin)])
def acknowledge(
    alert_id: str,
    _: Identity = Depends(require_login),
    repo: NotificationsRepository = Depends(repository),
) -> dict:
    alert = repo.acknowledge(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aviseringen hittades inte")
    return {"ok": True, "alert": alert}
