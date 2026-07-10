#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ARTICLES = ROOT / "content" / "articles" / "articles.json"
PRODUCTS = ROOT / "data" / "products.json"
AFFILIATE_LINKS = ROOT / "data" / "affiliate_links.json"
SITE_CONFIG = ROOT / "config" / "site.json"
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
BASE_PATH = os.environ.get("BASE_PATH", "").strip().rstrip("/")
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = "/" + BASE_PATH

MONEY_SLUGS = {
    "basta-smarta-hem-prylar-barnfamiljer",
    "basta-smarta-lampor-barnsovrum",
    "basta-robotdammsugare-barnfamiljer",
    "billigt-smart-hem-under-100-euro",
    "zigbee-vs-wifi-smarta-prylar",
    "basta-zigbee-hubbar-for-familjer",
    "bygg-familjedashboard-surfplatta",
    "basta-vattenlackagesensorer-smart-hem",
    "vattenlackage-sensor-barnfamilj",
    "smarta-pluggar-barnfamilj",
    "aqara-ikea-philips-hue-vad-ska-familjer-valja",
    "narvarosensor-vs-rorelsesensor",
    "home-assistant-green-eller-raspberry-pi",
    "basta-smarta-nattljus-for-barn",
    "smart-kok-for-barnfamiljer",
    "smart-hem-i-hyresratt-utan-att-borra",
    "smarta-hem-prylar-att-inte-kopa-forst",
    "matter-vs-zigbee-familj",
}

PHOTO_BY_SLUG = {
    "basta-smarta-hem-prylar-barnfamiljer": "generated/startpaket-smart-hem.jpg",
    "home-assistant-for-familjer-nyborjarguide": "generated/hubb-pa-hylla.jpg",
    "bygg-familjedashboard-surfplatta": "generated/familjedashboard-kok.jpg",
    "adhd-vanliga-morgonrutiner-smarta-hem": "generated/morgonhall-smart-knapp.jpg",
    "basta-smarta-lampor-barnsovrum": "generated/barnrum-varmt-nattljus.jpg",
    "smarta-knappar-10-anvandningar-hemma": "generated/smart-knapp-narbild.jpg",
    "familjekalender-pa-vaggskarm": "generated/familjedashboard-kok.jpg",
    "robotdammsugare-schema-barnfamilj": "generated/robotdammsugare-kok-hall.jpg",
    "smarta-hem-for-laggdags": "generated/barnrum-varmt-nattljus.jpg",
    "automatisera-inkopslistor-hemma": "generated/familjedashboard-kok.jpg",
    "smarta-hem-notiser-utan-stress": "generated/familjedashboard-kok.jpg",
    "basta-robotdammsugare-barnfamiljer": "generated/robotdammsugare-kok-hall.jpg",
    "home-assistant-dashboard-koket": "generated/familjedashboard-kok.jpg",
    "smarta-paminnelser-skola-medicin-laggdags": "generated/morgonhall-smart-knapp.jpg",
    "zigbee-vs-wifi-smarta-prylar": "generated/hub-sensorer-bord.jpg",
    "familjens-veckovy-idag-plus-sex-dagar": "generated/veckoplan-magnetkort.jpg",
    "smarta-hem-misstag-barnfamiljer": "messy-table.jpg",
    "billigt-smart-hem-under-100-euro": "generated/startpaket-smart-hem.jpg",
    "basta-zigbee-hubbar-for-familjer": "generated/hub-sensorer-bord.jpg",
    "basta-vattenlackagesensorer-smart-hem": "generated/lackage-diskmaskin-sensor.jpg",
    "vattenlackage-sensor-barnfamilj": "generated/tvattstuga-sensor.jpg",
    "smarta-pluggar-barnfamilj": "generated/startpaket-smart-hem.jpg",
    "aqara-ikea-philips-hue-vad-ska-familjer-valja": "generated/barnrum-varmt-nattljus.jpg",
    "narvarosensor-vs-rorelsesensor": "hallway.jpg",
    "smart-hem-i-hyresratt-utan-att-borra": "generated/morgonhall-smart-knapp.jpg",
    "home-assistant-green-eller-raspberry-pi": "generated/hubb-pa-hylla.jpg",
    "basta-smarta-nattljus-for-barn": "generated/barnrum-varmt-nattljus.jpg",
    "smart-hem-for-hundagare": "generated/hund-hall-sensor.jpg",
    "smart-kok-for-barnfamiljer": "generated/familjedashboard-kok.jpg",
    "smarta-hem-prylar-att-inte-kopa-forst": "generated/startpaket-smart-hem.jpg",
    "hallkaos-smart-hem-skola-forskola": "generated/morgonhall-smart-knapp.jpg",
    "tvattstuga-sensorer-familj": "generated/tvattstuga-sensor.jpg",
    "matplanering-dashboard-smart-kok": "generated/veckoplan-magnetkort.jpg",
    "barnens-skarmtid-smarta-hem-signaler": "generated/barnrum-varmt-nattljus.jpg",
    "basta-smarta-pluggar-energi-familj": "generated/energiplugg-kok.jpg",
    "sensorer-i-badrum-natt-och-vatten": "generated/lackage-diskmaskin-sensor.jpg",
    "basta-luftkvalitetssensorer-barnrum": "generated/luftsensor-barnrum.jpg",
    "co2-sensor-home-assistant": "generated/luftsensor-barnrum.jpg",
    "smart-brandvarnare-familj": "generated/brandvarnare-hall.jpg",
    "basta-smarta-las-barnfamilj": "generated/ytterdorr-smart-las-sensor.jpg",
    "fryslarm-med-temperatursensor": "generated/tvattstuga-sensor.jpg",
    "smart-brevlada-dorrsensor": "commons-mailbox.jpg",
    "smart-forrad-garage-sensorer": "generated/ytterdorr-smart-las-sensor.jpg",
    "integritet-smart-hem-familj": "generated/lokalt-natverk-router.jpg",
    "backup-home-assistant-familj": "generated/backup-desk-usb.jpg",
    "forbattra-zigbee-mesh-hemma": "generated/zigbee-mesh-lagenhet.jpg",
    "smarta-gardiner-barnrum": "generated/gardiner-morgonljus.jpg",
    "basta-smarta-gardiner-familj": "generated/gardiner-morgonljus.jpg",
    "smart-hem-utan-abonnemang": "generated/startpaket-smart-hem.jpg",
    "matter-vs-zigbee-familj": "generated/hub-sensorer-bord.jpg",
    "smarta-hem-for-laxa-och-fokus": "generated/barnrum-varmt-nattljus.jpg",
    "smart-hem-for-medicinpaminnelser": "generated/familjedashboard-kok.jpg",
    "smart-hem-for-familj-med-skiftarbete": "generated/barnrum-varmt-nattljus.jpg",
    "kopguide-smarta-hem-presenter": "generated/startpaket-smart-hem.jpg",
    "tvattmaskinen-klar-smart-paminnelse": "generated/tvattstuga-sensor.jpg",
    "smart-hem-delad-vardnad-packlista": "generated/familjedashboard-kok.jpg",
    "barn-glommer-saker-smart-checklista": "generated/morgonhall-smart-knapp.jpg",
    "smart-hall-vinterfamilj": "generated/termostat-vinter.jpg",
    "god-natt-knapp-familj-home-assistant": "generated/barnrum-varmt-nattljus.jpg",
    "smart-kyl-frys-utan-dyrt-kylskap": "generated/startpaket-smart-hem.jpg",
    "barnrum-utan-appkaos-tre-lagen": "generated/barnrum-varmt-nattljus.jpg",
    "barn-ensamma-hemma-smart-hem-utan-kamera": "generated/ytterdorr-smart-las-sensor.jpg",
    "robotdammsugare-stadzoner-kok-hall-matbord": "generated/robotdammsugare-kok-hall.jpg",
    "familjens-krislage-dashboard-vatten-brand-strom": "generated/lackage-diskmaskin-sensor.jpg",
    "produktguide-forsta-zigbee-sensorerna-rum-for-rum": "generated/hub-sensorer-bord.jpg",
    "spara-el-home-assistant-familj": "generated/startpaket-smart-hem.jpg",
    "smart-plug-energimatning-vad-kan-man-mata": "generated/energiplugg-kok.jpg",
    "home-assistant-startpaket-vad-behover-man-kopa": "generated/hub-sensorer-bord.jpg",
    "smart-hem-hyresratt-startpaket-under-100-euro": "generated/morgonhall-smart-knapp.jpg",
    "vackningsljus-barn-smart-lampa-eller-vackarklocka": "generated/barnrum-varmt-nattljus.jpg",
    "smart-hem-for-sommarstuga": "generated/sommarstuga-sensor.jpg",
    "smart-hem-for-regniga-dagar": "generated/regnig-hall-tvatt.jpg",
    "basta-smarta-termostater-familj": "generated/termostat-vinter.jpg",
    "smart-hem-energispara-familj": "generated/energiplugg-kok.jpg",
    "smart-hem-nar-internet-gar-ner": "generated/lokalt-natverk-router.jpg",
    "smart-hem-utan-moln": "generated/lokalt-natverk-router.jpg",
}

