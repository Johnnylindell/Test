from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database.database import Database

_UNIT = re.compile(r"^[A-Za-z0-9_.@-]+\.service$")
_COMMANDS = {"notify", "refresh_dashboard", "collect_status"}
_ACTIONS = {"start", "stop", "restart"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _safe_json(value: Any, *, max_depth: int = 3) -> Any:
    if max_depth < 0:
        return None
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return value[:1000]
    if isinstance(value, list):
        return [_safe_json(item, max_depth=max_depth - 1) for item in value[:100]]
    if isinstance(value, dict):
        return {
            str(key)[:100]: _safe_json(item, max_depth=max_depth - 1)
            for key, item in list(value.items())[:100]
        }
    return str(value)[:1000]


class OperationsService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def ready(self) -> bool:
        return all(
            self.database.table_exists(table)
            for table in (
                "managed_services",
                "computer_agents_v2",
                "agent_commands_v2",
                "homelab_baselines_v2",
            )
        )

    @staticmethod
    def system_snapshot() -> dict[str, Any]:
        disk = shutil.disk_usage(Path.home())
        memory_total = 0
        memory_available = 0
        try:
            values = {}
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                key, raw = line.split(":", 1)
                values[key] = int(raw.strip().split()[0]) * 1024
            memory_total = values.get("MemTotal", 0)
            memory_available = values.get("MemAvailable", 0)
        except (OSError, ValueError, IndexError):
            pass
        uptime_seconds = 0.0
        try:
            uptime_seconds = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            pass
        try:
            load = list(os.getloadavg())
        except OSError:
            load = []
        return {
            "checked_at": _now(),
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "used_percent": round((disk.used / disk.total * 100) if disk.total else 0, 1),
            },
            "memory": {
                "total_bytes": memory_total,
                "available_bytes": memory_available,
                "used_percent": round(
                    ((memory_total - memory_available) / memory_total * 100) if memory_total else 0,
                    1,
                ),
            },
            "uptime_seconds": round(uptime_seconds),
            "load_average": load,
        }

    def managed_services(self, *, live: bool = True) -> list[dict[str, Any]]:
        if not self.database.table_exists("managed_services"):
            return []
        rows = self.database.fetch_all(
            "SELECT id,label,unit_name,active,created_at,updated_at FROM managed_services "
            "ORDER BY active DESC,label COLLATE NOCASE"
        )
        return [{**row, "status": self.service_status(row["unit_name"]) if live and row.get("active") else {}} for row in rows]

    @staticmethod
    def service_status(unit_name: str) -> dict[str, Any]:
        if not _UNIT.fullmatch(unit_name):
            raise ValueError("Ogiltigt service-namn")
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "show",
                    unit_name,
                    "--property=ActiveState,SubState,LoadState,UnitFileState,MainPID",
                    "--no-pager",
                ],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "state": "unavailable", "error": str(exc)[:240]}
        values = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        return {
            "ok": result.returncode == 0,
            "active_state": values.get("ActiveState", "unknown"),
            "sub_state": values.get("SubState", "unknown"),
            "load_state": values.get("LoadState", "unknown"),
            "unit_file_state": values.get("UnitFileState", "unknown"),
            "main_pid": int(values.get("MainPID") or 0),
            "error": result.stderr.strip()[:240] if result.returncode else "",
        }

    def add_service(self, label: str, unit_name: str) -> str:
        if not _UNIT.fullmatch(unit_name):
            raise ValueError("Ogiltigt service-namn")
        service_id = "managed-service-" + secrets.token_hex(8)
        now = _now()
        self.database.execute(
            "INSERT INTO managed_services(id,label,unit_name,active,created_at,updated_at) VALUES(?,?,?,1,?,?) "
            "ON CONFLICT(unit_name) DO UPDATE SET label=excluded.label,active=1,updated_at=excluded.updated_at",
            (service_id, label[:120], unit_name, now, now),
        )
        row = self.database.fetch_one("SELECT id FROM managed_services WHERE unit_name=?", (unit_name,))
        return str(row["id"]) if row else service_id

    def remove_service(self, service_id: str) -> bool:
        before = self.database.count("managed_services", "id=?", (service_id,))
        self.database.execute("DELETE FROM managed_services WHERE id=?", (service_id,))
        return before == 1

    def service_action(self, service_id: str, action: str) -> dict[str, Any]:
        if action not in _ACTIONS:
            raise ValueError("Serviceåtgärden är inte tillåten")
        row = self.database.fetch_one(
            "SELECT unit_name FROM managed_services WHERE id=? AND active=1",
            (service_id,),
        )
        if not row:
            raise ValueError("Servicen finns inte i tillåtelselistan")
        unit_name = str(row["unit_name"])
        result = subprocess.run(
            ["systemctl", "--user", action, unit_name],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "action": action,
            "unit_name": unit_name,
            "error": result.stderr.strip()[:240] if result.returncode else "",
            "status": self.service_status(unit_name),
        }

    def create_agent(self, name: str) -> dict[str, Any]:
        token = secrets.token_urlsafe(40)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        agent_id = "agent-" + secrets.token_hex(8)
        now = _now()
        self.database.execute(
            "INSERT INTO computer_agents_v2(id,name,token_hash,active,last_seen,status_json,created_at,updated_at) "
            "VALUES(?,?,?,1,'','{}',?,?)",
            (agent_id, name[:120], token_hash, now, now),
        )
        return {
            "id": agent_id,
            "name": name[:120],
            "token": token,
            "token_returned_once": True,
        }

    def authenticate_agent(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return self.database.fetch_one(
            "SELECT id,name,active,last_seen FROM computer_agents_v2 WHERE token_hash=? AND active=1",
            (token_hash,),
        )

    def heartbeat(self, agent_id: str, status: dict[str, Any]) -> dict[str, Any]:
        sanitized = _safe_json(status)
        now = _now()
        self.database.execute(
            "UPDATE computer_agents_v2 SET last_seen=?,status_json=?,updated_at=? WHERE id=? AND active=1",
            (now, _json(sanitized), now, agent_id),
        )
        return {"ok": True, "agent_id": agent_id, "last_seen": now}

    def agents(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("computer_agents_v2"):
            return []
        rows = self.database.fetch_all(
            "SELECT id,name,active,last_seen,status_json,created_at,updated_at FROM computer_agents_v2 "
            "ORDER BY active DESC,last_seen DESC,name COLLATE NOCASE"
        )
        result = []
        now = time.time()
        for row in rows:
            try:
                status = json.loads(row.get("status_json") or "{}")
            except json.JSONDecodeError:
                status = {}
            last_seen = str(row.get("last_seen") or "")
            try:
                seen_epoch = datetime.fromisoformat(last_seen.replace("Z", "+00:00")).timestamp()
            except ValueError:
                seen_epoch = 0
            result.append({
                "id": row["id"],
                "name": row["name"],
                "active": bool(row.get("active")),
                "last_seen": last_seen,
                "online": bool(last_seen and now - seen_epoch <= 180),
                "status": _safe_json(status),
                "created_at": row.get("created_at"),
            })
        return result

    def delete_agent(self, agent_id: str) -> bool:
        before = self.database.count("computer_agents_v2", "id=?", (agent_id,))
        self.database.execute("DELETE FROM computer_agents_v2 WHERE id=?", (agent_id,))
        return before == 1

    def queue_command(
        self,
        agent_id: str,
        command_type: str,
        payload: dict[str, Any],
        actor: str,
    ) -> str:
        if command_type not in _COMMANDS:
            raise ValueError("Agentkommandot är inte tillåtet")
        if not self.database.fetch_one(
            "SELECT id FROM computer_agents_v2 WHERE id=? AND active=1",
            (agent_id,),
        ):
            raise ValueError("Agenten hittades inte")
        clean_payload = _safe_json(payload)
        if command_type == "notify":
            message = str((clean_payload or {}).get("message") or "")[:500]
            if not message:
                raise ValueError("Notismeddelande krävs")
            clean_payload = {"message": message}
        else:
            clean_payload = {}
        command_id = "agent-command-" + secrets.token_hex(8)
        self.database.execute(
            "INSERT INTO agent_commands_v2(id,agent_id,command_type,payload_json,status,created_by,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (command_id, agent_id, command_type, _json(clean_payload), "queued", actor[:80], _now()),
        )
        return command_id

    def claim_commands(self, agent_id: str) -> list[dict[str, Any]]:
        now = _now()
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT id,command_type,payload_json,created_at FROM agent_commands_v2 "
                "WHERE agent_id=? AND status='queued' ORDER BY created_at LIMIT 20",
                (agent_id,),
            ).fetchall()
            ids = [str(row["id"]) for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"UPDATE agent_commands_v2 SET status='claimed',claimed_at=? WHERE id IN ({placeholders})",
                    (now, *ids),
                )
        result = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            result.append({
                "id": row["id"],
                "command_type": row["command_type"],
                "payload": _safe_json(payload),
                "created_at": row["created_at"],
            })
        return result

    def complete_command(
        self,
        agent_id: str,
        command_id: str,
        status: str,
        result: dict[str, Any],
    ) -> bool:
        before = self.database.count(
            "agent_commands_v2",
            "id=? AND agent_id=? AND status='claimed'",
            (command_id, agent_id),
        )
        if not before:
            return False
        self.database.execute(
            "UPDATE agent_commands_v2 SET status=?,completed_at=?,result_json=? "
            "WHERE id=? AND agent_id=? AND status='claimed'",
            (status, _now(), _json(_safe_json(result)), command_id, agent_id),
        )
        return True

    def recent_commands(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("agent_commands_v2"):
            return []
        return self.database.fetch_all(
            "SELECT c.id,c.agent_id,a.name AS agent_name,c.command_type,c.status,c.created_by,c.created_at,"
            "c.claimed_at,c.completed_at FROM agent_commands_v2 c "
            "JOIN computer_agents_v2 a ON a.id=c.agent_id ORDER BY c.created_at DESC LIMIT 100"
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "system": self.system_snapshot(),
            "services": self.managed_services(live=True),
            "agents": self.agents(),
        }

    def create_baseline(self, label: str, actor: str) -> str:
        baseline_id = "baseline-" + secrets.token_hex(8)
        self.database.execute(
            "INSERT INTO homelab_baselines_v2(id,label,snapshot_json,created_by,created_at) VALUES(?,?,?,?,?)",
            (baseline_id, label[:120], _json(self.snapshot()), actor[:80], _now()),
        )
        return baseline_id

    def baselines(self) -> list[dict[str, Any]]:
        if not self.database.table_exists("homelab_baselines_v2"):
            return []
        rows = self.database.fetch_all(
            "SELECT id,label,snapshot_json,created_by,created_at FROM homelab_baselines_v2 "
            "ORDER BY created_at DESC LIMIT 30"
        )
        return [
            {
                "id": row["id"],
                "label": row["label"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def compare_baseline(self, baseline_id: str) -> dict[str, Any]:
        row = self.database.fetch_one(
            "SELECT label,snapshot_json,created_at FROM homelab_baselines_v2 WHERE id=?",
            (baseline_id,),
        )
        if not row:
            raise ValueError("Baslinjen hittades inte")
        try:
            previous = json.loads(row["snapshot_json"])
        except json.JSONDecodeError:
            previous = {}
        current = self.snapshot()
        old_services = {
            service.get("unit_name"): service.get("status", {}).get("active_state")
            for service in previous.get("services", [])
        }
        new_services = {
            service.get("unit_name"): service.get("status", {}).get("active_state")
            for service in current.get("services", [])
        }
        service_changes = [
            {"unit_name": unit, "before": old_services.get(unit), "after": new_services.get(unit)}
            for unit in sorted(set(old_services) | set(new_services))
            if old_services.get(unit) != new_services.get(unit)
        ]
        return {
            "ok": True,
            "baseline": {
                "id": baseline_id,
                "label": row["label"],
                "created_at": row["created_at"],
            },
            "current": current,
            "changes": {
                "services": service_changes,
                "disk_used_percent": {
                    "before": previous.get("system", {}).get("disk", {}).get("used_percent"),
                    "after": current.get("system", {}).get("disk", {}).get("used_percent"),
                },
                "memory_used_percent": {
                    "before": previous.get("system", {}).get("memory", {}).get("used_percent"),
                    "after": current.get("system", {}).get("memory", {}).get("used_percent"),
                },
                "agents_online": {
                    "before": sum(1 for agent in previous.get("agents", []) if agent.get("online")),
                    "after": sum(1 for agent in current.get("agents", []) if agent.get("online")),
                },
            },
        }

    def overview(self) -> dict[str, Any]:
        return {
            "ok": self.ready(),
            "ready": self.ready(),
            "system": self.system_snapshot(),
            "services": self.managed_services(live=True),
            "agents": self.agents(),
            "commands": self.recent_commands(),
            "baselines": self.baselines(),
            "arbitrary_shell_exposed": False,
            "active_network_scan_exposed": False,
            "agent_token_exposed": False,
        }
