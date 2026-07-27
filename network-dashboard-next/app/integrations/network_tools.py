from __future__ import annotations

import ipaddress
import json
import shutil
import socket
import ssl
import subprocess
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.cache import TTLCache
from app.core.circuit_breaker import CircuitBreaker
from app.database.database import Database


class NetworkToolsAdapter:
    def __init__(self, database: Database, cache: TTLCache, breaker: CircuitBreaker) -> None:
        self.database = database
        self.cache = cache
        self.breaker = breaker

    @staticmethod
    def _host(value: str) -> str:
        host = str(value or "").strip().rstrip(".")
        if not host or len(host) > 253:
            raise ValueError("Ogiltigt värdnamn")
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            pass
        if any(not label or len(label) > 63 for label in host.split(".")):
            raise ValueError("Ogiltigt värdnamn")
        if any(not all(ch.isalnum() or ch == "-" for ch in label) for label in host.split(".")):
            raise ValueError("Ogiltigt värdnamn")
        return host

    @staticmethod
    def _port(value: int) -> int:
        port = int(value)
        if not 1 <= port <= 65535:
            raise ValueError("Ogiltig port")
        return port

    def dns(self, host: str) -> dict[str, Any]:
        target = self._host(host)
        rows = socket.getaddrinfo(target, None)
        addresses = sorted({str(row[4][0]) for row in rows})
        return {"ok": True, "host": target, "addresses": addresses}

    def ping(self, host: str, timeout: int = 3) -> dict[str, Any]:
        target = self._host(host)
        executable = shutil.which("ping")
        if not executable:
            return {"ok": False, "host": target, "error": "ping saknas"}
        result = subprocess.run(
            [executable, "-c", "1", "-W", str(max(1, min(timeout, 10))), target],
            capture_output=True,
            text=True,
            timeout=max(2, min(timeout + 2, 12)),
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "host": target,
            "returncode": result.returncode,
            "output": (result.stdout or result.stderr)[-2000:],
        }

    def http_check(self, url: str) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(str(url or ""))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Ogiltig HTTP-adress")
        started = datetime.now(timezone.utc)
        response = httpx.get(url, timeout=10, follow_redirects=True)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        return {
            "ok": response.is_success,
            "url": str(response.url),
            "status": response.status_code,
            "elapsed_ms": round(elapsed, 1),
            "content_type": response.headers.get("content-type", ""),
        }

    def tls_check(self, host: str, port: int = 443) -> dict[str, Any]:
        target = self._host(host)
        target_port = self._port(port)
        context = ssl.create_default_context()
        with socket.create_connection((target, target_port), timeout=8) as raw:
            with context.wrap_socket(raw, server_hostname=target) as secured:
                certificate = secured.getpeercert()
        return {
            "ok": True,
            "host": target,
            "port": target_port,
            "subject": certificate.get("subject"),
            "issuer": certificate.get("issuer"),
            "not_before": certificate.get("notBefore"),
            "not_after": certificate.get("notAfter"),
            "san": certificate.get("subjectAltName", []),
        }

    def port_scan(self, host: str, ports: list[int], timeout: float = 0.35) -> dict[str, Any]:
        target = self._host(host)
        checked = sorted({self._port(port) for port in ports[:200]})
        open_ports = []
        for port in checked:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(max(0.05, min(timeout, 2.0)))
                if sock.connect_ex((target, port)) == 0:
                    open_ports.append(port)
        result = {
            "ok": True,
            "host": target,
            "ports_checked": checked,
            "open_ports": open_ports,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }
        self.database.set_json_state("last_port_scan", result)
        return result

    def subnet_scan(self, network: str, ports: list[int]) -> dict[str, Any]:
        subnet = ipaddress.ip_network(str(network or ""), strict=False)
        if not subnet.is_private or subnet.num_addresses > 256:
            raise ValueError("Endast privata nät upp till /24 stöds")
        devices = []
        checked_ports = sorted({self._port(port) for port in ports[:30]})
        for address in list(subnet.hosts())[:254]:
            opened = []
            for port in checked_ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.08)
                    if sock.connect_ex((str(address), port)) == 0:
                        opened.append(port)
            if opened:
                devices.append({"ip": str(address), "open_ports": opened})
        result = {
            "ok": True,
            "network": str(subnet),
            "devices": devices,
            "device_count": len(devices),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }
        self.database.set_json_state("last_network_scan", result)
        return result

    def internet_check(self) -> dict[str, Any]:
        checks = []
        for url in ("https://www.cloudflare.com/cdn-cgi/trace", "https://www.google.com/generate_204"):
            try:
                checks.append(self.http_check(url))
            except Exception as exc:
                checks.append({"ok": False, "url": url, "error": str(exc)[:240]})
        result = {
            "ok": any(row.get("ok") for row in checks),
            "checks": checks,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        history = self.database.get_json_state("internet_history", [])
        rows = list(history) if isinstance(history, list) else []
        rows.insert(0, result)
        self.database.set_json_state("internet_history", rows[:500])
        return result

    def wake_on_lan(self, mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> dict[str, Any]:
        clean = "".join(ch for ch in str(mac or "") if ch.isalnum()).lower()
        if len(clean) != 12 or any(ch not in "0123456789abcdef" for ch in clean):
            raise ValueError("Ogiltig MAC-adress")
        address = ipaddress.ip_address(broadcast)
        if not address.is_private and not address.is_unspecified and str(address) != "255.255.255.255":
            raise ValueError("Ogiltig broadcast-adress")
        packet = bytes.fromhex("ff" * 6 + clean * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (str(address), self._port(port)))
        return {"ok": True, "mac": clean, "broadcast": str(address), "port": port}

    def saved_status(self) -> dict[str, Any]:
        return {
            "last_port_scan": self.database.get_json_state("last_port_scan", {}),
            "last_network_scan": self.database.get_json_state("last_network_scan", {}),
            "internet_history": self.database.get_json_state("internet_history", [])[:50],
            "router_probe": self.database.get_json_state("router_probe", {}),
            "device_profiles": self.database.get_json_state("device_profiles", {}),
            "computer_agents": self.database.get_json_state("computer_agents", {}),
        }