TAG_LABELS = {
    "home-assistant": "Home Assistant",
    "kopguide": "Köpguide",
    "guide": "Guide",
    "ideer": "Idéer",
    "idéer": "Idéer",
    "sakerhet": "Säkerhet",
    "jamforelse": "Jämförelse",
    "sensorer": "Sensorer",
    "belysning": "Belysning",
    "dashboard": "Dashboard",
    "rutiner": "Rutiner",
    "barnrum": "Barnrum",
    "kok": "Kök",
    "zigbee": "Zigbee",
    "städning": "Städning",
    "vattenlackage": "Vattenläcka",
    "budget": "Budget",
    "hyresratt": "Hyresrätt",
    "hund": "Hund",
    "morgon": "Morgon",
    "laggdags": "Läggdags",
    "kalender": "Kalender",
    "notiser": "Notiser",
    "knappar": "Knappar",
    "pluggar": "Pluggar",
    "dorrar": "Dörrar",
    "hall": "Hall",
    "klimat": "Klimat",
    "varme": "Värme",
    "värme": "Värme",
    "energi": "Energi",
    "checklista": "Checklista",
    "faq": "FAQ",
    "co2": "CO₂",
    "luftkvalitet": "Luftkvalitet",
    "brand": "Brand",
    "las": "Lås",
    "lås": "Lås",
    "frys": "Frys",
    "forrad": "Förråd",
    "garage": "Garage",
    "integritet": "Integritet",
    "backup": "Backup",
    "matter": "Matter",
    "presenter": "Presenter",
}


