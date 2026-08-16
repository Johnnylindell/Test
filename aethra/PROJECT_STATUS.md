# Aethra project status — v0.19

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
- **v0.19:** Git-friendly source overlay adds FastArray inventory replication, unique persistent item instances, Trade Marks guards, shared item locks and two-party server trade escrow with rollback paths.
- **v0.19:** First data-driven sidegrade item catalog covers Veyr, Skeld, Elarin and shared frontier/PvE materials.

## Still required for a complete shipping MMO
- Production-quality balance/animation/presentation pass across all 27 classes.
- Persistence-backed inventory transactions, partial-stack escrow, market/mail, offline delivery and economy/admin tooling.
- Production character/creature skeletal meshes, rigs, animation libraries, VFX, materials and UI art.
- Full homeland/frontier geography, exploration, story chains, dungeons, world bosses and dynamic-event depth.
- Housing/guild halls, deeper guild permissions/alliance campaigns and keep ownership systems.
- Account/backend persistence, server fleet/orchestration, anti-cheat and live-operations/admin tooling.
- Final score, complete SFX/VO pipeline, localization, accessibility/settings, patching/installer and shipping QA.

## Recovery / transport note
The previous run recorded SHA-256 hashes for the v0.18 source/full archives but did not successfully transport those large archives into GitHub. v0.19 therefore keeps the v0.18 checksum as its explicit baseline and stores the new source as plain text under `aethra/source-v0.19/` so future work is recoverable directly from Git.

## Verification boundary
The v0.19 static validator passes. Unreal Engine 5.8 / UnrealBuildTool is not installed in the execution environment, so actual UE compilation, cooked builds and runtime multiplayer playtests remain externally unverified.
