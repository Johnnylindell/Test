#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parent.parent
out = ROOT / "assets" / "photos"
out.mkdir(parents=True, exist_ok=True)
# Deterministic placeholder photography seeds. Local files make the Netlify build self-contained.
files = [
  "family-living.jpg", "tablet-kitchen.jpg", "morning-hall.jpg", "kids-bedroom.jpg", "switch-wall.jpg",
  "family-calendar.jpg", "bedroom-night.jpg", "grocery-kitchen.jpg", "phone-table.jpg", "robot-floor.jpg",
  "weekly-planner.jpg", "messy-table.jpg", "budget-home.jpg", "hub-table.jpg", "water-sink.jpg",
  "laundry-sensor.jpg", "smart-plug.jpg", "smart-bulbs.jpg", "apartment.jpg", "green-pi.jpg",
  "night-light.jpg", "dog-hall.jpg", "shopping-basket.jpg", "school-bag.jpg", "zigbee-desk.jpg"
]
for name in files:
    path = out / name
    if path.exists() and path.stat().st_size > 5000:
        continue
    url = f"https://picsum.photos/seed/smart-family-{name}/1200/800"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as r:
        data = r.read()
    path.write_bytes(data)
    print(name, len(data))