def slugify(text: str) -> str:
    text = text.lower().replace("å", "a").replace("ä", "a").replace("ö", "o").replace("é", "e")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def normalize_tag(tag: str) -> str:
    tag = str(tag).strip().lower()
    if tag == "köpguide":
        return "kopguide"
    return slugify(tag)


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def render_page(title: str, description: str, body: str, out: Path, extra_head: str = "") -> None:
    page = (
        BASE.replace("{{ title }}", esc(title))
        .replace("{{ description }}", esc(description))
        .replace("{{ extra_head }}", extra_head)
        .replace("{{ body }}", body)
    )
    if BASE_PATH:
        page = page.replace("href='/", f"href='{BASE_PATH}/")
        page = page.replace('href="/', f'href="{BASE_PATH}/')
        page = page.replace("src='/", f"src='{BASE_PATH}/")
        page = page.replace('src="/', f'src="{BASE_PATH}/')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def is_money(article: dict) -> bool:
    return article.get("slug") in MONEY_SLUGS or article.get("category") == "köpguide"


def tag_label(tag: str) -> str:
    return TAG_LABELS.get(tag, tag.replace("-", " ").title())


def article_tags(article: dict) -> list[str]:
    tags = [normalize_tag(t) for t in article.get("tags", []) if normalize_tag(t)]
    cat = article.get("category", "").strip().lower()
    if cat:
        tags.append("kopguide" if cat == "köpguide" else normalize_tag(cat))
    slug = article.get("slug", "")
    title = article.get("title", "").lower()
    checks = {
        "home-assistant": ["home-assistant", "home assistant"],
        "sensorer": ["sensor", "narvaro", "rörelse", "rorelse"],
        "belysning": ["lampa", "lampor", "ljus", "nattljus"],
        "barnrum": ["sovrum", "nattljus", "barnsovrum"],
        "kok": ["kok", "kök", "inkop", "inköp", "diskmaskin"],
        "zigbee": ["zigbee", "aqara", "ikea", "hue", "hub"],
        "städning": ["robot", "dammsugare", "städ"],
        "vattenlackage": ["vatten", "läck", "lack"],
        "budget": ["budget", "100-euro", "billigt"],
        "hyresratt": ["hyresratt", "hyresrätt"],
        "hund": ["hund"],
        "morgon": ["morgon"],
        "laggdags": ["lägg", "lagg", "natt"],
        "kalender": ["kalender", "veckovy"],
        "notiser": ["notis", "påminn", "paminn"],
        "knappar": ["knapp"],
        "pluggar": ["plug"],
    }
    hay = f"{slug} {title}"
    for tag, needles in checks.items():
        if any(n in hay for n in needles):
            tags.append(tag)
    return sorted(dict.fromkeys(tags))[:8]


def thumb_for(article: dict) -> str:
    slug = article.get("slug", "")
    title = article.get("title", "").lower()
    hay = f"{slug} {title}"
    filename = PHOTO_BY_SLUG.get(slug)
    if not filename:
        if any(x in hay for x in ["vatten", "läck", "lack", "fukt", "badrum", "tvatt", "tvätt"]):
            filename = "commons-leaky-sink-valve.jpg"
        elif any(x in hay for x in ["dorr", "dörr", "hall", "regn", "lagenhet", "lägenhet"]):
            filename = "generated/morgonhall-smart-knapp.jpg"
        elif any(x in hay for x in ["temperatur", "fukt", "termostat", "varme", "värme", "vinter", "energi"]):
            filename = "generated/startpaket-smart-hem.jpg"
        elif any(x in hay for x in ["dashboard", "kalender", "veckovy", "barnvakt"]):
            filename = "generated/familjedashboard-kok.jpg"
        elif any(x in hay for x in ["knapp", "button"]):
            filename = "generated/morgonhall-smart-knapp.jpg"
        elif any(x in hay for x in ["zigbee", "aqara", "ikea", "hue", "green", "internet", "moln", "lokalt"]):
            filename = "generated/hub-sensorer-bord.jpg"
        elif any(x in hay for x in ["robot", "dammsugare", "husdjur", "hund"]):
            filename = "generated/robotdammsugare-kok-hall.jpg"
        elif any(x in hay for x in ["barnrum", "natt", "skarmtid", "skärmtid", "tonaring", "tonåring"]):
            filename = "generated/barnrum-varmt-nattljus.jpg"
        elif any(x in hay for x in ["kok", "kök", "mat", "inkop", "inköp"]):
            filename = "generated/familjedashboard-kok.jpg"
        else:
            filename = "generated/startpaket-smart-hem.jpg"
    return f"/assets/photos/{filename}"


def tag_links(article: dict) -> str:
    tags = article_tags(article)
    if not tags:
        return ""
    return "<div class='tags'>" + "".join(f"<a href='/tag/{slugify(t)}.html'>#{esc(tag_label(t))}</a>" for t in tags[:6]) + "</div>"


def amazon_search_url(query: str) -> str:
    return f"https://www.amazon.se/s?k={quote_plus(query)}&tag=smartahemmet-21"


