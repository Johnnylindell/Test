# Aethra MMORPG — transport branch

This subtree is the isolated GitHub transport/publishing area for **Aethra**, a three-realm PvE + RvRvR MMORPG prototype inspired by the realm-war DNA of classic MMORPGs and built as an original world/game.

Current source milestone: **v0.11 — War Session + Release Content + Audio Pipeline**.

## GitHub safety

This lives only on branch `agent/aethra-mmorpg`. The repository's existing Smart Familj Hemma project on `main` is unrelated and must not be overwritten or merged with Aethra. A dedicated `Aethra` repository should replace this temporary transport branch when repository creation / Git LFS is available.

## Included here

- `packages/aethra-source-v0.11.zip` — UE 5.8 C++ source, configs, data catalogs, scripts, docs, proxy mesh sources and asset-import tooling.
- `PROJECT_STATUS.md` — implemented vs remaining production scope.
- `PACKAGE_SHA256.txt` — hashes for source, audio, concept-art and complete local packages.

## Large source assets

Original procedural music/SFX and the concept-art PNGs are maintained as separate source packages because this connector does not expose Git LFS or streamed binary upload. Their hashes are recorded here so the packages can be moved intact into a dedicated Aethra repository later.

## Current design target

- 3 realms: Veyr Dominion, Skeld, Elarin Synod
- 9 playable origin lineages
- 27 planned release classes (9 / realm)
- persistent homeland + The Scar frontier
- Ravenhold keep warfare, siege and logistics
- shared PvE/RvR dungeon The Hollow Crown
- Realm Rank, Chronicle and war-session history
- authoritative dedicated-server architecture with Replication Graph scale work

The project is not yet a shipping-complete MMO. The source milestone is intentionally explicit about unfinished production assets, content, backend services and QA.