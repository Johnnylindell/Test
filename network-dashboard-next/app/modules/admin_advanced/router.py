from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity
from app.database.migrations import discover

router = APIRouter(prefix="/api/v2/admin/advanced", tags=["admin-advanced"])
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ConfirmAction(BaseModel):
    confirm: bool = False


class BreakerResetRequest(BaseModel):
    key: str = Field(default="", max_length=100, pattern=r"^[A-Za-z0-9_.:-]*$")
    confirm: bool = False


def _display_path(path: Path) -> str:
    resolved = Path(path).expanduser()
    home = Path.home()
    try:
        return "~/" + str(resolved.relative_to(home))
    except ValueError:
        return resolved.name


def _parity() -> dict[str, Any]:
    path = _PROJECT_ROOT / "docs" / "parity.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        domains = list(payload.get("domains") or []) if isinstance(payload, dict) else []
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "error": str(exc)[:240],
            "domains": [],
            "summary": {"complete": 0, "partial": 0, "missing": 0, "total": 0},
            "gaps": [],
        }
    summary = {
        "complete": sum(row.get("status") == "complete" for row in domains),
        "partial": sum(row.get("status") == "partial" for row in domains),
        "missing": sum(row.get("status") == "missing" for row in domains),
        "total": len(domains),
    }
    gaps = [
        {
            "id": str(row.get("id") or "")[:80],
            "status": str(row.get("status") or "")[:40],
            "missing": [str(item)[:160] for item in list(row.get("missing") or [])[:30]],
        }
        for row in domains
        if row.get("status") != "complete" or row.get("missing")
    ]
    return {"ok": True, "domains": domains, "summary": summary, "gaps": gaps}


def _migrations(request: Request) -> dict[str, Any]:
    try:
        discovered = discover(_PROJECT_ROOT / "migrations")
        with sqlite3.connect(request.app.state.database.path, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            journal_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            applied = {
                row["version"]: dict(row)
                for row in connection.execute("SELECT * FROM schema_migrations")
            } if journal_exists else {}
        rows = []
        for migration in discovered:
            saved = applied.get(migration.version)
            rows.append({
                "version": migration.version,
                "name": migration.name,
                "status": saved.get("status") if saved else "pending",
                "checksum_match": not saved or saved.get("checksum") == migration.checksum,
                "applied_at": saved.get("applied_at") if saved else None,
            })
        pending = sum(row["status"] != "applied" for row in rows)
        checksum_errors = sum(not bool(row.get("checksum_match")) for row in rows)
        failed = sum(row.get("status") == "failed" for row in rows)
        return {
            "ok": pending == 0 and checksum_errors == 0 and failed == 0,
            "pending": pending,
            "checksum_errors": checksum_errors,
            "failed": failed,
            "migrations": rows,
        }
    except Exception as exc:
        return {
            "ok": False,
            "pending": None,
            "checksum_errors": None,
            "failed": None,
            "migrations": [],
            "error": str(exc)[:240],
        }


def _overview(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    database = request.app.state.database
    integrity = database.integrity_check()
    live_database = (Path.home() / ".hermes" / "state" / "family_budget.sqlite3").resolve()
    try:
        current_database = database.path.expanduser().resolve()
    except OSError:
        current_database = database.path.expanduser()
    parity = _parity()
    migrations = _migrations(request)
    breakers = request.app.state.circuit_breaker.snapshot()
    transcription = request.app.state.speech_transcription.status()
    integration_summary = request.app.state.integration_config.overview()
    support_bundle = {
        "app_version": request.app.version,
        "runtime": {
            "read_only": settings.read_only,
            "external_side_effects": settings.external_side_effects,
            "legacy_writes": settings.allow_legacy_writes,
            "cookie_secure": settings.cookie_secure,
            "selected_port": request.app.state.selected_port,
            "live_port_untouched": request.app.state.selected_port != 8792,
        },
        "database": {
            "path": _display_path(database.path),
            "isolated_from_live": current_database != live_database,
            "integrity": integrity,
        },
        "migrations": {
            "ok": migrations["ok"],
            "pending": migrations["pending"],
            "checksum_errors": migrations["checksum_errors"],
            "failed": migrations["failed"],
        },
        "cache_entries": request.app.state.cache.size(),
        "circuit_breakers": {
            key: {
                "open": value.get("open", False),
                "half_open": value.get("half_open", False),
                "failures": value.get("failures", 0),
                "retry_after_seconds": value.get("retry_after_seconds", 0),
                "has_error": bool(value.get("last_error")),
            }
            for key, value in breakers.items()
        },
        "parity": parity["summary"],
        "parity_gaps": parity["gaps"],
        "transcription": transcription,
        "integrations": {
            "configured": integration_summary.get("configured", 0),
            "missing": integration_summary.get("missing", 0),
        },
        "scheduler": {
            "configured": settings.notification_scheduler_enabled,
            "active": bool(request.app.state.notification_scheduler_active),
        },
        "sensitive_values_exposed": False,
    }
    healthy = bool(
        integrity == "ok"
        and migrations["ok"]
        and support_bundle["runtime"]["live_port_untouched"]
        and support_bundle["database"]["isolated_from_live"]
    )
    return {
        "ok": healthy,
        "runtime": support_bundle["runtime"],
        "database": support_bundle["database"],
        "migrations": migrations,
        "cache": {"entries": support_bundle["cache_entries"]},
        "circuit_breakers": breakers,
        "parity": parity,
        "transcription": transcription,
        "integrations": support_bundle["integrations"],
        "scheduler": support_bundle["scheduler"],
        "support_bundle": support_bundle,
        "sensitive_values_exposed": False,
    }


@router.get("/overview")
def overview(request: Request, _: Identity = Depends(require_admin)) -> dict[str, Any]:
    return _overview(request)


@router.post("/cache/clear", dependencies=[Depends(require_same_origin)])
def clear_cache(
    payload: ConfirmAction,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict[str, Any]:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cachetömningen måste bekräftas")
    removed = request.app.state.cache.invalidate()
    return {"ok": True, "removed": removed, "cache": {"entries": request.app.state.cache.size()}}


@router.post("/breakers/reset", dependencies=[Depends(require_same_origin)])
def reset_breakers(
    payload: BreakerResetRequest,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict[str, Any]:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Återställningen måste bekräftas")
    removed = request.app.state.circuit_breaker.reset(payload.key)
    return {
        "ok": True,
        "removed": removed,
        "circuit_breakers": request.app.state.circuit_breaker.snapshot(),
    }
