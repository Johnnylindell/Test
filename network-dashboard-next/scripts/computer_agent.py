from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Any

import httpx


def load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Agentkonfigurationen kunde inte läsas: {exc}") from exc
    origin = str(data.get("origin") or "").strip().rstrip("/")
    token = str(data.get("token") or "").strip()
    if not origin.startswith(("http://", "https://")) or len(token) < 20:
        raise SystemExit("Agentkonfigurationen kräver origin och token")
    return {
        "origin": origin,
        "token": token,
        "dashboard_url": str(data.get("dashboard_url") or origin).strip(),
        "interval_seconds": max(30, min(3600, int(data.get("interval_seconds") or 60))),
        "verify_tls": bool(data.get("verify_tls", True)),
    }


def status_snapshot() -> dict[str, Any]:
    disk = shutil.disk_usage(Path.home())
    return {
        "hostname": socket.gethostname()[:120],
        "platform": platform.system()[:80],
        "platform_release": platform.release()[:120],
        "python": platform.python_version(),
        "user": os.getenv("USERNAME") or os.getenv("USER") or "",
        "disk": {
            "total_bytes": disk.total,
            "free_bytes": disk.free,
            "used_percent": round((disk.used / disk.total * 100) if disk.total else 0, 1),
        },
        "checked_at_epoch": time.time(),
    }


def notify(message: str) -> dict[str, Any]:
    clean = " ".join(message.strip().split())[:500]
    if not clean:
        return {"ok": False, "error": "Tom notifiering"}
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Add-Type -AssemblyName PresentationFramework;"
                    f"[System.Windows.MessageBox]::Show({json.dumps(clean)},'Lindells app') | Out-Null",
                ],
                timeout=15,
                check=False,
                capture_output=True,
            )
        elif system == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'display notification {json.dumps(clean)} with title "Lindells app"'],
                timeout=15,
                check=False,
                capture_output=True,
            )
        elif shutil.which("notify-send"):
            subprocess.run(
                ["notify-send", "Lindells app", clean],
                timeout=15,
                check=False,
                capture_output=True,
            )
        else:
            return {"ok": False, "error": "Systemnotifieringar stöds inte på den här datorn"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)[:240]}
    return {"ok": True}


def execute(command: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    command_type = str(command.get("command_type") or "")
    payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
    if command_type == "collect_status":
        return {"ok": True, "status": status_snapshot()}
    if command_type == "refresh_dashboard":
        opened = webbrowser.open(config["dashboard_url"], new=0, autoraise=True)
        return {"ok": bool(opened), "dashboard_url_opened": bool(opened)}
    if command_type == "notify":
        return notify(str(payload.get("message") or ""))
    return {"ok": False, "error": "Kommandotypen stöds inte"}


def request(
    client: httpx.Client,
    config: dict[str, Any],
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.request(
        method,
        config["origin"] + path,
        headers={"Authorization": f"Bearer {config['token']}"},
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def run_once(config: dict[str, Any]) -> dict[str, Any]:
    completed = 0
    with httpx.Client(timeout=15, verify=config["verify_tls"], follow_redirects=False) as client:
        request(client, config, "POST", "/api/v2/operations/agent/heartbeat", {"status": status_snapshot()})
        commands = request(client, config, "GET", "/api/v2/operations/agent/commands").get("commands") or []
        for command in commands[:20]:
            result = execute(command, config)
            request(
                client,
                config,
                "POST",
                f"/api/v2/operations/agent/commands/{command['id']}/result",
                {"status": "completed" if result.get("ok") else "failed", "result": result},
            )
            completed += 1
    return {"ok": True, "commands_completed": completed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Restricted Lindells computer agent")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".config" / "network-dashboard-next-agent.json",
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config.expanduser())
    while True:
        try:
            result = run_once(config)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)[:240]}, ensure_ascii=False), flush=True)
        if args.once:
            return 0
        time.sleep(config["interval_seconds"])


if __name__ == "__main__":
    raise SystemExit(main())
