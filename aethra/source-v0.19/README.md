# Aethra v0.19 source overlay

Milestone: **Inventory & Trade Escrow Foundation**.

This is an uncompressed, Git-friendly source overlay for the checksum-recorded v0.18 baseline. It exists because the previous run recorded the v0.18 package checksums but did not successfully transport the large v0.18 archives into GitHub.

## Added in v0.19

- Replicated persistent item instances with immutable GUID identity.
- FastArray-based inventory replication for MMO-friendly delta updates.
- Server-owned Trade Marks balance operations with overflow/underflow guards.
- Shared item lock states for trade/market/mail/crafting reservation semantics.
- Two-party server trade escrow with offer revalidation, acceptance reset and rollback paths.
- First data-driven sidegrade item catalog spanning Veyr, Skeld, Elarin and frontier/shared content.
- Static milestone validator and multiplayer test plan.

## Verification boundary

The static validator can run without Unreal Engine. UE 5.8 compilation, cooking and runtime multiplayer verification still require an Unreal-equipped environment.
