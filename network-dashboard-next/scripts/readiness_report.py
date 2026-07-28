#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app.database.database import Database
from app.database.migrations import status as migration_status
from app.integrations.config_store import IntegrationConfigStore


REQUIRED_MODULES = (
    "fastapi",
    "uvicorn",
    "httpx",
    "multipart",
    "googleapiclient",
    "google_auth_oauthlib",
    "openpyxl",
    "cryptography",
    "pywebpush",
)
REQUIRED_STATIC = (
    "static/live/index.html",
    "static/live/app.js",
    "static/v2/index.html",
    "static/v2/app.js",
    "static/v2/configuration.js",
    "static/v2/configuration.css",
    "static/shared/app.css",
)
OPTIONAL_CREDENTIALS = (
    "home_assistant_url",
    "home_assistant_token",
    "discord_webhook_url",
    "vapid_public_key",
    "vapid_private_key",
    "vapid_subject",
)


def _env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _flag(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _permissions(path: Path) -> str:
    return oct(stat.S_IMODE(path.stat().st_mode)) if path.is_file() else ""


def _integrity(path: Path) -> str:
    if not path.is_file():
        return "missing"
    uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=20) as connection:
        connection.execute("PRAGMA query_only=ON")
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "unknown"


def _migration_state(database: Path, directory: Path) -> tuple[bool, str]:
    if not database.is_file():
        return False, "database missing"
    if not directory.is_dir():
        return False, "migrations directory missing"
    try:
        result = migration_status(database, directory)
    except Exception as exc:
        return False, str(exc)[:400]
    rows = result.get("migrations") or []
    pending = int(result.get("pending") or 0)
    mismatches = [str(row.get("version")) for row in rows if not row.get("checksum_match")]
    failed = [str(row.get("version")) for row in rows if row.get("status") not in {"applied"}]
    ok = pending == 0 and not mismatches and not failed
    detail = f"total={len(rows)} pending={pending} checksum_mismatches={','.join(mismatches) or 'none'}"
    return ok, detail


