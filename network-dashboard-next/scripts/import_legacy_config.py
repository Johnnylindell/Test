from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.database.database import Database
from app.integrations.config_store import IntegrationConfigStore


_ENV_TO_KEY = {
    "HOME_ASSISTANT_URL": "home_assistant_url",
    "HOME_ASSISTANT_TOKEN": "home_assistant_token",
    "DISCORD_WEBHOOK_URL": "discord_webhook_url",
    "VAPID_PUBLIC_KEY": "vapid_public_key",
    "VAPID_PRIVATE_KEY": "vapid_private_key",
    "VAPID_SUBJECT": "vapid_subject",
}
_GOOGLE_TOKEN_NAMES = ("google_token.json", "token.json", "google-token.json")
_GOOGLE_CLIENT_NAMES = (
    "google_client_secret.json",
    "google_client_secrets.json",
    "client_secret.json",
    "credentials.json",
)


def _env_lines(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return values
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in _ENV_TO_KEY:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            values[key] = value
    return values


def _systemd_environment(service: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not service:
        return values
    try:
        environment = subprocess.run(
            ["systemctl", "--user", "show", service, "--property=Environment", "--value"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if environment.returncode == 0:
            for item in shlex.split(environment.stdout.strip()):
                if "=" not in item:
                    continue
                key, value = item.split("=", 1)
                if key in _ENV_TO_KEY and value:
                    values[key] = value
        environment_files = subprocess.run(
            ["systemctl", "--user", "show", service, "--property=EnvironmentFiles", "--value"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if environment_files.returncode == 0:
            for item in shlex.split(environment_files.stdout.strip()):
                candidate = item.split(";", 1)[0].split("(", 1)[0].strip().lstrip("-")
                if candidate:
                    values.update(_env_lines(Path(candidate).expanduser()))
    except (OSError, subprocess.SubprocessError, ValueError):
        return values
    return values


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _valid_google_client(payload: dict[str, Any]) -> bool:
    client = payload.get("installed") or payload.get("web")
    return isinstance(client, dict) and all(
        str(client.get(key) or "").strip()
        for key in ("client_id", "client_secret", "auth_uri", "token_uri")
    )


def _valid_google_token(payload: dict[str, Any]) -> bool:
    return all(
        str(payload.get(key) or "").strip()
        for key in ("client_id", "client_secret", "refresh_token")
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _candidate_directories(legacy_root: Path | None) -> list[Path]:
    candidates = [
        Path.home() / ".config" / "network-dashboard",
        Path.home() / ".config" / "homelab-control-center",
        Path.home() / ".config" / "hermes",
        Path.home() / ".hermes" / "state",
    ]
    if legacy_root:
        root = legacy_root.expanduser()
        candidates.extend([root, root / "config", root / "data"])
    result: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(candidate)
    return result


def _find_google_file(
    directories: list[Path],
    names: tuple[str, ...],
    validator,
) -> tuple[Path | None, dict[str, Any] | None]:
    for directory in directories:
        for name in names:
            candidate = directory / name
            payload = _read_json(candidate)
            if payload is not None and validator(payload):
                return candidate, payload
    return None, None


def import_configuration(args: argparse.Namespace) -> dict[str, Any]:
    database = Database(Path(args.legacy_db).expanduser())
    store = IntegrationConfigStore(database, Path(args.secrets).expanduser())
    adopted_database = store.adopt_legacy(overwrite=args.replace)

    adopted_environment: list[str] = []
    skipped_environment: list[str] = []
    for environment_name, value in _systemd_environment(args.service).items():
        key = _ENV_TO_KEY[environment_name]
        if store.get(key) and not args.replace:
            skipped_environment.append(key)
            continue
        try:
            store.set(key, value)
            adopted_environment.append(key)
        except ValueError:
            skipped_environment.append(key)

    directories = _candidate_directories(Path(args.legacy_root) if args.legacy_root else None)
    google: dict[str, Any] = {
        "token": "existing" if Path(args.google_token_target).expanduser().is_file() else "missing",
        "client_secret": "existing" if Path(args.google_client_target).expanduser().is_file() else "missing",
    }
    if args.replace or google["token"] == "missing":
        source, payload = _find_google_file(directories, _GOOGLE_TOKEN_NAMES, _valid_google_token)
        if source and payload:
            _write_json(Path(args.google_token_target).expanduser(), payload)
            google["token"] = "adopted"
            google["token_source_name"] = source.name
    if args.replace or google["client_secret"] == "missing":
        source, payload = _find_google_file(directories, _GOOGLE_CLIENT_NAMES, _valid_google_client)
        if source and payload:
            _write_json(Path(args.google_client_target).expanduser(), payload)
            google["client_secret"] = "adopted"
            google["client_source_name"] = source.name

    return {
        "ok": True,
        "database": {
            "adopted": adopted_database["adopted"],
            "skipped": adopted_database["skipped"],
        },
        "systemd_environment": {
            "adopted": sorted(adopted_environment),
            "skipped": sorted(skipped_environment),
        },
        "google": google,
        "secrets_file_exists": Path(args.secrets).expanduser().is_file(),
        "sensitive_values_exposed": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Adoptera tillåtna inställningar från den gamla dashboarden")
    result.add_argument("--legacy-db", required=True)
    result.add_argument("--secrets", required=True)
    result.add_argument("--google-token-target", required=True)
    result.add_argument("--google-client-target", required=True)
    result.add_argument("--legacy-root", default="")
    result.add_argument("--service", default="homelab-control-center.service")
    result.add_argument("--replace", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    print(json.dumps(import_configuration(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
