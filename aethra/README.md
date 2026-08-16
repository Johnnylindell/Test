# Aethra MMORPG — isolated development branch

Current milestone: **v0.20 — Durable Economy Transactions & Recovery Foundation**.

The project is temporarily staged under `aethra/` on `agent/aethra-mmorpg` while the dedicated private Aethra repository is connected to the GitHub App.

## v0.20 highlights
- Existing 27-class prototype roster, three realms, PvE/RvR foundations, guild/crafting systems, audio source pipeline and dynamic frontier weather remain the gameplay baseline.
- v0.19 added replicated persistent item identity, FastArray inventory and server-owned direct trade escrow.
- v0.20 adds write-ahead transaction journaling, idempotency-key enforcement, crash replay and explicit recovery semantics for economy mutations.
- A UE 5.8 Windows self-hosted Actions workflow is staged under `source-v0.20/ci/` and will be activated in the dedicated repository once its runner is reachable.

## Verification boundary
Static gates are available without Unreal. UE compilation/runtime verification will move into GitHub Actions as soon as the new repository/runner permissions are visible through the integration.
