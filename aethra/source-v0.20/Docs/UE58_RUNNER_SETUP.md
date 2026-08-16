# UE 5.8 self-hosted runner contract

When the dedicated Aethra repository and Windows runner are available, copy `ci/ue58-self-hosted.yml` to `.github/workflows/ue58-ci.yml`.

The workflow expects these runner labels:

- `self-hosted`
- `Windows`
- `X64`
- `unreal-5.8` (custom)

It expects a launcher/source installation at `C:\Program Files\Epic Games\UE_5.8`. Change `UE_ROOT` if the engine is installed elsewhere.

The job discovers the `.uproject` dynamically, runs the v0.20 static validator, builds the Editor target and then the dedicated Server target. Failed builds upload Unreal logs/crash files as workflow artifacts so they can be inspected through GitHub.

Do not activate this workflow in an unrelated repository; it is staged here only for migration into the dedicated private Aethra repository.
