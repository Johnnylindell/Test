from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity
from app.modules.operations.schemas import (
    AgentCommandCreate,
    AgentCommandResult,
    AgentCreate,
    AgentHeartbeat,
    BaselineCreate,
    ManagedServiceCreate,
    ServiceAction,
)
from app.modules.operations.service import OperationsService

router = APIRouter(prefix="/api/v2/operations", tags=["operations"])


def service(request: Request) -> OperationsService:
    return OperationsService(request.app.state.database)


def _require_external(request: Request) -> None:
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Externa driftåtgärder är avstängda")


def _agent(
    authorization: str,
    operations: OperationsService,
) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agenttoken krävs")
    agent = operations.authenticate_agent(token)
    if not agent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ogiltig agenttoken")
    return agent


@router.get("/overview")
def overview(
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    return operations.overview()


@router.post("/services", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def add_service(
    payload: ManagedServiceCreate,
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    try:
        service_id = operations.add_service(payload.label, payload.unit_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "id": service_id, "services": operations.managed_services(live=True)}


@router.delete("/services/{service_id}", dependencies=[Depends(require_same_origin)])
def remove_service(
    service_id: str,
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    if not operations.remove_service(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicen hittades inte")
    return {"ok": True}


@router.post("/services/{service_id}/action", dependencies=[Depends(require_same_origin)])
def service_action(
    service_id: str,
    payload: ServiceAction,
    request: Request,
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    _require_external(request)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Serviceåtgärden måste bekräftas")
    try:
        result = operations.service_action(service_id, payload.action)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.get("error") or "Serviceåtgärden misslyckades")
    return result


@router.post("/agents", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_agent(
    payload: AgentCreate,
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    return {"ok": True, "agent": operations.create_agent(payload.name)}


@router.delete("/agents/{agent_id}", dependencies=[Depends(require_same_origin)])
def delete_agent(
    agent_id: str,
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    if not operations.delete_agent(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agenten hittades inte")
    return {"ok": True}


@router.post("/agents/{agent_id}/commands", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def queue_command(
    agent_id: str,
    payload: AgentCommandCreate,
    request: Request,
    identity: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    _require_external(request)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agentkommandot måste bekräftas")
    try:
        command_id = operations.queue_command(
            agent_id,
            payload.command_type,
            payload.payload,
            identity.user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "id": command_id}


@router.post("/baselines", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_same_origin)])
def create_baseline(
    payload: BaselineCreate,
    identity: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    baseline_id = operations.create_baseline(payload.label, identity.user)
    return {"ok": True, "id": baseline_id, "baselines": operations.baselines()}


@router.get("/baselines/{baseline_id}/compare")
def compare_baseline(
    baseline_id: str,
    _: Identity = Depends(require_admin),
    operations: OperationsService = Depends(service),
) -> dict:
    try:
        return operations.compare_baseline(baseline_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/agent/heartbeat")
def agent_heartbeat(
    payload: AgentHeartbeat,
    authorization: str = Header(default=""),
    operations: OperationsService = Depends(service),
) -> dict:
    agent = _agent(authorization, operations)
    return operations.heartbeat(str(agent["id"]), payload.status)


@router.get("/agent/commands")
def agent_commands(
    authorization: str = Header(default=""),
    operations: OperationsService = Depends(service),
) -> dict:
    agent = _agent(authorization, operations)
    return {"ok": True, "commands": operations.claim_commands(str(agent["id"]))}


@router.post("/agent/commands/{command_id}/result")
def agent_command_result(
    command_id: str,
    payload: AgentCommandResult,
    authorization: str = Header(default=""),
    operations: OperationsService = Depends(service),
) -> dict:
    agent = _agent(authorization, operations)
    if not operations.complete_command(
        str(agent["id"]),
        command_id,
        payload.status,
        payload.result,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kommandot hittades inte")
    return {"ok": True}
