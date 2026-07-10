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
    "inkopslista-kyl": "Photorealistic Scandinavian family kitchen refrigerator with a small unbranded wall tablet beside it showing blurred checklist blocks, grocery bag and milk on counter, natural afternoon light, editorial home photography, no readable text, no logos",
    "smart-knapp-narbild": "Photorealistic close-up of a hand pressing a small plain unbranded smart button mounted beside a Scandinavian hallway light switch, coat and school bag softly blurred in background, natural light, realistic hand anatomy, no readable text, no logos",
    "energiplugg-kok": "Photorealistic Scandinavian kitchen counter with a compact unbranded energy monitoring smart plug safely connected to a small coffee machine, phone screen blurred in background, clean realistic electrical setup, no readable text, no logos",
    "luftsensor-barnrum": "Photorealistic Nordic child bedroom in daylight with a small unbranded air quality sensor on a shelf beside books and plant, window slightly open, calm lived-in room, no readable display text, no logos",
    "gardiner-morgonljus": "Photorealistic Scandinavian child bedroom in early morning, motorized blackout curtains partly opening to soft daylight, tidy bed and simple wooden furniture, no people, no readable text, no logos",
    "sommarstuga-sensor": "Photorealistic modest Nordic summer cottage interior with wooden walls, small unbranded temperature sensor and radiator, rainy lake visible through window, realistic editorial photography, no readable text, no logos",
    "regnig-hall-tvatt": "Photorealistic Scandinavian family hallway on a rainy day with wet boots, rain jackets and drying rack, discreet humidity sensor on shelf, practical lived-in atmosphere, no readable text, no logos",
    "medicinpaminnelse-kok": "Photorealistic Scandinavian kitchen shelf with a simple weekly pill organizer, small warm reminder light and phone with blurred notification, responsible adult medication routine, no readable text, no logos",
    "dorrsensor-brevlada": "Photorealistic Nordic apartment hallway close-up with a discreet small door contact sensor on the front door frame, mail on a side table, soft natural light, no readable text, no logos",
    "hund-hall-sensor": "Photorealistic Scandinavian home hallway with a calm medium-sized dog by the door, leash and towel nearby, small unbranded door sensor, warm natural light, no readable text, no logos",
    "termostat-vinter": "Photorealistic Nordic living room in winter with snow outside, discreet unbranded smart radiator thermostat in foreground, wool blanket and warm lamp, no readable text, no logos",
    "brandvarnare-kok": "Photorealistic Scandinavian open-plan kitchen ceiling with a clean smoke detector visible, family breakfast setting below, bright safe everyday home, no smoke or fire, no readable text, no logos",
    "hubb-pa-hylla": "Photorealistic Scandinavian living room shelf with a small plain unbranded smart home hub, Zigbee USB radio on a short extension cable, books and warm lamp nearby, realistic editorial photography, no readable text, no logos",
    "zigbee-mesh-lagenhet": "Photorealistic Nordic apartment hallway opening into living room, discreet unbranded smart plug in hallway and small lamp in next room, warm evening light, illustrates connected rooms without diagrams, no readable text, no logos",
    "backup-desk-usb": "Photorealistic Scandinavian home office desk with a small unbranded home server, external USB backup drive and handwritten blank notebook, tidy cables, soft daylight, no readable text, no logos",
    "budgetprylar-bord": "Photorealistic Nordic dining table with three affordable unbranded smart home items separated clearly: smart plug, motion sensor and physical button, receipt turned face down, realistic daylight, no readable text, no logos",
    "lokalt-natverk-router": "Photorealistic Scandinavian home office shelf with an unbranded wifi router, small local smart home hub and ethernet cable, internet outage mood with laptop screen dark, warm room lighting, no readable text, no logos",
    "temperatursensor-frys": "Photorealistic Scandinavian kitchen freezer drawer slightly open with a small unbranded temperature sensor safely placed nearby, ordinary family kitchen, cool clean light, no readable text, no logos",
    "veckoplan-magnetkort": "Photorealistic Scandinavian family kitchen wall with seven blank colored magnetic cards arranged as a weekly plan, absolutely no letters or numbers, school bag and fruit bowl nearby, natural daylight, editorial home photography, no logos",
    "inkopslista-hogtalare": "Photorealistic Scandinavian kitchen counter with grocery bag, milk, bread and vegetables beside a small plain unbranded voice speaker, family home in natural daylight, no screens, no readable text, no logos",
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
