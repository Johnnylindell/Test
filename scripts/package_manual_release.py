#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = ROOT / "dist"


def build(env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(["python3", "scripts/build_site.py"], cwd=ROOT, env=merged, check=True)


def main() -> None:
    version = time.strftime("%Y%m%d-%H%M")
    DIST.mkdir(parents=True, exist_ok=True)
    archive_base = DIST / f"smart-familj-hemma-release-{version}"

    # Build a domain-root version for manual Netlify/Cloudflare drag-and-drop.
    build({"BASE_PATH": "", "SITE_URL": "https://smarthahem.netlify.app"})
    archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=SITE))

    # Restore committed/local preview output for the GitHub Pages project path.
    build(
        {
            "BASE_PATH": "/Test",
            "SITE_URL": "https://johnnylindell.github.io/Test",
        }
    )

    print(archive)


if __name__ == "__main__":
    main()