def model_rows(product: dict, limit: int = 3) -> str:
    rows = []
    for model in product.get("models", [])[:limit]:
        name = model.get("name", "")
        if not name:
            continue
        rows.append(
            "<li>"
            f"<a href='{esc(amazon_search_url(name))}' rel='sponsored nofollow noopener' target='_blank'><strong>{esc(name)}</strong></a>"
            f"<span>{esc(model.get('good', ''))}</span>"
            f"<em>{esc(model.get('watch', ''))}</em>"
            "</li>"
        )
    if not rows:
        return ""
    return "<ul class='model-list'>" + "".join(rows) + "</ul>"


def model_comparison(products: list[dict], ids: list[str], title: str = "Faktiska modeller att jämföra") -> str:
    by_id = {p["id"]: p for p in products}
    blocks = []
    for pid in ids[:5]:
        p = by_id.get(pid)
        if not p or not p.get("models"):
            continue
        blocks.append(
            "<div class='model-block'>"
            f"<h3>{esc(p['name'])}</h3>"
            f"<p>{esc(p.get('note', p.get('best_for', '')))}</p>"
            f"{model_rows(p)}"
            "</div>"
        )
    if not blocks:
        return ""
    return (
        f"<section class='model-comparison'><h2>{esc(title)}</h2>"
        "<p class='fineprint'>Det här är jämförelseexempel, inte produkter vi har laboratorietestat. Pris, lager och kompatibilitet kan ändras.</p>"
        "<div class='model-grid'>" + "".join(blocks) + "</div></section>"
    )


def product_cards(products: list[dict], ids: list[str], affiliate_links: dict, title: str = "Prylar som nämns", compact: bool = False) -> str:
    by_id = {p["id"]: p for p in products}
    cards = []
    seen_links = set()
    for pid in ids:
        p = by_id.get(pid)
        if not p:
            continue
        link = affiliate_links.get(pid, {})
        link_html = ""
        url = link.get("url", "")
        if link.get("status") == "active" and url and url not in seen_links:
            seen_links.add(url)
            label = link.get('label', 'Se alternativ')
            if compact:
                label = label.replace(" på Amazon", "")
            link_html = f"<a class='buy-link' href='{esc(url)}' rel='sponsored nofollow noopener' target='_blank'>{esc(label)}</a>"
        examples = ""
        if not compact and p.get("models"):
            names = ", ".join(m.get("name", "") for m in p.get("models", [])[:3] if m.get("name"))
            examples = f"<p class='model-teaser'><strong>Exempel:</strong> {esc(names)}</p>" if names else ""
        cards.append(
            "<div class='mini-card'>"
            f"<span class='pill'>{esc(p['category'])}</span>"
            f"<h3>{esc(p['name'])}</h3>"
            f"<p>{esc(p['best_for'])}</p>"
            f"<small>Typiskt pris: {esc(p['price_hint'])}</small>"
            f"{examples}{link_html}"
            "</div>"
        )
    if not cards:
        return ""
    compact_class = " related-products-compact" if compact else ""
    return f"<section class='related-products{compact_class}'><h2>{esc(title)}</h2><div class='mini-grid'>" + "".join(cards) + "</div></section>"


def buying_summary_box(article: dict, products: list[dict]) -> str:
    if not is_money(article):
        return ""
    tags = set(article_tags(article))
    product_ids = article.get("products", [])
    by_id = {p["id"]: p for p in products}
    first_product = by_id.get(product_ids[0], {}) if product_ids else {}
    best = "Börja med den produktkategori som löser problemet varje vecka, inte den som verkar mest avancerad."
    avoid = "Undvik paket där allt kräver en separat app om målet är Home Assistant och låg friktion."
    budget = first_product.get("price_hint", "börja billigt och bygg vidare")
    works = "Home Assistant, Zigbee eller vanliga app-lösningar beroende på hur mycket du vill pilla."
    if "vattenlackage" in tags:
        best = "Om du bara köper en sak: sätt ett vattenlarm under diskmaskin, vask eller tvättmaskin."
        avoid = "Undvik sensorer som bara larmar i en app ingen öppnar."
        works = "Bäst med Zigbee och lokala notiser i Home Assistant."
    elif "budget" in tags or "hyresratt" in tags:
        best = "Välj flyttbara prylar: lampa, knapp, sensor eller plug utan fast installation."
        avoid = "Undvik fasta installationer och dyra startpaket innan ni vet vad som används."
    elif "home-assistant" in tags or "zigbee" in tags:
        best = "Börja med hubb, en knapp och 2–3 sensorer som löser tydliga vardagsproblem."
        avoid = "Undvik att köpa tio olika ekosystem samtidigt."
        works = "Bäst med Zigbee, lokal styrning och enkel backup."
    elif "energi" in tags:
        best = "Mät först: smart plug med energimätning ger mest värde där den ändrar ett beteende."
        avoid = "Undvik att styra värme aggressivt så familjen börjar överstyra allt manuellt."
    elif "barnrum" in tags or "belysning" in tags:
        best = "Börja med en enkel lampa eller knapp barnet förstår utan app."
        avoid = "Undvik för starkt ljus och för många färgscener."
    return (
        "<section class='buying-summary'><h2>Snabbval</h2><div class='summary-grid'>"
        f"<div><strong>Välj detta om</strong><p>{esc(best)}</p></div>"
        f"<div><strong>Undvik om</strong><p>{esc(avoid)}</p></div>"
        f"<div><strong>Rimlig budget</strong><p>{esc(budget)}</p></div>"
        f"<div><strong>Funkar bäst med</strong><p>{esc(works)}</p></div>"
        "</div></section>"
    )


