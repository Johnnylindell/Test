#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ARTICLES = ROOT / "content" / "articles" / "articles.json"
PRODUCTS = ROOT / "data" / "products.json"
AFFILIATE_LINKS = ROOT / "data" / "affiliate_links.json"
SITE_CONFIG = ROOT / "config" / "site.json"
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")

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
}

PHOTO_BY_SLUG = {
    "basta-smarta-hem-prylar-barnfamiljer": "family-living.jpg",
    "home-assistant-for-familjer-nyborjarguide": "tech-desk.jpg",
    "bygg-familjedashboard-surfplatta": "tablet-kitchen.jpg",
    "adhd-vanliga-morgonrutiner-smarta-hem": "morning-hall.jpg",
    "basta-smarta-lampor-barnsovrum": "kids-bedroom.jpg",
    "smarta-knappar-10-anvandningar-hemma": "switch-wall.jpg",
    "familjekalender-pa-vaggskarm": "family-calendar.jpg",
    "robotdammsugare-schema-barnfamilj": "vacuum-room.jpg",
    "smarta-hem-for-laggdags": "bedroom-night.jpg",
    "automatisera-inkopslistor-hemma": "grocery-kitchen.jpg",
    "smarta-hem-notiser-utan-stress": "phone-table.jpg",
    "basta-robotdammsugare-barnfamiljer": "robot-floor.jpg",
    "home-assistant-dashboard-koket": "tablet-desk.jpg",
    "smarta-paminnelser-skola-medicin-laggdags": "school-bag.jpg",
    "zigbee-vs-wifi-smarta-prylar": "zigbee-desk.jpg",
    "familjens-veckovy-idag-plus-sex-dagar": "weekly-planner.jpg",
    "smarta-hem-misstag-barnfamiljer": "messy-table.jpg",
    "billigt-smart-hem-under-100-euro": "budget-home.jpg",
    "basta-zigbee-hubbar-for-familjer": "hub-table.jpg",
    "basta-vattenlackagesensorer-smart-hem": "water-sink.jpg",
    "vattenlackage-sensor-barnfamilj": "commons-laundry-room.jpg",
    "smarta-pluggar-barnfamilj": "smart-plug.jpg",
    "aqara-ikea-philips-hue-vad-ska-familjer-valja": "smart-bulbs.jpg",
    "narvarosensor-vs-rorelsesensor": "hallway.jpg",
    "smart-hem-i-hyresratt-utan-att-borra": "apartment.jpg",
    "home-assistant-green-eller-raspberry-pi": "green-pi.jpg",
    "basta-smarta-nattljus-for-barn": "night-light.jpg",
    "smart-hem-for-hundagare": "dog-hall.jpg",
    "smart-kok-for-barnfamiljer": "kitchen.jpg",
    "smarta-hem-prylar-att-inte-kopa-forst": "shopping-basket.jpg",
    "hallkaos-smart-hem-skola-forskola": "morning-hall.jpg",
    "tvattstuga-sensorer-familj": "commons-laundry-room.jpg",
    "matplanering-dashboard-smart-kok": "tablet-kitchen.jpg",
    "barnens-skarmtid-smarta-hem-signaler": "kids-bedroom.jpg",
    "basta-smarta-pluggar-energi-familj": "smart-plug.jpg",
    "sensorer-i-badrum-natt-och-vatten": "water-sink.jpg",
    "basta-luftkvalitetssensorer-barnrum": "commons-co2-monitor.jpg",
    "co2-sensor-home-assistant": "commons-co2-monitor.jpg",
    "smart-brandvarnare-familj": "commons-smoke-detector.jpg",
    "basta-smarta-las-barnfamilj": "commons-smart-lock.jpg",
    "fryslarm-med-temperatursensor": "commons-thermostat.jpg",
    "smart-brevlada-dorrsensor": "commons-mailbox.jpg",
    "smart-forrad-garage-sensorer": "morning-hall.jpg",
    "integritet-smart-hem-familj": "zigbee-desk.jpg",
    "backup-home-assistant-familj": "green-pi.jpg",
    "forbattra-zigbee-mesh-hemma": "zigbee-desk.jpg",
    "smarta-gardiner-barnrum": "commons-roller-blinds.jpg",
    "basta-smarta-gardiner-familj": "commons-roller-blinds.jpg",
    "smart-hem-utan-abonnemang": "family-living.jpg",
    "matter-vs-zigbee-familj": "zigbee-desk.jpg",
    "smarta-hem-for-laxa-och-fokus": "kids-bedroom.jpg",
    "smart-hem-for-medicinpaminnelser": "tablet-kitchen.jpg",
    "smart-hem-for-familj-med-skiftarbete": "bedroom-night.jpg",
    "kopguide-smarta-hem-presenter": "smart-plug.jpg",
    "tvattmaskinen-klar-smart-paminnelse": "commons-laundry-room.jpg",
    "smart-hem-delad-vardnad-packlista": "family-calendar.jpg",
    "barn-glommer-saker-smart-checklista": "school-bag.jpg",
    "smart-hall-vinterfamilj": "morning-hall.jpg",
    "god-natt-knapp-familj-home-assistant": "bedroom-night.jpg",
    "smart-kyl-frys-utan-dyrt-kylskap": "commons-thermostat.jpg",
    "barnrum-utan-appkaos-tre-lagen": "kids-bedroom.jpg",
    "barn-ensamma-hemma-smart-hem-utan-kamera": "commons-smart-lock.jpg",
    "robotdammsugare-stadzoner-kok-hall-matbord": "robot-floor.jpg",
    "familjens-krislage-dashboard-vatten-brand-strom": "water-sink.jpg",
    "produktguide-forsta-zigbee-sensorerna-rum-for-rum": "zigbee-desk.jpg",
    "spara-el-home-assistant-familj": "budget-home.jpg",
    "smart-plug-energimatning-vad-kan-man-mata": "smart-plug.jpg",
    "home-assistant-startpaket-vad-behover-man-kopa": "green-pi.jpg",
    "smart-hem-hyresratt-startpaket-under-100-euro": "apartment.jpg",
    "vackningsljus-barn-smart-lampa-eller-vackarklocka": "night-light.jpg",
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
        if any(x in hay for x in ["vatten", "diskmaskin", "badrum", "tvatt", "tvätt", "sommarstuga"]):
            filename = "water-sink.jpg"
        elif any(x in hay for x in ["dorr", "dörr", "hall", "regn", "lagenhet", "lägenhet"]):
            filename = "morning-hall.jpg"
        elif any(x in hay for x in ["temperatur", "fukt", "termostat", "varme", "värme", "vinter", "energi"]):
            filename = "budget-home.jpg"
        elif any(x in hay for x in ["dashboard", "kalender", "veckovy", "barnvakt"]):
            filename = "tablet-kitchen.jpg"
        elif any(x in hay for x in ["knapp", "button"]):
            filename = "switch-wall.jpg"
        elif any(x in hay for x in ["zigbee", "aqara", "ikea", "hue", "green", "internet", "moln", "lokalt"]):
            filename = "zigbee-desk.jpg"
        elif any(x in hay for x in ["robot", "dammsugare", "husdjur", "hund"]):
            filename = "robot-floor.jpg"
        elif any(x in hay for x in ["barnrum", "natt", "skarmtid", "skärmtid", "tonaring", "tonåring"]):
            filename = "kids-bedroom.jpg"
        elif any(x in hay for x in ["kok", "kök", "mat", "inkop", "inköp"]):
            filename = "kitchen.jpg"
        else:
            filename = "family-living.jpg"
    return f"/assets/photos/{filename}"


def tag_links(article: dict) -> str:
    tags = article_tags(article)
    if not tags:
        return ""
    return "<div class='tags'>" + "".join(f"<a href='/tag/{slugify(t)}.html'>#{esc(tag_label(t))}</a>" for t in tags[:6]) + "</div>"


def product_cards(products: list[dict], ids: list[str], affiliate_links: dict) -> str:
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
            link_html = f"<a class='buy-link' href='{esc(url)}' rel='sponsored nofollow noopener' target='_blank'>{esc(link.get('label', 'Se alternativ'))}</a>"
        cards.append(
            "<div class='mini-card'>"
            f"<span class='pill'>{esc(p['category'])}</span>"
            f"<h3>{esc(p['name'])}</h3>"
            f"<p>{esc(p['best_for'])}</p>"
            f"<small>Typiskt pris: {esc(p['price_hint'])}</small>"
            f"{link_html}"
            "</div>"
        )
    if not cards:
        return ""
    return "<section class='related-products'><h2>Prylar som nämns</h2><div class='mini-grid'>" + "".join(cards) + "</div></section>"


def everyday_block(article: dict) -> str:
    examples = article.get("examples", [])
    if not examples:
        examples = [
            "Morgonen går snabbare när samma signal betyder samma sak varje dag.",
            "Hallen blir lugnare när lampor, påminnelser och knappar sitter där familjen faktiskt passerar.",
            "Kvällen fungerar bättre när tekniken gör färre saker, men gör dem pålitligt.",
        ]
    items = "".join(f"<li>{esc(item)}</li>" for item in examples[:5])
    return f"<section class='example-box'><h2>Exempel från vardagen</h2><ul>{items}</ul></section>"


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
        tag_links(article),
        f"<img class='article-hero-image' src='{thumb_for(article)}' alt=''>",
    ]
    intro = article.get("intro")
    if intro:
        parts.append(f"<p>{esc(intro)}</p>")
    for idx, (heading, text) in enumerate(article["sections"]):
        parts.append(f"<h2>{esc(heading)}</h2><p>{esc(text)}</p>")
        if idx == 1:
            parts.append(everyday_block(article))
    parts.append(product_cards(products, article.get("products", []), affiliate_links))
    parts.append(related_articles_html(article, all_articles))
    parts.append("<p class='fineprint'>Senast uppdaterad: juli 2026.</p></article>")
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

    site_url = str(site_config.get("site_url", "")).rstrip("/")

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
        body = article_list_page(f"#{tag_label(tag)}", f"Artiklar taggade med {tag_label(tag)}.", tagged_articles, "Filtrera artiklar efter det problem eller rum du vill lösa först.")
        render_page(f"Tagg: {tag_label(tag)}", f"Artiklar om {tag_label(tag)}.", body, SITE / "tag" / f"{slugify(tag)}.html")
    popular_tags = [t for t, _ in Counter({k: len(v) for k, v in tag_map.items()}).most_common()]
    tag_page = "<section><div class='section-title'><h1>Taggar</h1></div><p class='lead page-lead'>Välj ämne i stället för att gå via rum. Det passar bättre när du vet problemet men inte vilken pryl som löser det.</p><div class='tag-cloud'>" + "".join(
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
      <h2>Exempel: en vanlig tisdag</h2>
      <p>07.10 tänds hallen mjukt och köksskärmen visar skolväskor, gympapåse och vem som hämtar. 17.30 ligger inköpslistan synligt när någon går förbi kylen. 20.15 går barnrummet över till varmare ljus och en knapp vid sängen släcker resten.</p>
      <p>Det är den typen av små lösningar sajten bygger runt: färre öppna appar, färre muntliga påminnelser och prylar som går att förstå när man redan är trött.</p>
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

    render_page("Blogg", "Alla artiklar från Smart Familj Hemma.", article_list_page("Blogg", "Alla artiklar", articles, "Här finns både längre guider och rena köpråd. Vill du slippa blandningen finns separata sidor för guider och köpråd."), SITE / "artiklar.html")
    render_page("Guider", "Praktiska smart hem-guider för barnfamiljer.", article_list_page("Guider", "Praktiska guider", guide_articles, "Rutiner, dashboards, Home Assistant och vardagsexempel utan produktlistor i centrum."), SITE / "guider.html")
    render_page("Köpråd", "Köpguider för smart hem i barnfamiljer.", article_list_page("Köpråd", "Köpguider", buy_articles, "Här samlas sidor där produktvalet är huvudfrågan. Guiderna ligger separat."), SITE / "koprad.html")

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
            f"{link_html}</div></div>"
        )

    product_groups = [
        ("Vatten, brand och frånvaro", "Prylar som varnar när något kan bli dyrt eller farligt.", ["water-leak-sensor", "smart-smoke-detector", "door-window-sensor", "temperature-sensor"]),
        ("Barnrum och kväll", "Ljus, knappar och klimat för lugnare kvällar utan appkaos.", ["smart-bulb", "smart-button", "motion-sensor", "air-quality-sensor", "smart-blinds"]),
        ("Energi och vinter", "Mät, styr och förstå elförbrukning utan att göra hemmet obekvämt.", ["smart-plug", "smart-thermostat", "temperature-sensor"]),
        ("Kom igång med Home Assistant", "Basen för dashboard, Zigbee och de första automationerna.", ["zigbee-hub", "tablet-wall", "smart-button", "motion-sensor"]),
        ("Städning och hall", "Sådant som märks varje vecka: smulor, grus, väskor och dörrar.", ["robot-vacuum", "door-window-sensor", "smart-button", "motion-sensor"]),
    ]
    product_sections = []
    for heading, intro_text, ids in product_groups:
        cards = "".join(product_card(pid) for pid in ids)
        product_sections.append(
            f"<section><div class='section-title'><h2>{esc(heading)}</h2></div>"
            f"<p class='lead page-lead'>{esc(intro_text)}</p><div class='grid'>{cards}</div></section>"
        )
    products_page = "<section><div class='section-title'><h1>Produktkategorier</h1></div><p class='lead page-lead'>Välj efter vardagsproblem först. Produkten är bara intressant om den löser något som händer hemma på riktigt.</p></section>" + "".join(product_sections)
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
    site_url = str(site_config.get("site_url", "")).rstrip("/")
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
