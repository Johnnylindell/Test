from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import require_admin, require_same_origin
from app.auth.service import Identity
from app.modules.homelab.repository import HomelabRepository
from app.modules.homelab.schemas import DeviceProfileUpsert, SubnetScanRequest, WakeOnLanRequest

router = APIRouter(prefix="/api/v2/admin/homelab", tags=["admin-homelab"])


def _run_tool(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return call()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nätverkskontrollen kunde inte slutföras: {str(exc)[:240]}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Nätverkskontrollen misslyckades: {str(exc)[:240]}",
        ) from exc


def _ports(value: str, *, limit: int = 30) -> list[int]:
    raw = [item.strip() for item in str(value or "").split(",") if item.strip()]
    if not raw:
        return []
    if len(raw) > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Högst {limit} portar får kontrolleras samtidigt",
        )
    try:
        ports = sorted({int(item) for item in raw})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portlistan är ogiltig") from exc
    if any(port < 1 or port > 65535 for port in ports):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portlistan innehåller en ogiltig port")
    return ports


def _require_external(request: Request) -> None:
    if request.app.state.settings.read_only or not request.app.state.settings.external_side_effects:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Aktiv nätverksskanning och Wake-on-LAN är avstängda i nuvarande driftläge",
        )


@router.get("/overview")
def overview(request: Request, _: Identity = Depends(require_admin)) -> dict:
    repository = HomelabRepository(request.app.state.database)
    return repository.overview()


@router.get("/system")
def system(request: Request, _: Identity = Depends(require_admin)) -> dict:
    repository = HomelabRepository(request.app.state.database)
    return {"ok": True, "system": repository.system_counts(), "live_probes_performed": False}


@router.get("/toolbox/status")
def toolbox_status(request: Request, _: Identity = Depends(require_admin)) -> dict:
    saved = request.app.state.network_tools.saved_status()
    overview_data = HomelabRepository(request.app.state.database).overview()
    agents = saved.get("computer_agents", {})
    return {
        "ok": True,
        "status": {
            "last_port_scan": saved.get("last_port_scan", {}),
            "last_network_scan": saved.get("last_network_scan", {}),
            "internet_history": list(saved.get("internet_history", []))[:50],
            "router_probe": saved.get("router_probe", {}),
            "device_profiles": overview_data.get("device_profiles", []),
            "computer_agents_configured": len(agents) if isinstance(agents, dict) else 0,
        },
        "policy": {
            "targeted_probes_allowed": True,
            "subnet_scan_allowed": bool(
                request.app.state.settings.external_side_effects and not request.app.state.settings.read_only
            ),
            "wake_on_lan_allowed": bool(
                request.app.state.settings.external_side_effects and not request.app.state.settings.read_only
            ),
            "arbitrary_shell_exposed": False,
            "secrets_exposed": False,
        },
        "live_probes_performed": False,
    }


@router.get("/toolbox/dns")
def dns(
    request: Request,
    host: str = Query(min_length=1, max_length=253),
    _: Identity = Depends(require_admin),
) -> dict:
    return _run_tool(lambda: request.app.state.network_tools.dns(host))


@router.get("/toolbox/ping")
def ping(
    request: Request,
    host: str = Query(min_length=1, max_length=253),
    timeout: int = Query(default=3, ge=1, le=10),
    _: Identity = Depends(require_admin),
) -> dict:
    return _run_tool(lambda: request.app.state.network_tools.ping(host, timeout))


@router.get("/toolbox/http")
def http_check(
    request: Request,
    url: str = Query(min_length=1, max_length=2000),
    _: Identity = Depends(require_admin),
) -> dict:
    return _run_tool(lambda: request.app.state.network_tools.http_check(url))


@router.get("/toolbox/tls")
def tls_check(
    request: Request,
    host: str = Query(min_length=1, max_length=253),
    port: int = Query(default=443, ge=1, le=65535),
    _: Identity = Depends(require_admin),
) -> dict:
    return _run_tool(lambda: request.app.state.network_tools.tls_check(host, port))


@router.get("/toolbox/ports")
def port_scan(
    request: Request,
    host: str = Query(min_length=1, max_length=253),
    ports: str = Query(default="22,53,80,443,445,8123", max_length=400),
    _: Identity = Depends(require_admin),
) -> dict:
    selected = _ports(ports)
    if not selected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minst en port måste anges")
    return _run_tool(lambda: request.app.state.network_tools.port_scan(host, selected))


@router.get("/toolbox/device")
def device_probe(
    request: Request,
    host: str = Query(min_length=1, max_length=253),
    ports: str = Query(default="22,53,80,443,445,8123", max_length=400),
    _: Identity = Depends(require_admin),
) -> dict:
    selected = _ports(ports)
    return _run_tool(lambda: request.app.state.network_tools.device_probe(host, selected or None))


@router.get("/toolbox/router")
def router_probe(
    request: Request,
    host: str = Query(min_length=1, max_length=253),
    _: Identity = Depends(require_admin),
) -> dict:
    return _run_tool(lambda: request.app.state.network_tools.router_probe(host))


@router.get("/toolbox/internet")
def internet_check(request: Request, _: Identity = Depends(require_admin)) -> dict:
    return _run_tool(request.app.state.network_tools.internet_check)


@router.put("/devices/{profile_id}", dependencies=[Depends(require_same_origin)])
def save_device_profile(
    profile_id: str,
    payload: DeviceProfileUpsert,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    result = _run_tool(
        lambda: request.app.state.network_tools.save_device_profile(profile_id, payload.model_dump())
    )
    return {"ok": True, "profile": result}


@router.delete("/devices/{profile_id}", dependencies=[Depends(require_same_origin)])
def delete_device_profile(
    profile_id: str,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    if not request.app.state.network_tools.delete_device_profile(profile_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enhetsprofilen hittades inte")
    return {"ok": True}


@router.post("/toolbox/subnet-scan", dependencies=[Depends(require_same_origin)])
def subnet_scan(
    payload: SubnetScanRequest,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    _require_external(request)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nätverksskanningen måste bekräftas")
    return _run_tool(lambda: request.app.state.network_tools.subnet_scan(payload.network, payload.ports))


@router.post("/toolbox/wake-on-lan", dependencies=[Depends(require_same_origin)])
def wake_on_lan(
    payload: WakeOnLanRequest,
    request: Request,
    _: Identity = Depends(require_admin),
) -> dict:
    _require_external(request)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wake-on-LAN måste bekräftas")
    return _run_tool(
        lambda: request.app.state.network_tools.wake_on_lan(payload.mac, payload.broadcast, payload.port)
    )
