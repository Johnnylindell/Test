#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "photos" / "generated"

PROMPTS = {
    "morgonhall-smart-knapp": "Photorealistic Scandinavian family apartment hallway in soft winter morning light, school bags, small shoes, jackets, a subtle smart wall button near the door, warm practical atmosphere, editorial interior photography, no readable text, no logos, no brand names",
    "familjedashboard-kok": "Photorealistic Scandinavian family kitchen with a wall mounted tablet dashboard, screen content blurred into simple colored blocks and icons with no readable text, groceries and family objects on counter, natural daylight, no logos",
    "lackage-diskmaskin-sensor": "Photorealistic close-up under a Scandinavian kitchen dishwasher, small white water leak sensor on the floor, clean realistic home environment, safety focused, no readable text, no logos",
    "tvattstuga-sensor": "Photorealistic Nordic laundry room with washing machine, laundry baskets, small leak sensor near the floor, soft utility lighting, tidy but lived-in family home, no readable text, no logos",
    "hub-sensorer-bord": "Photorealistic cozy Scandinavian home office corner with a small smart home hub, USB dongle, a few unbranded sensors and smart buttons on a wooden desk, laptop screen blurred, warm desk lamp, no readable text, no logos",
    "barnrum-varmt-nattljus": "Photorealistic Scandinavian child bedroom at bedtime, dim warm smart lamp, small motion sensor on shelf, cozy bedding, curtains partly closed, calm evening atmosphere, no readable text, no logos, no cartoon characters",
    "robotdammsugare-kok-hall": "Photorealistic Scandinavian family kitchen and hallway floor, robot vacuum cleaning crumbs after breakfast, shoes and school bags neatly to the side, realistic lived-in home, no readable text, no logos",
    "ytterdorr-smart-las-sensor": "Photorealistic Scandinavian apartment entrance door with a discreet unbranded smart lock and small door sensor, shoes and coat rack nearby, secure but welcoming mood, no readable text, no logos",
    "brandvarnare-hall": "Photorealistic Scandinavian hallway ceiling with a clean smoke detector, warm family home below with coats and soft lighting, safety focused editorial photo, no readable text, no logos",
    "startpaket-smart-hem": "Photorealistic Nordic kitchen table with an unbranded smart home starter kit: small button, smart bulb, motion sensor, smart plug, simple hub, family apartment background, natural light, no readable text, no logos",
}


def slugify(text: str) -> str:
    text = text.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def fetch(name: str, prompt: str, seed: int, width: int = 1024, height: int = 576) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{slugify(name)}.jpg"
    url = "https://image.pollinations.ai/prompt/" + quote(prompt) + f"?width={width}&height={height}&seed={seed}&nologo=true&private=true&enhance=true"
    req = Request(url, headers={"User-Agent": "SmartFamiljHemma/1.0"})
    with urlopen(req, timeout=90) as r:
        data = r.read()
    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError(f"Unexpected response for {name}: {data[:80]!r}")
    target.write_bytes(data)
    return target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="Prompt name, or omit with --all")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seed", type=int, default=20260708)
    args = ap.parse_args()
    items = PROMPTS.items() if args.all else [(args.name, PROMPTS[args.name])]
    for i, (name, prompt) in enumerate(items):
        path = fetch(name, prompt, args.seed + i)
        print(path)
        time.sleep(2)


if __name__ == "__main__":
    main()
