#!/usr/bin/env python3
from pathlib import Path
import json
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
links = json.loads((ROOT / "data" / "affiliate_links.json").read_text(encoding="utf-8"))
programs = json.loads((ROOT / "data" / "affiliate_programs.json").read_text(encoding="utf-8"))

broken = []
for key, item in links.items():
    url = item.get("url", "")
    parsed = urlparse(url)
    tag = parse_qs(parsed.query).get("tag", [""])[0]
    if item.get("status") != "active" or parsed.scheme != "https" or not parsed.netloc or not tag:
        broken.append((key, item))

amazon = next((item for item in programs if item.get("name", "").startswith("Amazon Associates")), {})
print("# Affiliate-status")
print()
if broken:
    print(f"{len(broken)} länkkategorier saknar aktiv status, giltig HTTPS-URL eller tracking-ID:")
    for key, item in broken:
        print(f"- {key}: {item.get('url', 'länk saknas')}")
else:
    print(f"{len(links)} länkkategorier är tekniskt konfigurerade med tracking-ID.")

if amazon.get("status") in {"needs_user_signup", "research_needed", "configured_unverified"}:
    print("Amazon-kontots godkännande och registrerad webbplats kan inte verifieras från repot.")
    print("Kontrollera Amazon Associates manuellt innan länkarna beskrivs som intäktsaktiva.")
else:
    print(f"Programstatus i datafilen: {amazon.get('status', 'saknas')}")

print("Detta test verifierar URL-format och märkning, inte klickspårning, kontoägande eller utbetalning.")

if broken:
    raise SystemExit(1)