def decision_table(article: dict, products: list[dict]) -> str:
    if not is_money(article) or not article.get("products"):
        return ""
    by_id = {p["id"]: p for p in products}
    rows = []
    for pid in article.get("products", [])[:5]:
        p = by_id.get(pid)
        if not p:
            continue
        rows.append(
            "<tr>"
            f"<td>{esc(p['category'])}</td>"
            f"<td>{esc(p['name'])}</td>"
            f"<td>{esc(p['price_hint'])}</td>"
            f"<td>{esc(p['best_for'])}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return (
        "<section class='decision-table-wrap'><h2>Saker att jämföra</h2>"
        "<table class='decision-table'><thead><tr><th>Behov</th><th>Titta efter</th><th>Prisnivå</th><th>Passar bäst för</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></section>"
    )


def problem_chips() -> str:
    chips = [
        ("Morgonrutin", "/tag/morgon.html"),
        ("Barnrum", "/tag/barnrum.html"),
        ("Vattenläcka", "/tag/vattenlackage.html"),
        ("Billigt startpaket", "/tag/budget.html"),
        ("Home Assistant", "/tag/home-assistant.html"),
        ("Hyresrätt", "/tag/hyresratt.html"),
        ("Energi", "/tag/energi.html"),
        ("Säkerhet", "/tag/sakerhet.html"),
    ]
    return "<nav class='problem-chips' aria-label='Välj problem'>" + "".join(f"<a href='{href}'>{esc(label)}</a>" for label, href in chips) + "</nav>"


def everyday_block(article: dict) -> str:
    examples = [str(item).strip() for item in article.get("examples", []) if str(item).strip()]
    if not examples:
        return ""
    items = "".join(f"<li>{esc(item)}</li>" for item in examples[:4])
    return f"<section class='example-box'><h2>Så kan det se ut hemma</h2><ul>{items}</ul></section>"


def reading_minutes(article: dict) -> int:
    text = " ".join(
        [article.get("description", ""), article.get("intro", "")]
        + [str(part) for section in article.get("sections", []) for part in section[:2]]
        + [str(item) for item in article.get("examples", [])]
    )
    word_count = len(re.findall(r"\w+", text))
    return max(2, (word_count + 189) // 190)


def related_articles(article: dict, all_articles: list[dict], limit: int = 4) -> list[dict]:
    current_slug = article.get("slug")
    current_tags = set(article_tags(article))
    scored = []
    for candidate in all_articles:
        if candidate.get("slug") == current_slug:
            continue
        overlap = len(current_tags & set(article_tags(candidate)))
        if is_money(article) == is_money(candidate):
            overlap += 1
        if overlap:
            scored.append((overlap, candidate.get("title", ""), candidate))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:limit]]


def related_articles_html(article: dict, all_articles: list[dict]) -> str:
    related = related_articles(article, all_articles)
    if not related:
        return ""
    links = []
    for item in related:
        kind = "Köpråd" if is_money(item) else "Guide"
        links.append(
            f"<a class='related-link' href='/artiklar/{esc(item['slug'])}.html'>"
            f"<strong>{esc(item['title'])}</strong><span>{kind} · {esc(item['description'])}</span></a>"
        )
    return "<section class='related-articles'><h2>Läs vidare</h2><div class='related-list'>" + "".join(links) + "</div></section>"


def breadcrumb_html(article: dict) -> str:
    section = "Köpråd" if is_money(article) else "Guider"
    href = "/koprad.html" if is_money(article) else "/guider.html"
    return f"<nav class='breadcrumb' aria-label='Brödsmulor'><a href='/'>Start</a> / <a href='{href}'>{section}</a> / {esc(article['title'])}</nav>"


def json_ld(data: dict) -> str:
    return "<script type='application/ld+json'>" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"


def article_extra_head(article: dict, site_url: str) -> str:
    slug = article.get("slug", "")
    url = f"{site_url}/artiklar/{slug}.html" if site_url else f"/artiklar/{slug}.html"
    image = f"{site_url}{thumb_for(article)}" if site_url else thumb_for(article)
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.get("title", ""),
        "description": article.get("description", ""),
        "inLanguage": "sv-SE",
        "dateModified": "2026-07-08",
        "datePublished": "2026-07-08",
        "author": {"@type": "Organization", "name": "Smart Familj Hemma"},
        "publisher": {"@type": "Organization", "name": "Smart Familj Hemma"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "image": [image],
        "keywords": [tag_label(t) for t in article_tags(article)],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Start", "item": site_url + "/" if site_url else "/"},
            {"@type": "ListItem", "position": 2, "name": "Köpråd" if is_money(article) else "Guider", "item": site_url + ("/koprad.html" if is_money(article) else "/guider.html") if site_url else ("/koprad.html" if is_money(article) else "/guider.html")},
            {"@type": "ListItem", "position": 3, "name": article.get("title", ""), "item": url},
        ],
    }
    og = "\n".join([
        f"<link rel='canonical' href='{esc(url)}'>",
        f"<meta property='og:title' content='{esc(article.get('title', ''))}'>",
        f"<meta property='og:description' content='{esc(article.get('description', ''))}'>",
        f"<meta property='og:type' content='article'>",
        f"<meta property='og:url' content='{esc(url)}'>",
        f"<meta property='og:image' content='{esc(image)}'>",
    ])
    return og + "\n" + json_ld(schema) + "\n" + json_ld(breadcrumb)


