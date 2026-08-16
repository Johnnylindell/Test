# Aethra v0.20 source overlay

Milestone: **Durable Economy Transactions & Recovery Foundation**.

Built on the v0.19 inventory/trade overlay. v0.20 introduces the write-ahead transaction contract needed before market, mail and offline economy are allowed to mutate persistent items/currency.

## Added

- Durable append-only reference transaction ledger.
- `Prepared -> Committed/Aborted` state machine with illegal transition rejection.
- Idempotency keys and payload-digest matching.
- Crash replay with contiguous sequence validation.
- Unresolved Prepared transactions explicitly surfaced as recovery work rather than guessed.
- Thread-safe in-process ledger coordination.
- Shared transaction coordinator intended for trade, vendors, crafting, market, mail and admin economy actions.
- Recovery/idempotency test matrix.
- Staged GitHub Actions workflow for a Windows self-hosted UE 5.8 runner.

## Important boundary

The JSONL provider is intentionally a reference/single-process implementation. It must be replaced by an atomic replicated database provider before production-scale persistent economy or cross-server market/mail is enabled.
