# Aethra MMORPG — isolated transport branch

Current milestone: **v0.18 — Full 27-Class Prototype Roster + Dynamic Weather**.

This subtree remains isolated on branch `agent/aethra-mmorpg` under `aethra/`; the unrelated project on `main` remains untouched.

## v0.18 highlights
- All **27/27 target release class IDs** now have playable six-ability prototype combat kits.
- 9 playable origin lineages across Veyr, Skeld and Elarin.
- Capitals/homeland safe zones, Ravenhold frontier and shared Hollow Crown dungeon.
- Capital bounty boards, homeland elite events, Trade Marks economy and nearby server-validated currency transfer.
- Guilds, alliances, maker-mark crafting and Ravenhold guild claims.
- Beastmaster replicated companion and Echo replicated decoys.
- Replicated dynamic weather over The Scar; fog/rain/storm reduce server scout range without altering combat hit authority.
- Original procedural music/SFX and growing original OBJ source-asset library.

## Artifact handling
The complete v0.18 and source-only v0.18 ZIPs are checksum-recorded in `PACKAGE_SHA256.txt`. The temporary GitHub connector does not expose Git LFS/local-file streaming, so large binaries remain external artifacts until Aethra has a dedicated repository with LFS.

## Important verification boundary
UnrealBuildTool / UE 5.8 cannot run in the current execution environment. v0.18 passes the full static/regression suite, but actual UE compilation and runtime playtest remain external verification steps.