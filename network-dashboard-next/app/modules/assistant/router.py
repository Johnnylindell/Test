from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.auth.dependencies import require_login, require_same_origin
from app.auth.service import Identity
from app.integrations.speech_transcription import SpeechTranscriptionBusyError
from app.modules.assistant.schemas import AssistantConfirmation
from app.modules.assistant.service import AssistantService

router = APIRouter(prefix="/api/v2/assistant", tags=["assistant"])
_AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
}


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


@router.get("/transcription/status")
def transcription_status(
    request: Request,
    _: Identity = Depends(require_login),
) -> dict:
    return request.app.state.speech_transcription.status()


@router.post("/transcribe", dependencies=[Depends(require_same_origin)])
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    _: Identity = Depends(require_login),
) -> dict:
    adapter = request.app.state.speech_transcription
    content_type = str(file.content_type or "").split(";", 1)[0].strip().casefold()
    suffix = _AUDIO_TYPES.get(content_type)
    if suffix is None:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Ljudformatet stöds inte",
        )
    audio = await file.read(adapter.max_bytes + 1)
    await file.close()
    if not audio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ljudfilen är tom")
    if len(audio) > adapter.max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Ljudfilen är för stor")
    try:
        return adapter.transcribe(audio, suffix=suffix, language="sv")
    except SpeechTranscriptionBusyError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


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
