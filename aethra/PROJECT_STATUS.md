# Aethra project status — v0.18

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

## Still required for a complete shipping MMO
- Production-quality balance/animation/presentation pass across all 27 classes.
- Full inventory, item escrow/trade, market/mail and robust economy tooling.
- Production character/creature skeletal meshes, rigs, animation libraries, VFX, materials and UI art.
- Full homeland/frontier geography, exploration, story chains, dungeons, world bosses and dynamic-event depth.
- Housing/guild halls, deeper guild permissions/alliance campaigns and keep ownership systems.
- Account/backend persistence, server fleet/orchestration, anti-cheat and live-operations/admin tooling.
- Final score, complete SFX/VO pipeline, localization, accessibility/settings, patching/installer and shipping QA.

## Verification boundary
The complete static/regression suite through v0.18 passes. Unreal Engine 5.8 / UnrealBuildTool is not installed in the execution environment, so actual UE compilation, cooked builds and runtime playtests remain externally unverified.