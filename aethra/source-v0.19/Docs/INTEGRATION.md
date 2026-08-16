# v0.19 integration notes

This overlay targets the checksum-recorded `aethra-source-v0.18.zip` baseline and the existing `Ravenhold` Unreal module.

## Wiring

1. Copy `Source/Ravenhold/Public/*.h` and `Source/Ravenhold/Private/*.cpp` into the v0.18 Ravenhold module.
2. Add `URHInventoryComponent` to the persistent player-owned actor. Prefer the existing `ARHPlayerState` so inventory survives pawn death/respawn and realm travel.
3. Spawn `ARHTradeEscrow` on the authoritative server only after both participants pass proximity, realm/social and session checks.
4. Route client UI requests through the existing server-owned interaction/controller layer. The escrow methods in this overlay are server primitives and should not be exposed as trust-the-client mutation endpoints.
5. Load `Data/Items/item_catalog.json` into the content/data import layer and enforce the sidegrade stat budget during item creation.

## Security and integrity rules

- Item instance GUIDs are server-created and immutable.
- Currency is integer-only and server-owned.
- An item locked for trade cannot be destroyed, mailed, marketed or crafted.
- Changing either offer resets both acceptance flags.
- Both offers are revalidated immediately before commit.
- Disconnect/destruction cancels an open trade and releases trade locks.
- Market/mail must reuse the same lock model with distinct lock reasons rather than adding client-side reservation flags.

## Known v0.19 boundary

The direct trade prototype transfers whole item instances. Partial-stack escrow, persistence-backed transactions, market listings, mail attachments and offline delivery remain later economy milestones.
