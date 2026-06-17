#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

IDEAS = [
    ("Bästa Zigbee-hubbar för barnfamiljer", "köpguide", "Jämför hubbar utifrån stabilitet, lokal kontroll och enkelhet."),
    ("Så gör du en läggdagsrutin med smarta lampor", "rutiner", "Praktisk guide med kvällsljus, checklista och knapp."),
    ("Billigt smart hem: startpaket under 100 euro", "köpguide", "Perfekt match för låg startbudget och affiliate."),
    ("Home Assistant vs Apple Home vs Google Home för familjer", "jämförelse", "Sökintention: välja plattform."),
    ("Smarta sensorer som faktiskt hjälper i vardagen", "köpguide", "Rörelse, dörr, temperatur och vattenläckage."),
    ("Så bygger du en skoldags-checklista på väggskärm", "dashboard", "Barnvänlig rutin med tydlig klar-signal."),
    ("Robotdammsugare med självtömning: värt priset?", "köpguide", "Hög order value; bra affiliate-kandidat."),
]


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = REPORTS / f"weekly-ideas-{today}.md"
    lines = [f"# Veckorapport / artikelidéer {today}", "", "## Nästa rekommenderade artiklar", ""]
    for title, category, why in IDEAS:
        lines.append(f"- **{title}** ({category}) — {why}")
    lines += [
        "",
        "## Monetiseringssteg",
        "",
        "1. Välj affiliateprogram: Amazon/Adtraction/nordisk butik.",
        "2. Byt placeholders i `data/products.json` efter godkännande.",
        "3. Publicera till GitHub Pages eller Cloudflare Pages efter godkännande.",
        "4. Skapa första digitala produkten: Family Dashboard Template.",
        "",
        "## Approval behövs innan externa steg",
        "",
        "- riktiga affiliate-länkar",
        "- publicering",
        "- domänköp",
        "- annonser/outreach",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
