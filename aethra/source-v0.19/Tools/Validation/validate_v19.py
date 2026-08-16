#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    ROOT / "patch_manifest.json",
    ROOT / "Data/Economy/economy_rules.json",
    ROOT / "Data/Items/item_catalog.json",
    ROOT / "Source/Ravenhold/Public/RHItemTypes.h",
    ROOT / "Source/Ravenhold/Public/RHInventoryComponent.h",
    ROOT / "Source/Ravenhold/Private/RHInventoryComponent.cpp",
    ROOT / "Source/Ravenhold/Public/RHTradeEscrow.h",
    ROOT / "Source/Ravenhold/Private/RHTradeEscrow.cpp",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)}: {exc}")


def main() -> None:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    manifest = load_json(ROOT / "patch_manifest.json")
    if manifest.get("milestone") != "v0.19":
        fail("manifest milestone must be v0.19")
    if len(manifest.get("baseline", {}).get("sha256", "")) != 64:
        fail("baseline SHA-256 must be present")

    economy = load_json(ROOT / "Data/Economy/economy_rules.json")
    inventory = economy.get("inventory", {})
    trade = economy.get("trade", {})
    currency = economy.get("currency", {}).get("trade_marks", {})
    if not (1 <= inventory.get("default_slots", 0) <= inventory.get("hard_slot_cap", 0) <= 256):
        fail("inventory slot limits are invalid")
    if not trade.get("requires_both_accept") or not trade.get("reset_acceptance_on_offer_change"):
        fail("trade acceptance invariants must stay enabled")
    if currency.get("negative_balance_allowed") is not False:
        fail("Trade Marks must not allow negative balances")

    catalog = load_json(ROOT / "Data/Items/item_catalog.json")
    items = catalog.get("items", [])
    ids = [item.get("id") for item in items]
    if len(items) < 9 or len(ids) != len(set(ids)) or any(not item_id for item_id in ids):
        fail("item catalog requires at least 9 unique non-empty IDs")
    realms = {item.get("realm_affinity") for item in items}
    if not {"Veyr", "Skeld", "Elarin", "Any"}.issubset(realms):
        fail("catalog must cover all three realms and shared items")

    item_types = (ROOT / "Source/Ravenhold/Public/RHItemTypes.h").read_text(encoding="utf-8")
    inventory_h = (ROOT / "Source/Ravenhold/Public/RHInventoryComponent.h").read_text(encoding="utf-8")
    inventory_cpp = (ROOT / "Source/Ravenhold/Private/RHInventoryComponent.cpp").read_text(encoding="utf-8")
    trade_cpp = (ROOT / "Source/Ravenhold/Private/RHTradeEscrow.cpp").read_text(encoding="utf-8")
    combined = "\n".join([item_types, inventory_h, inventory_cpp, trade_cpp])

    required_symbols = [
        "FFastArraySerializer",
        "InstanceId",
        "ERHItemLockReason::Trade",
        "ServerExtractLockedItem",
        "CanCreditTradeMarks",
        "ResetAcceptances",
        "ValidateOffer",
        "RollbackCommit",
        "DOREPLIFETIME",
    ]
    for symbol in required_symbols:
        if symbol not in combined:
            fail(f"required source invariant missing: {symbol}")

    forbidden = ["TODO", "FIXME", "return false; // Replaced", "IPSIZATION"]
    for token in forbidden:
        if token in combined:
            fail(f"unfinished source marker found: {token}")

    print(f"PASS: Aethra v0.19 static gate ({len(items)} catalog items, {len(REQUIRED)} required files)")


if __name__ == "__main__":
    main()