def article_html(article: dict, products: list[dict], affiliate_links: dict, all_articles: list[dict]) -> str:
    parts = [
        breadcrumb_html(article),
        "<article>",
        f"<span class='pill'>{esc(article['category'])}</span>",
        f"<h1>{esc(article['title'])}</h1>",
        f"<p class='lead'>{esc(article['description'])}</p>",
        f"<div class='article-meta'><span>{reading_minutes(article)} min läsning</span><span>Uppdaterad juli 2026</span></div>",
        tag_links(article),
        f"<img class='article-hero-image' src='{thumb_for(article)}' alt=''>",
    ]
    intro = article.get("intro")
    if intro:
        parts.append(f"<p>{esc(intro)}</p>")
    if is_money(article):
        parts.append(buying_summary_box(article, products))
        parts.append(decision_table(article, products))
        parts.append(model_comparison(products, article.get("products", [])))
    for idx, (heading, text) in enumerate(article["sections"]):
        parts.append(f"<h2>{esc(heading)}</h2><p>{esc(text)}</p>")
        if idx == 1:
            parts.append(everyday_block(article))
    if not is_money(article):
        parts.append(product_cards(products, article.get("products", []), affiliate_links))
    parts.append(related_articles_html(article, all_articles))
    parts.append("</article>")
    return "\n".join(parts)


def card(article: dict, large: bool = False, compact: bool = False) -> str:
    size = " card-large" if large else ""
    compact_class = " card-compact" if compact else ""
    slug = article.get("slug", "")
    kind = "Köpråd" if is_money(article) else "Guide"
    return (
        f"<div class='card{size}{compact_class}'>"
        f"<a class='card-image' href='/artiklar/{slug}.html'><img src='{thumb_for(article)}' alt=''></a>"
        f"<div class='card-body'><span class='pill'>{kind}</span>"
        f"<h2><a href='/artiklar/{slug}.html'>{esc(article['title'])}</a></h2>"
        f"<p>{esc(article['description'])}</p>{tag_links(article)}</div>"
        "</div>"
    )


def article_list_page(title: str, description: str, articles: list[dict], intro: str = "") -> str:
    intro_html = f"<p class='lead page-lead'>{esc(intro)}</p>" if intro else ""
    return f"<section><div class='section-title'><h1>{esc(title)}</h1></div>{intro_html}<div class='grid'>" + "".join(card(a) for a in articles) + "</div></section>"


