# v0.20 recovery and idempotency test plan

## Ledger invariants

1. First record for a transaction must be `Prepared`.
2. Only `Prepared -> Committed` and `Prepared -> Aborted` are legal.
3. A terminal transaction can never change state again.
4. An idempotency key can map to only one transaction ID.
5. Reusing an idempotency key with a different payload fails.
6. Reusing an existing matching idempotency key returns the existing transaction result.
7. Ledger sequence is contiguous from 1..N.
8. A malformed/gapped ledger starts unhealthy and blocks economy mutations.

## Crash injection matrix

For direct trade, kill the dedicated server after each stage:

- before Prepare;
- immediately after Prepare;
- after source item extraction;
- after currency debit;
- after destination item grant;
- after authoritative persistence commit;
- immediately before ledger Commit;
- immediately after ledger Commit.

After restart, assert that replay classifies unresolved Prepared records for reconciliation and never duplicates items/currency.

## Idempotency abuse

- Send the same client action 100 times with the same key and payload.
- Send the same key with a modified amount/item list.
- Race the same key from two server worker threads.
- Re-submit a committed transaction after reconnect.
- Re-submit an aborted transaction after reconnect.

## Production provider gate

Before enabling persistent market/mail in a public environment, replace the JSONL provider with a transactional database adapter and rerun the same semantic test suite against it.
