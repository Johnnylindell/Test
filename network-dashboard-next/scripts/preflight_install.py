#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_COMMANDS = ("rsync", "openssl", "systemctl", "realpath")


def check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
    checks.append({"id": name, "ok": bool(ok), "detail": str(detail)[:500]})


def command_available(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    return bool(path), path or "missing"


def user_systemd() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show-environment"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    detail = result.stdout.strip() or result.stderr.strip() or f"exit={result.returncode}"
    return result.returncode == 0, detail


def build_report(live_database: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    check(
        checks,
        "python.version",
        sys.version_info >= (3, 12),
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}; Python 3.12+ krävs",
    )
    check(
        checks,
        "python.venv",
        importlib.util.find_spec("venv") is not None,
        "venv-modulen tillgänglig" if importlib.util.find_spec("venv") is not None else "installera python3-venv",
    )
    for command in REQUIRED_COMMANDS:
        ok, detail = command_available(command)
        check(checks, f"command.{command}", ok, detail)
    systemd_ok, systemd_detail = user_systemd()
    check(checks, "systemd.user", systemd_ok, systemd_detail)
    check(
        checks,
        "database.live_exists",
        live_database.is_file(),
        str(live_database),
    )
    failed = [row["id"] for row in checks if not row["ok"]]
    return {
        "ok": not failed,
        "status": "ready" if not failed else "blocked",
        "failed": failed,
        "checks": checks,
        "sensitive_values_exposed": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Kontrollera WSL innan parallellinstallationen startar")
    result.add_argument(
        "--live-database",
        default=str(Path.home() / ".hermes" / "state" / "family_budget.sqlite3"),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    report = build_report(Path(args.live_database).expanduser())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
