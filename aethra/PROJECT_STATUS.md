# Aethra project status — v0.20

## Implemented
- Authoritative three-realm multiplayer combat and server-owned ability outcomes.
- **27/27 planned release class IDs have playable six-ability prototype kits.**
- 9 playable origin lineages across Veyr, Skeld and Elarin.
- Ravenhold capture, supply lines, caravans, forward camps, ram/ballista siege and guild claims.
- Shared Hollow Crown PvE/RvR dungeon with Sentinels, phased Hollow Warden and Loom Shards.
- Realm Points / Realm Rank, Chronicle, commander/scout intel, war-session flow and server metrics.
- Replication Graph, scale-bot harness, presentation/readability LOD and UMG combat HUD.
- Capitals Caer Veyr, Hrafnheim and Ilyr; safe homeland PvP rules and realm-locked frontier travel.
- Homeland PvE, capital bounty boards, recurring realm elite events, Trade Marks and capital vendor foundation.
- Guilds/alliances, maker-mark crafting, persistent crafted item identity and capped sidegrade gear power.
- Nearby server-validated Trade Marks transfer foundation.
- Echo replicated decoys and Beastmaster replicated companion.
- Replicated dynamic weather in The Scar; fog/rain/storm alter scout range without changing hit authority.
- Original procedural music/SFX source pipeline and growing original OBJ proxy/source-asset library.
- **v0.19:** FastArray inventory, unique item instances, Trade Marks guards, shared item locks and two-party trade escrow.
- **v0.20:** Write-ahead economy transaction ledger, idempotency keys, legal state transitions, crash replay and recovery contract.
- **v0.20:** UE 5.8 self-hosted GitHub Actions build workflow staged for the dedicated private Aethra repository.

## Still required for a complete shipping MMO
- Production-quality balance/animation/presentation pass across all 27 classes.
- Production database adapter, authoritative inventory snapshots, partial-stack escrow, market/mail and offline delivery.
- Production character/creature skeletal meshes, rigs, animation libraries, VFX, materials and UI art.
- Full homeland/frontier geography, exploration, story chains, dungeons, world bosses and dynamic-event depth.
- Housing/guild halls, deeper guild permissions/alliance campaigns and keep ownership systems.
- Account/backend persistence, server fleet/orchestration, anti-cheat and live-operations/admin tooling.
- Final score, complete SFX/VO pipeline, localization, accessibility/settings, patching/installer and shipping QA.

## Repository/runner status
The dedicated repository was not yet visible through the connected GitHub App when v0.20 was staged. Development therefore remains temporarily isolated on `agent/aethra-mmorpg` until the new repository permission is available.

## Verification boundary
v0.20 has a static validation gate and a UE 5.8 CI workflow ready to activate. Actual Unreal compilation begins once the dedicated repository and self-hosted runner are visible to the GitHub integration.
