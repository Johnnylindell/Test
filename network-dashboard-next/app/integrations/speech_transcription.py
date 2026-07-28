from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from threading import Lock, RLock
from typing import Any


class SpeechTranscriptionBusyError(RuntimeError):
    """Raised when the single local transcription worker is already occupied."""


class SpeechTranscriptionAdapter:
    def __init__(
        self,
        *,
        enabled: bool,
        model: str,
        device: str = "cpu",
        compute_type: str = "int8",
        max_bytes: int = 8 * 1024 * 1024,
        allow_model_download: bool = False,
    ) -> None:
        self.enabled = bool(enabled)
        self.model = str(model or "").strip()
        self.device = str(device or "cpu").strip()[:40] or "cpu"
        self.compute_type = str(compute_type or "int8").strip()[:40] or "int8"
        self.max_bytes = max(64 * 1024, min(int(max_bytes), 50 * 1024 * 1024))
        self.allow_model_download = bool(allow_model_download)
        self._model_instance: Any = None
        self._model_lock = RLock()
        self._worker_lock = Lock()

    def _model_path(self) -> Path | None:
        if not self.model:
            return None
        candidate = Path(self.model).expanduser()
        return candidate.resolve() if candidate.is_dir() else None

    def status(self) -> dict[str, Any]:
        dependency_installed = importlib.util.find_spec("faster_whisper") is not None
        model_path = self._model_path()
        configured = bool(self.enabled and self.model)
        local_model = model_path is not None
        available = bool(
            configured
            and dependency_installed
            and (local_model or self.allow_model_download)
        )
        if not self.enabled:
            state = "disabled"
            message = "Servertranskribering är inte aktiverad"
        elif not self.model:
            state = "model_not_configured"
            message = "Ingen lokal Whisper-modell är konfigurerad"
        elif not dependency_installed:
            state = "dependency_missing"
            message = "Det valfria paketet faster-whisper är inte installerat"
        elif not local_model and not self.allow_model_download:
            state = "model_not_local"
            message = "Modellen måste finnas lokalt när modellhämtning är avstängd"
        else:
            state = "ready"
            message = "Lokal servertranskribering är redo"
        return {
            "ok": available,
            "configured": configured,
            "available": available,
            "state": state,
            "message": message,
            "backend": "faster-whisper",
            "model": model_path.name if model_path else self.model[:100],
            "model_local": local_model,
            "model_download_allowed": self.allow_model_download,
            "dependency_installed": dependency_installed,
            "device": self.device,
            "compute_type": self.compute_type,
            "max_bytes": self.max_bytes,
            "audio_persisted": False,
            "external_transcription_service_used": False,
            "sensitive_values_exposed": False,
        }

    def _load_model(self) -> Any:
        status = self.status()
        if not status["available"]:
            raise RuntimeError(status["message"])
        with self._model_lock:
            if self._model_instance is not None:
                return self._model_instance
            from faster_whisper import WhisperModel

            source = str(self._model_path() or self.model)
            self._model_instance = WhisperModel(
                source,
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=not self.allow_model_download,
            )
            return self._model_instance

    def transcribe(self, audio: bytes, *, suffix: str, language: str = "sv") -> dict[str, Any]:
        if not audio:
            raise ValueError("Ljudfilen är tom")
        if len(audio) > self.max_bytes:
            raise ValueError("Ljudfilen är för stor")
        if not self._worker_lock.acquire(blocking=False):
            raise SpeechTranscriptionBusyError("Transkriberaren arbetar redan med en annan inspelning")

        temporary_path: Path | None = None
        try:
            model = self._load_model()
            with tempfile.NamedTemporaryFile(prefix="lindells-voice-", suffix=suffix, delete=False) as handle:
                handle.write(audio)
                handle.flush()
                temporary_path = Path(handle.name)

            segments, info = model.transcribe(
                str(temporary_path),
                language=language or "sv",
                beam_size=1,
                vad_filter=True,
            )
            parts: list[str] = []
            for segment in segments:
                text = str(getattr(segment, "text", "") or "").strip()
                if text:
                    parts.append(text)
                if sum(len(part) for part in parts) > 750:
                    break
            full_text = " ".join(parts).strip()
            if not full_text:
                raise ValueError("Ingen talad text kunde identifieras")
            truncated = len(full_text) > 500
            return {
                "ok": True,
                "text": full_text[:500],
                "truncated": truncated,
                "language": str(getattr(info, "language", language) or language)[:20],
                "duration_seconds": round(float(getattr(info, "duration", 0.0) or 0.0), 2),
                "backend": "faster-whisper",
                "audio_persisted": False,
                "external_transcription_service_used": False,
                "sensitive_values_exposed": False,
            }
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            self._worker_lock.release()
