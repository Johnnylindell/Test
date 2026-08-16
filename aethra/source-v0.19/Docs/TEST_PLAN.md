# v0.19 test plan — Inventory & Trade Escrow

## Static/regression gate

Run `python Tools/Validation/validate_v19.py` from the v0.19 overlay root. It validates JSON schemas/invariants, required source symbols and guards against unfinished placeholder code.

## Unreal compile gate

Build Editor, Client and Server targets for UE 5.8. Treat warnings involving replication, FastArray serialization, generated headers or RPC ownership as release blockers.

## Multiplayer functional cases

1. Server grants a unique item; only one replicated instance appears on the owning player.
2. Duplicate GUID grant is rejected.
3. Full inventory rejects a new grant.
4. Trade Marks cannot become negative or overflow `int32`.
5. Offering an unbound item locks it with `Trade`.
6. Bound or already locked items cannot enter escrow.
7. Editing either offer clears both acceptance flags.
8. Commit fails cleanly when either side lacks currency at final validation.
9. Commit fails cleanly when the receiving inventory would exceed slot capacity.
10. Successful commit preserves item instance GUID, maker mark, quality, durability and stat rolls.
11. Successful commit transfers Trade Marks exactly once.
12. Cancelling or destroying an open escrow unlocks all offered items.
13. Disconnect during an open trade leaves no permanent item locks.
14. Rapid repeated accept/unaccept cannot duplicate items or currency.
15. Two simultaneous trade attempts cannot lock the same item twice.

## Soak/abuse cases

- 1000 sequential trades between two bots with randomized item/currency offers.
- 50 concurrent escrow actors across 100 bots.
- Packet delay/loss simulation while offers change and accept states race.
- Forced participant destruction during each commit phase.

## Persistence gate for a later milestone

Before market/mail or production economy is enabled, the commit section must be wrapped by an idempotent persistence transaction with a durable transaction ID and audit ledger.
