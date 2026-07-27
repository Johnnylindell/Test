from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Filen saknas: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Filen innehåller ogiltig JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON-objekt krävs i {path}")
    return value


def _devices(state: dict[str, Any]) -> list[dict[str, Any]]:
    value = state.get("devices") or {}
    if isinstance(value, dict):
        return [row for row in value.values() if isinstance(row, dict)]
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _normalized(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", ":")


def collect_observations(state: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    devices = _devices(state)
    by_identifier = {}
    for row in devices:
        for field in ("mac", "id", "identifier"):
            identifier = _normalized(row.get(field))
            if identifier:
                by_identifier[identifier] = row
    observations = []
    for mapping in config.get("devices") or []:
        if not isinstance(mapping, dict) or not mapping.get("enabled", True):
            continue
        identifier = _normalized(mapping.get("source_identifier"))
        owner = str(mapping.get("owner") or "").strip()
        if not identifier or not owner:
            continue
        row = by_identifier.get(identifier, {})
        observations.append({
            "source_identifier": str(mapping["source_identifier"]),
            "present": bool(row.get("is_present")),
            "observed_at": str(row.get("last_checked") or state.get("updated_at") or ""),
        })
    return observations


def post_observations(origin: str, token: str, observations: list[dict[str, Any]]) -> dict[str, int]:
    if not token:
        raise RuntimeError("PRESENCE_INGEST_TOKEN saknas")
    endpoint = origin.rstrip("/") + "/api/v2/presence/observations"
    sent = 0
    transitions = 0
    with httpx.Client(timeout=10, headers={"X-Presence-Token": token}) as client:
        for observation in observations:
            response = client.post(endpoint, json=observation)
            response.raise_for_status()
            payload = response.json()
            sent += 1
            transitions += int(bool(payload.get("transition")))
    return {"sent": sent, "transitions": transitions}


def main() -> int:
    parser = argparse.ArgumentParser(description="Skicka sanerade närvaroobservationer till Dashboard Next")
    parser.add_argument(
        "--state",
        type=Path,
        default=Path.home() / ".hermes" / "state" / "lan_new_device_watch.json",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".config" / "network-dashboard-next-presence.json",
    )
    parser.add_argument("--origin", default=os.getenv("DASHBOARD_NEXT_ORIGIN", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.origin and not args.dry_run:
        raise RuntimeError("DASHBOARD_NEXT_ORIGIN eller --origin krävs")
    state = _load_object(args.state.expanduser())
    config = _load_object(args.config.expanduser())
    observations = collect_observations(state, config)
    if args.dry_run:
        print(json.dumps({"ok": True, "configured": len(observations)}, ensure_ascii=False))
        return 0
    result = post_observations(
        args.origin,
        os.getenv("PRESENCE_INGEST_TOKEN", ""),
        observations,
    )
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:240]}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc
