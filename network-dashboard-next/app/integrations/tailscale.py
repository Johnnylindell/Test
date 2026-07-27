from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker


class TailscaleAdapter:
    def __init__(self, cache: TTLCache, breaker: CircuitBreaker, dashboard_port: int) -> None:
        self.cache = cache
        self.breaker = breaker
        self.dashboard_port = dashboard_port

    @staticmethod
    def _command() -> list[str] | None:
        linux = shutil.which("tailscale")
        if linux:
            return [linux]
        for candidate in (
            "/mnt/c/Program Files/Tailscale/tailscale.exe",
            "/mnt/c/Program Files (x86)/Tailscale/tailscale.exe",
        ):
            if Path(candidate).is_file():
                return [candidate]
        return None

    def _load(self) -> dict:
        command = self._command()
        if not command:
            return {"installed": False, "running": False, "state": "not_installed"}
        if not self.breaker.allow("tailscale"):
            return {
                "installed": True,
                "running": False,
                "state": "circuit_open",
                "breaker": self.breaker.status("tailscale"),
            }
        try:
            completed = subprocess.run(
                [*command, "status", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError((completed.stderr or completed.stdout or "status failed")[:240])
            payload = json.loads(completed.stdout)
            own = payload.get("Self") if isinstance(payload.get("Self"), dict) else {}
            ips = [str(value) for value in own.get("TailscaleIPs") or []][:8]
            dns_name = str(own.get("DNSName") or "").rstrip(".")[:200]
            backend = str(payload.get("BackendState") or "unknown")[:80]
            running = bool(own) and backend.lower() not in {"needslogin", "stopped"}
            urls = [
                f"http://[{ip}]:{self.dashboard_port}" if ":" in ip else f"http://{ip}:{self.dashboard_port}"
                for ip in ips
            ]
            if dns_name:
                urls.append(f"http://{dns_name}:{self.dashboard_port}")
            self.breaker.success("tailscale")
            return {
                "installed": True,
                "running": running,
                "state": "connected" if running else "needs_login",
                "backend_state": backend,
                "tailscale_ips": ips,
                "dns_name": dns_name,
                "dashboard_urls": urls,
                "peer_count": len(payload.get("Peer") or {}),
            }
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
            self.breaker.failure("tailscale")
            return {
                "installed": True,
                "running": False,
                "state": "unavailable",
                "error": str(exc)[:240],
                "breaker": self.breaker.status("tailscale"),
            }

    def status(self, *, fresh: bool = False) -> dict:
        if fresh:
            self.cache.invalidate("tailscale:status")
        value, cached = self.cache.get_or_set("tailscale:status", 30, self._load)
        return {**value, "cache": "hit" if cached else "miss"}
