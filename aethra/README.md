# Aethra MMORPG — transport branch

Temporary isolated publishing area for **Aethra**, an original three-realm PvE + RvRvR MMORPG project.

Current source milestone: **v0.12 — Character Identity + Nine Playable Classes**.

## Safety
This content exists only on branch `agent/aethra-mmorpg` under `aethra/`. The unrelated project on `main` is not modified. Do not merge this subtree into the unrelated site; move it to a dedicated Aethra repository when repository creation / Git LFS is available.

## Latest source package
- `packages/aethra-source-v0.12.zip` — UE 5.8 C++ source/config/data/scripts/docs, custom proxy mesh sources and asset-import tooling.
- v0.12 adds persistent server-validated realm/origin/class selection and first-pass six-ability kits for Templar, Huntsman and Lifebinder.
- Stable IDs are now reserved for all 27 planned release classes; 9 are currently playable.

## Large source assets
Original procedural music/SFX and generated concept-art source images remain separate packages because the current GitHub connector does not expose Git LFS/streamed binary uploads. Their hashes are recorded in `PACKAGE_SHA256.txt` so the source sets can be moved without ambiguity later.

## Current systems
- 3 realms: Veyr Dominion / Skeld / Elarin Synod
- 9 origin lineages
- 9 playable classes, 27 target class IDs
- Ravenhold persistent-war vertical slice with siege/logistics
- shared Hollow Crown PvE/RvR dungeon
- Realm Rank, Chronicle, 90-minute war-session loop
- authoritative server model, Replication Graph and scale harness
- runtime UMG, combat telegraphs and adaptive original audio pipeline

This is not yet a shipping-complete MMO; `PROJECT_STATUS.md` deliberately lists remaining production work.