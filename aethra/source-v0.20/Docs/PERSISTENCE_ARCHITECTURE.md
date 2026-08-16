# v0.20 persistence architecture

## Goal

v0.19 made item/currency mutation server-authoritative. v0.20 adds the transaction boundary needed to make those mutations recoverable and idempotent.

## Transaction flow

1. Gameplay validates the request and computes a canonical payload digest.
2. The server creates/reuses an idempotency key for the player action.
3. `Prepare` is appended durably before item/currency state is mutated.
4. The authoritative gameplay/persistence mutation executes.
5. Only after success does the coordinator append `Committed`.
6. A failed mutation appends `Aborted` after rollback.
7. A server restart replays the ledger. Any surviving `Prepared` record is recovery work; it is never guessed into a terminal state.

## Why Prepared is not automatically aborted

A process can crash after the durable inventory/database mutation succeeds but before the `Committed` journal record is written. Blindly aborting would risk compensating a transaction that already happened. Recovery therefore compares the prepared transaction ID/idempotency key with the authoritative persisted item/currency state.

## Reference provider boundary

`URHEconomyLedgerSubsystem` writes an append-only JSONL journal under `Saved/Aethra/Economy`. This is deliberately a development/single-server reference provider. It gives us:

- deterministic replay;
- monotonically increasing sequence numbers;
- idempotency-key uniqueness in one process;
- legal state-transition validation;
- crash-visible Prepared transactions.

It is not the final MMO database. Production requires an atomic replicated persistence provider with a unique idempotency constraint.

## Integration with v0.19 direct trade

The trade payload digest should cover, in canonical sorted order:

- both account/character IDs;
- both offered item instance GUID sets;
- both Trade Marks amounts;
- item quantities and immutable definition IDs;
- trade session nonce.

Prepare before extracting/crediting anything. After both inventories and balances are durably updated, commit the same transaction ID. On rollback, abort it.

## Next consumers

Market purchase, mail claim, vendor transactions, crafting consumption/output and admin grants must all go through this same coordinator contract rather than inventing separate durability rules.
