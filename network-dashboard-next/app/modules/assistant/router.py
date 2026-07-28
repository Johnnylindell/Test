from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.modules.assistant.schemas import AssistantConfirmation
from app.modules.assistant.service import AssistantService

router = APIRouter(prefix="/api/v2/assistant", tags=["assistant"])


def service(request: Request) -> AssistantService:
    try:
        return AssistantService(
            request.app.state.database,
            request.app.state.settings.assistant_signing_secret,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/query")
def query(
    q: str = Query(min_length=2, max_length=500),
    identity: Identity = Depends(require_login),
    assistant: AssistantService = Depends(service),
) -> dict:
    return assistant.query(q, identity)


@router.post("/confirm", dependencies=[Depends(require_same_origin)])
def confirm(
    payload: AssistantConfirmation,
    identity: Identity = Depends(require_login),
    assistant: AssistantService = Depends(service),
) -> dict:
    try:
        return assistant.confirm(payload.token, identity)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
