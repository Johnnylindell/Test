#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    ROOT / "Data/Economy/transaction_policy.json",
    ROOT / "Docs/PERSISTENCE_ARCHITECTURE.md",
    ROOT / "Docs/RECOVERY_TEST_PLAN.md",
    ROOT / "Source/Ravenhold/Public/RHEconomyTransactionTypes.h",
    ROOT / "Source/Ravenhold/Public/RHEconomyLedgerSubsystem.h",
    ROOT / "Source/Ravenhold/Private/RHEconomyLedgerSubsystem.cpp",
    ROOT / "Source/Ravenhold/Public/RHEconomyTransactionCoordinator.h",
    ROOT / "Source/Ravenhold/Private/RHEconomyTransactionCoordinator.cpp",
]


def die(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    if missing:
        die("missing: " + ", ".join(missing))

    policy = json.loads((ROOT / "Data/Economy/transaction_policy.json").read_text(encoding="utf-8"))
    contract = policy["transaction_contract"]
    recovery = policy["recovery"]
    provider = policy["reference_provider"]

    if not contract["write_ahead_prepare_required"] or not contract["idempotency_key_required"] or not contract["payload_digest_required"]:
        die("core transaction invariants disabled")
    if set(contract["terminal_states"]) != {"committed", "aborted"}:
        die("terminal states changed")
    if set(contract["valid_transitions"]) != {"prepared->committed", "prepared->aborted"}:
        die("state transitions changed")
    if recovery["auto_commit_on_restart"] or recovery["auto_abort_on_restart"]:
        die("recovery must reconcile rather than guess")
    if provider["production_cluster_ready"]:
        die("reference JSONL provider must not claim production cluster readiness")

    source = "\n".join(path.read_text(encoding="utf-8") for path in REQUIRED if path.suffix in {".h", ".cpp"})
    symbols = [
        "FCriticalSection",
        "FScopeLock",
        "IdempotencyKey",
        "PayloadDigest",
        "Prepared",
        "Committed",
        "Aborted",
        "ReplayLedger",
        "FILEWRITE_Append",
        "terminal_transaction_mutated",
        "idempotency_key_payload_mismatch",
    ]
    for symbol in symbols:
        if symbol not in source:
            die(f"missing invariant/symbol: {symbol}")

    for token in ("TODO", "FIXME", "IPSIZATION"):
        if token in source:
            die(f"unfinished marker: {token}")

    print("PASS: Aethra v0.20 persistence/idempotency static gate")


if __name__ == "__main__":
    main()
