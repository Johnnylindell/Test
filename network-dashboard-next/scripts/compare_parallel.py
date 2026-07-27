from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class Contract:
    name: str
    legacy_path: str
    next_path: str
    required_next_keys: tuple[str, ...]


CONTRACTS = (
    Contract("health", "/api/health", "/api/health", ("ok",)),
    Contract("home", "/api/home", "/api/v2/home/summary", ("ok", "identity", "totals")),
    Contract("planning", "/api/preview-v2/planning", "/api/v2/planning/overview", ("ok",)),
    Contract("family", "/api/family-lists", "/api/v2/family/overview", ("ok",)),
    Contract("inventory", "/api/inventory", "/api/v2/inventory/overview", ("ok",)),
    Contract("food", "/api/preview-v2/food", "/api/v2/food/overview", ("ok",)),
    Contract("budget", "/api/preview-v2/budget", "/api/v2/budget/overview", ("ok",)),
)


def fetch(client: httpx.Client, origin: str, path: str) -> tuple[int, Any]:
    response = client.get(f"{origin.rstrip('/')}{path}")
    try:
        payload: Any = response.json()
    except ValueError:
        payload = response.text[:500]
    return response.status_code, payload


def summarize(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {
            "keys": sorted(payload)[:40],
            "ok": payload.get("ok"),
            "counts": {
                key: len(value)
                for key, value in payload.items()
                if isinstance(value, list)
            },
        }
    return {"type": type(payload).__name__, "preview": str(payload)[:160]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Jämför gamla och nya dashboardens läskontrakt.")
    parser.add_argument("--legacy", default="http://127.0.0.1:8792")
    parser.add_argument("--next", dest="next_origin", required=True)
    parser.add_argument("--cookie", action="append", default=[], help="Cookie som name=value; kan anges flera gånger.")
    parser.add_argument("--json", action="store_true", help="Skriv maskinläsbar JSON.")
    args = parser.parse_args()

    cookies = {}
    for raw in args.cookie:
        if "=" not in raw:
            parser.error("--cookie måste vara name=value")
        name, value = raw.split("=", 1)
        cookies[name] = value

    rows = []
    failures = 0
    with httpx.Client(timeout=12, cookies=cookies, follow_redirects=False) as client:
        for contract in CONTRACTS:
            legacy_status, legacy_payload = fetch(client, args.legacy, contract.legacy_path)
            next_status, next_payload = fetch(client, args.next_origin, contract.next_path)
            missing = [key for key in contract.required_next_keys if not isinstance(next_payload, dict) or key not in next_payload]
            passed = next_status == 200 and not missing
            failures += int(not passed)
            rows.append({
                "name": contract.name,
                "passed": passed,
                "legacy": {"status": legacy_status, **summarize(legacy_payload)},
                "next": {"status": next_status, **summarize(next_payload)},
                "missing_next_keys": missing,
            })

    result = {"ok": failures == 0, "failures": failures, "contracts": rows}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            mark = "OK" if row["passed"] else "FAIL"
            print(f"[{mark}] {row['name']}: legacy={row['legacy']['status']} next={row['next']['status']}")
            if row["missing_next_keys"]:
                print(f"       saknade nycklar: {', '.join(row['missing_next_keys'])}")
        print(f"\nResultat: {len(rows) - failures}/{len(rows)} kontrakt godkända")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