def _service_state(service: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, "systemctl unavailable"
    state = result.stdout.strip() or result.stderr.strip() or "unknown"
    return result.returncode == 0 and state == "active", state[:120]


def _check(checks: list[dict[str, Any]], check_id: str, ok: bool, detail: str, *, critical: bool = True) -> None:
    checks.append({
        "id": check_id,
        "ok": bool(ok),
        "critical": critical,
        "detail": str(detail)[:500],
    })


def _load_secret_values(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    values = payload.get("values") if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        return []
    return [str(value) for value in values.values() if str(value)]


def _google_shape(path: Path, kind: str) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, "invalid json"
    if not isinstance(payload, dict):
        return False, "invalid root"
    if kind == "client":
        client = payload.get("installed") or payload.get("web")
        valid = isinstance(client, dict) and all(
            str(client.get(key) or "").strip()
            for key in ("client_id", "client_secret", "auth_uri", "token_uri")
        )
    else:
        valid = all(
            str(payload.get(key) or "").strip()
            for key in ("client_id", "client_secret", "refresh_token")
        )
    return bool(valid), "valid" if valid else "required fields missing"


def _credential_checks(checks: list[dict[str, Any]], database: Path, secrets: Path) -> None:
    if not database.is_file():
        return
    try:
        store = IntegrationConfigStore(Database(database), secrets)
        for key in OPTIONAL_CREDENTIALS:
            status = store.status(key)
            _check(
                checks,
                f"credential.{key}",
                bool(status["configured"]),
                f"source={status['source']}",
                critical=False,
            )
    except Exception as exc:
        _check(checks, "credential.inventory", False, str(exc), critical=False)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    env_path = Path(args.env_file).expanduser()
    env = _env_file(env_path)
    database = Path(args.database or env.get("DASHBOARD_DB_PATH", "")).expanduser()
    live_database = Path(args.live_database).expanduser() if args.live_database else None
    secrets = Path(args.secrets or env.get("INTEGRATION_SECRETS_PATH", "")).expanduser()
    google_token = Path(args.google_token or env.get("GOOGLE_TOKEN_PATH", "")).expanduser()
    google_client = Path(args.google_client or env.get("GOOGLE_CLIENT_SECRETS_PATH", "")).expanduser()
    legacy_report = Path(args.legacy_report).expanduser()
    checks: list[dict[str, Any]] = []

    _check(checks, "python.version", sys.version_info >= (3, 12), sys.version.split()[0])
    missing_modules = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    _check(
        checks,
        "python.dependencies",
        not missing_modules,
        "missing: " + ", ".join(missing_modules) if missing_modules else "all installed",
    )

    missing_static = [relative for relative in REQUIRED_STATIC if not (root / relative).is_file()]
    _check(
        checks,
        "frontend.assets",
        not missing_static,
        "missing: " + ", ".join(missing_static) if missing_static else "all present",
    )

    _check(
        checks,
        "environment.file",
        env_path.is_file(),
        f"exists={env_path.is_file()} permissions={_permissions(env_path)}",
    )
    if env_path.is_file():
        _check(checks, "environment.permissions", _permissions(env_path) == "0o600", _permissions(env_path))
        _check(checks, "runtime.read_only", _flag(env.get("DASHBOARD_READ_ONLY", ""), True), "read-only enabled")
        _check(
            checks,
            "runtime.external_side_effects",
            not _flag(env.get("EXTERNAL_SIDE_EFFECTS", ""), False),
            "external side effects disabled",
        )
        required_secret_names = (
            "HOMELAB_ADMIN_PASSWORD",
            "PRESENCE_HASH_SECRET",
            "PRESENCE_INGEST_TOKEN",
            "ASSISTANT_SIGNING_SECRET",
        )
        missing = [name for name in required_secret_names if len(env.get(name, "")) < 16]
        _check(
            checks,
            "environment.generated_secrets",
            not missing,
            "missing: " + ", ".join(missing) if missing else "configured",
        )

    _check(checks, "database.exists", database.is_file(), str(database))
    if database.is_file():
        integrity = _integrity(database)
        _check(checks, "database.integrity", integrity == "ok", integrity)
        migrations_ok, migrations_detail = _migration_state(database, root / "migrations")
        _check(checks, "database.migrations", migrations_ok, migrations_detail)
    if live_database:
        isolated = database.resolve(strict=False) != live_database.resolve(strict=False)
        _check(checks, "database.isolated", isolated, "different paths" if isolated else "Next points at live database")
        _check(checks, "database.live_exists", live_database.is_file(), str(live_database))

    _check(
        checks,
        "integrations.secrets_file",
        secrets.is_file(),
        f"exists={secrets.is_file()} permissions={_permissions(secrets)}",
        critical=False,
    )
    if secrets.is_file():
        _check(checks, "integrations.secrets_permissions", _permissions(secrets) == "0o600", _permissions(secrets))
        try:
            payload = json.loads(secrets.read_text(encoding="utf-8"))
            valid_format = payload.get("format") == "network-dashboard-integration-secrets-v1"
        except (OSError, json.JSONDecodeError, AttributeError):
            valid_format = False
        _check(checks, "integrations.secrets_format", valid_format, "valid" if valid_format else "invalid")
    _credential_checks(checks, database, secrets)

    if legacy_report.is_file():
        try:
            report_text = legacy_report.read_text(encoding="utf-8")
            report = json.loads(report_text)
            safe_marker = report.get("sensitive_values_exposed") is False
            leaked = [value for value in _load_secret_values(secrets) if len(value) >= 8 and value in report_text]
            _check(checks, "legacy.report_json", True, "valid json")
            _check(checks, "legacy.report_safe_marker", safe_marker, "sensitive_values_exposed=false")
            _check(
                checks,
                "legacy.report_no_secret_values",
                not leaked,
                "no secret values present" if not leaked else "secret value detected",
            )
        except (OSError, json.JSONDecodeError):
            _check(checks, "legacy.report_json", False, "invalid json")
    else:
        _check(checks, "legacy.report", False, "missing", critical=False)

    token_ok, token_detail = _google_shape(google_token, "token")
    client_ok, client_detail = _google_shape(google_client, "client")
    _check(
        checks,
        "google.token",
        token_ok,
        f"{token_detail}; permissions={_permissions(google_token)}",
        critical=False,
    )
    _check(
        checks,
        "google.client",
        client_ok,
        f"{client_detail}; permissions={_permissions(google_client)}",
        critical=False,
    )
    if google_token.is_file():
        _check(checks, "google.token_permissions", _permissions(google_token) == "0o600", _permissions(google_token))
    if google_client.is_file():
        _check(checks, "google.client_permissions", _permissions(google_client) == "0o600", _permissions(google_client))

    service_ok, service_detail = _service_state(args.service)
    _check(checks, "service.next", service_ok, service_detail)

    if args.origin:
        try:
            response = httpx.get(
                args.origin.rstrip("/") + "/api/v2/health/ready",
                timeout=10,
                follow_redirects=False,
            )
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            _check(
                checks,
                "http.next_ready",
                response.status_code == 200 and payload.get("ok") is True,
                f"HTTP {response.status_code}",
            )
        except Exception as exc:
            _check(checks, "http.next_ready", False, str(exc))
    if args.live_origin:
        try:
            response = httpx.get(args.live_origin.rstrip("/") + "/", timeout=5, follow_redirects=False)
            _check(checks, "http.live_untouched", response.status_code < 500, f"HTTP {response.status_code}")
        except Exception as exc:
            _check(checks, "http.live_untouched", False, str(exc))

    failed_critical = [row["id"] for row in checks if row["critical"] and not row["ok"]]
    warnings = [row["id"] for row in checks if not row["critical"] and not row["ok"]]
    return {
        "ok": not failed_critical,
        "status": "ready" if not failed_critical else "blocked",
        "failed_critical": failed_critical,
        "warnings": warnings,
        "checks": checks,
        "sensitive_values_exposed": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Kontrollera om Network Dashboard Next är redo i WSL")
    result.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    result.add_argument("--origin", default="")
    result.add_argument("--live-origin", default="http://127.0.0.1:8792")
    result.add_argument("--database", default="")
    result.add_argument(
        "--live-database",
        default=str(Path.home() / ".hermes" / "state" / "family_budget.sqlite3"),
    )
    result.add_argument(
        "--env-file",
        default=str(Path.home() / ".config" / "network-dashboard-next.env"),
    )
    result.add_argument("--secrets", default="")
    result.add_argument("--google-token", default="")
    result.add_argument("--google-client", default="")
    result.add_argument(
        "--legacy-report",
        default=str(Path.home() / ".cache" / "network-dashboard-next" / "legacy-config-import.json"),
    )
    result.add_argument("--service", default="network-dashboard-next.service")
    return result


def main() -> int:
    report = build_report(parser().parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
