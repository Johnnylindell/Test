# Aethra MMORPG — isolated transport branch

Current milestone: **v0.19 — Inventory & Trade Escrow Foundation**.

This subtree remains isolated on branch `agent/aethra-mmorpg` under `aethra/`; the unrelated project on `main` remains untouched.

## v0.19 highlights
- All **27/27 target release class IDs** remain represented by playable six-ability prototype kits from v0.18.
- 9 playable origin lineages across Veyr, Skeld and Elarin.
- Capitals/homeland safe zones, Ravenhold frontier and shared Hollow Crown dungeon.
- Capital bounty boards, homeland elite events, Trade Marks economy, guilds/alliances, crafting, Beastmaster companion, Echo decoys and dynamic Scar weather.
- New Git-friendly `source-v0.19` overlay adds replicated unique item instances, FastArray inventory, server-owned currency guards and shared item-lock semantics.
- New two-party server trade escrow revalidates both offers, resets acceptance after changes, enforces distance/capacity and includes rollback paths.
- First v0.19 sidegrade item catalog covers all three realms plus shared frontier/PvE materials.

## Artifact handling
The v0.18 archive checksums remain recorded in `PACKAGE_SHA256.txt`, but those large v0.18 archives were not transported into GitHub before the previous run stopped. New work is therefore stored as plain text under `aethra/source-v0.19/` so the branch itself is a recoverable source of truth.

## Verification boundary
The v0.19 static validation gate passes. UnrealBuildTool / UE 5.8 cannot run in the current execution environment, so actual UE compilation and runtime multiplayer testing remain external verification steps.
