#!/usr/bin/env python3
"""One-time editorial correction of model categories found in the July 2026 audit."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
pp = ROOT / "data" / "products.json"
products = json.loads(pp.read_text(encoding="utf-8"))
by_id = {p["id"]: p for p in products}

for product in products:
    product.setdefault("models_verified_at", "2026-07-10")
    product.setdefault(
        "selection_basis",
        "Modeller valda för nordisk tillgänglighet, tydlig kompatibilitet och praktisk familjeanvändning; inget laboratorietest.",
    )

by_id["zigbee-hub"]["models"][0] = {
    "name": "Home Assistant Green + Connect ZBT-2",
    "good": "lokal Home Assistant-start med aktuell officiell Zigbee/Thread-adapter",
    "watch": "ZBT-2 kör antingen Zigbee eller Thread, inte båda samtidigt; Green kräver mer eget underhåll än en ren märkeshubb",
    "source_url": "https://www.home-assistant.io/connect/zbt-2/",
}

new_products = [
    {
        "id": "presence-sensor",
        "name": "mmWave-närvarosensor",
        "category": "sensorer",
        "price_hint": "30–90 €",
        "best_for": "rum där någon sitter still, exempelvis kök, kontor och vardagsrum",
        "note": "Närvaro via mmWave är känsligare än vanlig PIR-rörelse och kräver mer finjustering.",
        "models_verified_at": "2026-07-10",
        "selection_basis": "Valda för faktisk mmWave-närvaro, inte enbart rörelse; inget laboratorietest.",
        "models": [
            {
                "name": "Aqara Presence Sensor FP2",
                "good": "Wi‑Fi-mmWave med zoner, flera personer och lokal automation via stödda ekosystem",
                "watch": "kräver fast USB-C-ström och noggrann zoninställning; ingen Aqara-hubb krävs",
                "source_url": "https://www.aqara.com/en/product/presence-sensor-fp2/",
            },
            {
                "name": "Aqara Presence Sensor FP1E",
                "good": "Zigbee-baserad närvaro för ett rum och enklare automation än FP2",
                "watch": "färre zonfunktioner och kompatibiliteten beror på hubb/integration",
                "source_url": "https://www.aqara.com/en/product/presence-sensor-fp1e/",
            },
            {
                "name": "SONOFF SNZB-06P",
                "good": "prisvärd Zigbee-mmWave för enklare närvarostyrning",
                "watch": "USB-ström och placering påverkar falska träffar; kontrollera stöd i din Zigbee-integration",
                "source_url": "https://sonoff.tech/product/gateway-and-sensors/snzb-06p/",
            },
        ],
    },
    {
        "id": "home-assistant-hardware",
        "name": "Home Assistant-hårdvara",
        "category": "hubb",
        "price_hint": "100–250 €",
        "best_for": "lokal styrning med egen server eller färdig Home Assistant-box",
        "note": "Green är enklast. Raspberry Pi passar bättre när du accepterar eget lagrings- och underhållsansvar.",
        "models_verified_at": "2026-07-10",
        "selection_basis": "Jämför färdig Home Assistant-box med egenbyggd installation; inget prestandalaboratorietest.",
        "models": [
            {
                "name": "Home Assistant Green",
                "good": "färdig, tyst och enkel väg till Home Assistant OS",
                "watch": "behöver separat Zigbee-adapter och har mindre expansionsutrymme än egen dator",
                "source_url": "https://www.home-assistant.io/green/",
            },
            {
                "name": "Raspberry Pi 5 med SSD",
                "good": "flexibel och lätt att ersätta delar på om du redan kan Raspberry Pi",
                "watch": "köp inte bara microSD för permanent drift; nätaggregat, kapsling och SSD höjer totalpriset",
                "source_url": "https://www.home-assistant.io/installation/raspberrypi/",
            },
            {
                "name": "Home Assistant Yellow",
                "good": "mer integrerad och utbyggbar Home Assistant-hårdvara med Zigbee",
                "watch": "dyrare och mindre självklar att få tag på än Green",
                "source_url": "https://www.home-assistant.io/yellow/",
            },
        ],
    },
    {
        "id": "co2-sensor",
        "name": "CO₂-sensor med riktig mätning",
        "category": "klimat",
        "price_hint": "90–250 €",
        "best_for": "sovrum och rum där flera personer vistas länge",
        "note": "Skilj riktig CO₂-mätning från uppskattat eCO₂ och från partikelmätning.",
        "models_verified_at": "2026-07-10",
        "selection_basis": "Modeller med uttrycklig CO₂-mätning och begriplig lokal display/app; inget laboratorietest.",
        "models": [
            {
                "name": "Aranet4 Home",
                "good": "tydlig batteridriven display med CO₂, temperatur och luftfuktighet",
                "watch": "premiumpris och Bluetooth räcker inte för alla automatiseringsupplägg",
                "source_url": "https://aranet.com/en/home/products/aranet4-home",
            },
            {
                "name": "Airthings Wave Plus",
                "good": "mäter CO₂ tillsammans med radon, VOC, temperatur och fukt",
                "watch": "saknar den omedelbara bordskänslan hos en stor display och kostar mer",
                "source_url": "https://www.airthings.com/wave-plus",
            },
            {
                "name": "Netatmo Smart Indoor Air Quality Monitor",
                "good": "enkel CO₂-koll för sovrum och hemmakontor",
                "watch": "app/moln och ekosystem bör vägas mot lokala alternativ",
                "source_url": "https://www.netatmo.com/smart-indoor-air-quality-monitor",
            },
        ],
    },
]
for item in new_products:
    if item["id"] in by_id:
        products[products.index(by_id[item["id"]])] = item
    else:
        products.append(item)

# VINDSTYRKA is useful for particulate matter, but it is not a CO2 sensor.
for model in by_id["air-quality-sensor"]["models"]:
    if model["name"] == "IKEA VINDSTYRKA":
        model["good"] = "prisvärd display för PM2.5, temperatur och relativ luftkvalitet i IKEA-hem"
        model["watch"] = "mäter inte CO₂; välj en riktig CO₂-sensor om vädringsnivå är huvudfrågan"

pp.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ap = ROOT / "content" / "articles" / "articles.json"
articles = json.loads(ap.read_text(encoding="utf-8"))
corrections = {
    "basta-zigbee-hubbar-for-familjer": ["zigbee-hub"],
    "basta-narvarosensorer-familj": ["presence-sensor"],
    "narvarosensor-vs-rorelsesensor": ["presence-sensor", "motion-sensor"],
    "home-assistant-green-eller-raspberry-pi": ["home-assistant-hardware"],
    "kopguide-home-assistant-green": ["home-assistant-hardware"],
    "home-assistant-startpaket-vad-behover-man-kopa": ["home-assistant-hardware", "zigbee-hub"],
    "basta-luftkvalitetssensorer-barnrum": ["co2-sensor", "air-quality-sensor"],
    "co2-sensor-home-assistant": ["co2-sensor"],
}
for article in articles:
    if article["slug"] in corrections:
        article["products"] = corrections[article["slug"]]
ap.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"products={len(products)} corrected_articles={len(corrections)}")
