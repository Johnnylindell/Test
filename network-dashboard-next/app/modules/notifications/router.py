from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_login, require_same_origin
from app.auth.service import Identity
from app.modules.notifications.evaluator import SmartNotificationEvaluator
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.schemas import (
    AlertCreate,
    NotificationDeliveryRequest,
    NotificationRulesUpdate,
    PushSubscriptionRequest,
)
from app.modules.notifications.service import NotificationsService

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])


def repository(request: Request) -> NotificationsRepository:
    return NotificationsRepository(request.app.state.database)


def service(repo: NotificationsRepository = Depends(repository)) -> NotificationsService:
    return NotificationsService(repo)


def evaluator(request: Request, repo: NotificationsRepository = Depends(repository)) -> SmartNotificationEvaluator:
    return SmartNotificationEvaluator(request.app.state.database, repo)


@router.get("/overview")
def overview(
    identity: Identity = Depends(require_login),
    notifications: NotificationsService = Depends(service),
) -> dict:
    return notifications.overview(identity)


@router.get("/public-key")
def public_key(
    repo: NotificationsRepository = Depends(repository),
    _: Identity = Depends(require_login),
) -> dict:
    return {"ok": True, "public_key": repo.public_push_key()}


@router.get("/rules")
def rules(
    repo: NotificationsRepository = Depends(repository),
    _: Identity = Depends(require_admin),
) -> dict:
    return {"ok": True, "rules": repo.rules()}


@router.put("/rules", dependencies=[Depends(require_same_origin)])
def update_rules(
    payload: NotificationRulesUpdate,
    repo: NotificationsRepository = Depends(repository),
    _: Identity = Depends(require_admin),
) -> dict:
    repo.save_rules([row.model_dump() for row in payload.rules])
    return {"ok": True, "rules": repo.rules()}


@router.post("/checks", dependencies=[Depends(require_same_origin)])
def run_checks(
    request: Request,
    checks: SmartNotificationEvaluator = Depends(evaluator),
    _: Identity = Depends(require_admin),
) -> dict:
    result = checks.evaluate(trigger="manual")
    if request.app.state.settings.external_side_effects:
        for alert in result.get("created", []):
            request.app.state.notification_delivery.deliver(
                title="Lindells app",
                message=str(alert.get("message") or ""),
                target=str(alert.get("target") or "all"),
                severity=str(alert.get("severity") or "normal"),
                send_push=True,
                send_discord=False,
            )
    return result


@router.get("/diagnostics")
def diagnostics(
    request: Request,
    repo: NotificationsRepository = Depends(repository),
    _: Identity = Depends(require_admin),
) -> dict:
    return {
        "ok": True,
        **repo.diagnostics(),
        "external_side_effects": request.app.state.settings.external_side_effects,
    }


@router.post("/deliver", dependencies=[Depends(require_same_origin)])
def deliver(
    payload: NotificationDeliveryRequest,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    if not request.app.state.settings.external_side_effects:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Externa sidoeffekter är avstängda")
    return request.app.state.notification_delivery.deliver(**payload.model_dump())


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
