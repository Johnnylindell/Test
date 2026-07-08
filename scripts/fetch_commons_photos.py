#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import time

ROOT = Path(__file__).resolve().parent.parent
out = ROOT / "assets" / "photos"
out.mkdir(parents=True, exist_ok=True)
queries = {
    "commons-co2-monitor.jpg": "carbon dioxide monitor indoor",
    "commons-smoke-detector.jpg": "smoke detector ceiling",
    "commons-smart-lock.jpg": "electronic door lock",
    "commons-thermostat.jpg": "radiator thermostat",
    "commons-window-sensor.jpg": "door contact sensor",
    "commons-mailbox.jpg": "mailbox letterbox",
    "commons-garage-door.jpg": "garage door interior",
    "commons-roller-blinds.jpg": "roller blinds window",
    "commons-zigbee-device.jpg": "smart home hub",
    "commons-air-quality.jpg": "air quality monitor",
}
credits = []
for filename, search in queries.items():
    target = out / filename
    if target.exists() and target.stat().st_size > 5000:
        credits.append({"file": filename, "search": search, "source": "already downloaded"})
        continue
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": search,
        "gsrnamespace": "6",
        "gsrlimit": "8",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1200",
        "format": "json",
    }
    api = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    req = Request(api, headers={"User-Agent": "SmartFamiljHemma/1.0"})
    data = json.load(urlopen(req, timeout=30))
    pages = list(data.get("query", {}).get("pages", {}).values())
    chosen = None
    for page in sorted(pages, key=lambda p: p.get("index", 999)):
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        # avoid SVG thumbnails when possible
        if ".svg" in url.lower():
            continue
        chosen = (page, info, url)
        break
    if not chosen:
        print("NO_IMAGE", filename, search)
        continue
    page, info, url = chosen
    try:
        img_req = Request(url, headers={"User-Agent": "SmartFamiljHemma/1.0"})
        with urlopen(img_req, timeout=60) as r:
            blob = r.read()
    except Exception as exc:
        print("DOWNLOAD_FAILED", filename, search, exc)
        time.sleep(3)
        continue
    target.write_bytes(blob)
    meta = info.get("extmetadata", {})
    credits.append({
        "file": filename,
        "search": search,
        "title": page.get("title"),
        "source_url": info.get("descriptionurl"),
        "license": (meta.get("LicenseShortName") or {}).get("value", ""),
        "artist": (meta.get("Artist") or {}).get("value", ""),
    })
    print("downloaded", filename, len(blob), page.get("title"))
    time.sleep(2)
(Path(ROOT / "assets" / "photos" / "commons-credits.json")).write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("credits", len(credits))