def buying_index_page(articles: list[dict]) -> str:
    clusters = [
        ("Börja billigt", "Under 100 euro, hyresrätt och prylar som går att flytta.", ["budget", "hyresratt"], "/tag/budget.html"),
        ("Säkerhet", "Vattenlarm, brand, dörrar och frånvaro utan kamera.", ["sakerhet", "vattenlackage", "brand", "dorrar"], "/tag/sakerhet.html"),
        ("Barnrum", "Ljus, gardiner, klimat och kvällsrutiner.", ["barnrum", "belysning", "klimat"], "/tag/barnrum.html"),
        ("Home Assistant", "Hubb, Zigbee, sensorer och första inköpen.", ["home-assistant", "zigbee", "sensorer"], "/tag/home-assistant.html"),
        ("Energi", "Pluggar, termostater och mätning som faktiskt används.", ["energi", "varme", "pluggar"], "/tag/energi.html"),
    ]
    cluster_cards = []
    for title, text, tags, href in clusters:
        count = sum(1 for a in articles if set(tags) & set(article_tags(a)))
        cluster_cards.append(f"<a class='topic' href='{href}'><strong>{esc(title)}</strong><span>{esc(text)} · {count} sidor</span></a>")
    body = (
        "<section><div class='section-title'><h1>Köpråd</h1></div>"
        "<div class='topic-strip buying-clusters'>" + "".join(cluster_cards) + "</div></section>"
        "<section><div class='section-title'><h2>Alla köpråd</h2></div><div class='grid'>" + "".join(card(a) for a in articles) + "</div></section>"
    )
    return body


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    assets_src = ROOT / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, SITE / "assets")
    for verification_file in ROOT.glob("google*.html"):
        shutil.copy2(verification_file, SITE / verification_file.name)

    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    affiliate_links = json.loads(AFFILIATE_LINKS.read_text(encoding="utf-8")) if AFFILIATE_LINKS.exists() else {}
    site_config = json.loads(SITE_CONFIG.read_text(encoding="utf-8")) if SITE_CONFIG.exists() else {}

    site_url = str(os.environ.get("SITE_URL") or site_config.get("site_url", "")).rstrip("/")

    by_slug = {a.get("slug"): a for a in articles}
    buy_articles = [a for a in articles if is_money(a)]
    guide_articles = [a for a in articles if not is_money(a)]

    for a in articles:
        render_page(
            a["title"],
            a["description"],
            article_html(a, products, affiliate_links, articles),
            SITE / "artiklar" / f"{a['slug']}.html",
            extra_head=article_extra_head(a, site_url),
        )

    # Tags and tag pages
    tag_map: dict[str, list[dict]] = defaultdict(list)
    for a in articles:
        for t in article_tags(a):
            tag_map[t].append(a)
    for tag, tagged_articles in tag_map.items():
        body = article_list_page(f"#{tag_label(tag)}", f"Artiklar taggade med {tag_label(tag)}.", tagged_articles)
        render_page(f"Tagg: {tag_label(tag)}", f"Artiklar om {tag_label(tag)}.", body, SITE / "tag" / f"{slugify(tag)}.html")
    popular_tags = [t for t, _ in Counter({k: len(v) for k, v in tag_map.items()}).most_common()]
    tag_page = "<section><div class='section-title'><h1>Taggar</h1></div><div class='tag-cloud'>" + "".join(
        f"<a href='/tag/{slugify(t)}.html'>#{esc(tag_label(t))}<span>{len(tag_map[t])}</span></a>" for t in popular_tags
    ) + "</div></section>"
    render_page("Taggar", "Hitta guider via taggar.", tag_page, SITE / "taggar.html")

    lead = by_slug.get("home-assistant-for-familjer-nyborjarguide", articles[0])
    top_buy = [by_slug[s] for s in ["basta-vattenlackagesensorer-smart-hem", "basta-zigbee-hubbar-for-familjer", "basta-robotdammsugare-barnfamiljer"] if s in by_slug]
    top_guides = [by_slug[s] for s in ["adhd-vanliga-morgonrutiner-smarta-hem", "familjekalender-pa-vaggskarm", "smarta-hem-for-laggdags"] if s in by_slug]
    used_guide_slugs = {lead.get("slug"), *(a.get("slug") for a in top_guides)}
    used_buy_slugs = {a.get("slug") for a in top_buy}
    guide_home = top_guides + [a for a in guide_articles if a.get("slug") not in used_guide_slugs][:5]
    buy_home = [a for a in buy_articles if a.get("slug") not in used_buy_slugs][:8]

    home = f"""
    <section class='hero hero-editorial'>
      <a class='cover-story' href='/artiklar/{lead['slug']}.html'>
        <img src='{thumb_for(lead)}' alt=''>
        <div><span class='kicker'>Börja här</span><h1>{esc(lead['title'])}</h1><p class='lead'>{esc(lead['description'])}</p></div>
      </a>
      <div class='hero-stack'>
        {''.join(card(a, compact=True) for a in top_buy[:2])}
      </div>
    </section>

    <nav class='category-nav' aria-label='Huvudval'>
      <a href='/guider.html'>Guider</a>
      <a href='/koprad.html'>Köpråd</a>
      <a href='/taggar.html'>Taggar</a>
      <a href='/kom-igang.html'>Kom igång</a>
    </nav>

    <section class='problem-section'>
      <div class='section-title'><h2>Vad vill du lösa?</h2></div>
      {problem_chips()}
    </section>

    <section class='split-section'>
      <div>
        <div class='section-title'><h2>Guider</h2><a href='/guider.html'>Alla guider</a></div>
        <div class='compact-grid'>{''.join(card(a, compact=True) for a in guide_home)}</div>
      </div>
      <div>
        <div class='section-title'><h2>Köpråd</h2><a href='/koprad.html'>Alla köpråd</a></div>
        <div class='compact-grid'>{''.join(card(a, compact=True) for a in buy_home)}</div>
      </div>
    </section>

    <section>
      <div class='section-title'><h2>Hitta via taggar</h2><a href='/taggar.html'>Visa alla</a></div>
      <div class='tag-cloud tag-cloud-home'>{''.join(f"<a href='/tag/{slugify(t)}.html'>#{esc(tag_label(t))}<span>{len(tag_map[t])}</span></a>" for t in popular_tags[:14])}</div>
    </section>

    <section class='text-feature'>
      <h2>En vanlig tisdag</h2>
      <p>07.10 tänds hallen mjukt och köksskärmen visar skolväskor, gympapåse och vem som hämtar. 17.30 ligger inköpslistan synligt när någon går förbi kylen. 20.15 går barnrummet över till varmare ljus.</p>
    </section>
    """
    render_page("Smart Familj Hemma", "Smarta hem-guider för barnfamiljer: Home Assistant, familjedashboard och vardagsrutiner.", home, SITE / "index.html")

    start = """<article><span class='pill'>Börja här</span><h1>Kom igång utan att köpa halva elektronikbutiken</h1>
    <p class='lead'>Välj en jobbig stund hemma och bygg runt den.</p>
    <h2>1. Skriv ner friktionen</h2><p>Exempel: alla frågar vad som händer idag, nattlampan väcker syskonet, diskmaskinsläckan upptäcks för sent eller hallen blir kaos fem minuter före skolan.</p>
    <h2>2. Välj en synlig signal</h2><p>En lampa, knapp, väggskärm eller sensor är ofta bättre än ännu en notis. Familjen ska förstå lösningen utan att öppna en app.</p>
    <h2>3. Testa i två veckor</h2><p>Om lösningen inte används efter två veckor: förenkla. Flytta knappen, ta bort steg eller byt till en tydligare signal.</p>
    <p><a class='cta' href='/guider.html'>Läs guider</a> <a class='ghost' href='/koprad.html'>Se köpråd</a></p></article>"""
    render_page("Kom igång", "Börja med smart hem hemma utan att köpa fel prylar.", start, SITE / "kom-igang.html")

    render_page("Blogg", "Alla artiklar från Smart Familj Hemma.", article_list_page("Blogg", "Alla artiklar", articles), SITE / "artiklar.html")
    render_page("Guider", "Praktiska smart hem-guider för barnfamiljer.", article_list_page("Guider", "Guider", guide_articles), SITE / "guider.html")
    render_page("Köpråd", "Köpguider för smart hem i barnfamiljer.", buying_index_page(buy_articles), SITE / "koprad.html")

    product_by_id = {p["id"]: p for p in products}

    def product_card(pid: str) -> str:
        p = product_by_id.get(pid)
        if not p:
            return ""
        link = affiliate_links.get(pid, {})
        link_html = ""
        if link.get("status") == "active" and link.get("url"):
            link_html = f"<a class='buy-link' href='{esc(link['url'])}' rel='sponsored nofollow noopener' target='_blank'>{esc(link.get('label', 'Se alternativ'))}</a>"
        return (
            "<div class='card product-card'>"
            f"<div class='card-body'><span class='pill'>{esc(p['category'])}</span>"
            f"<h2>{esc(p['name'])}</h2>"
            f"<p>{esc(p['best_for'])}</p>"
            f"<p class='muted'>Typiskt pris: {esc(p['price_hint'])}</p>"
            f"<p class='fineprint'>{esc(p.get('note', ''))}</p>"
            f"{model_rows(p, limit=3)}"
            f"{link_html}</div></div>"
        )

    product_groups = [
        ("Vatten, brand och frånvaro", "", ["water-leak-sensor", "smart-smoke-detector", "door-window-sensor", "temperature-sensor"]),
        ("Barnrum och kväll", "", ["smart-bulb", "smart-button", "motion-sensor", "air-quality-sensor", "smart-blinds"]),
        ("Energi och vinter", "", ["smart-plug", "smart-thermostat", "temperature-sensor"]),
        ("Kom igång med Home Assistant", "", ["zigbee-hub", "tablet-wall", "smart-button", "motion-sensor"]),
        ("Städning och hall", "", ["robot-vacuum", "door-window-sensor", "smart-button", "motion-sensor"]),
    ]
    product_sections = []
    for heading, intro_text, ids in product_groups:
        cards = "".join(product_card(pid) for pid in ids)
        intro_html = f"<p class='lead page-lead'>{esc(intro_text)}</p>" if intro_text else ""
        product_sections.append(
            f"<section><div class='section-title'><h2>{esc(heading)}</h2></div>"
            f"{intro_html}<div class='grid'>{cards}</div></section>"
        )
    products_page = "<section><div class='section-title'><h1>Produktkategorier</h1></div></section>" + "".join(product_sections)
    render_page("Produktkategorier", "Prylar för smart hem i barnfamiljer.", products_page, SITE / "produkter.html")

    about = """<article><h1>Om Smart Familj Hemma</h1>
    <p class='lead'>Den här sajten handlar om smart hem där det faktiskt bor folk: barn, trötta vuxna, hund, tvätt, skolväskor och middagar som inte alltid går enligt plan.</p>
    <p>Jag är mer intresserad av lugnare vardag än av perfekta dashboards. Om en automation inte används av familjen är den inte klar, hur snygg den än ser ut.</p>
    <h2>Principen</h2><p>Börja med en verklig friktion. Lös den enkelt. Vänta. Bygg vidare först när det märks att lösningen hjälper.</p></article>"""
    render_page("Om", "Om Smart Familj Hemma.", about, SITE / "om.html")

    disclosure = """<article><h1>Transparens</h1>
    <p>Smart Familj Hemma använder affiliate-länkar, bland annat via Amazon Associates. Som Amazon-partner tjänar sajten pengar på kvalificerade köp.</p>
    <p>Det kostar inte extra för dig att använda en sådan länk.</p>
    <h2>Reklam</h2><p>Displayannonser kan bli aktuella när sajten har stabil trafik. Först krävs normalt egen domän, integritetstext, cookiehantering om annonsnätverket kräver det och tillräckligt med innehåll för att bli godkänd.</p>
    <p>Reklam ska märkas tydligt och inte blandas ihop med köpråd.</p></article>"""
    render_page("Transparens", "Transparens om länkar, annonser och rekommendationer.", disclosure, SITE / "affiliate.html")

    privacy = """<article><h1>Integritet</h1>
    <p>Den här versionen av sajten samlar inte in personuppgifter, har inga formulär och sätter inga egna cookies.</p>
    <p>Om analys, annonser eller affiliate-nätverk läggs till senare ska den här sidan uppdateras först.</p></article>"""
    render_page("Integritet", "Integritetspolicy för Smart Familj Hemma.", privacy, SITE / "integritet.html")

    paths = ["/", "/kom-igang.html", "/artiklar.html", "/guider.html", "/koprad.html", "/taggar.html", "/produkter.html", "/om.html", "/affiliate.html", "/integritet.html"]
    paths += [f"/artiklar/{a['slug']}.html" for a in articles]
    paths += [f"/tag/{slugify(t)}.html" for t in tag_map]
    site_url = str(os.environ.get("SITE_URL") or site_config.get("site_url", "")).rstrip("/")
    if site_url:
        sitemap = "\n".join([site_url + path for path in paths])
        robots = f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.txt\n"
    else:
        sitemap = "\n".join(paths)
        robots = "User-agent: *\nAllow: /\n"
    (SITE / "sitemap.txt").write_text(sitemap + "\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(robots, encoding="utf-8")
    print(f"Built {len(articles)} articles into {SITE}")


if __name__ == "__main__":
    main()
