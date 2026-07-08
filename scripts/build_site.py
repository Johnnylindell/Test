#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
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
}


def slugify(text: str) -> str:
    text = text.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def render_page(title: str, description: str, body: str, out: Path) -> None:
    page = BASE.replace("{{ title }}", html.escape(title)).replace("{{ description }}", html.escape(description)).replace("{{ body }}", body)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def product_cards(products: list[dict], ids: list[str], affiliate_links: dict) -> str:
    by_id = {p["id"]: p for p in products}
    cards = []
    for pid in ids:
        p = by_id.get(pid)
        if not p:
            continue
        link = affiliate_links.get(pid, {})
        link_html = ""
        if link.get("status") == "active" and link.get("url"):
            link_html = f"<a class='buy-link' href='{html.escape(link['url'])}' rel='sponsored nofollow noopener' target='_blank'>{html.escape(link.get('label', 'Se alternativ'))}</a>"
        cards.append(
            "<div class='mini-card'>"
            f"<span class='pill'>{html.escape(p['category'])}</span>"
            f"<h3>{html.escape(p['name'])}</h3>"
            f"<p>{html.escape(p['best_for'])}</p>"
            f"<small>Typiskt pris: {html.escape(p['price_hint'])}</small>"
            f"{link_html}"
            "</div>"
        )
    if not cards:
        return ""
    return "<section class='related-products'><h2>Prylar som nämns i guiden</h2><p class='muted'>Länkar märkta som sponsrade kan ge sajten ersättning utan extra kostnad för dig.</p><div class='mini-grid'>" + "".join(cards) + "</div></section>"


def ad_slot(label: str = "Annonsplats") -> str:
    return f"<aside class='ad-slot'><span>{html.escape(label)}</span><p>Reserverad för relevant annons, inte aktiverad.</p></aside>"


def article_html(article: dict, products: list[dict], affiliate_links: dict) -> str:
    parts = [
        "<article>",
        f"<span class='pill'>{html.escape(article['category'])}</span>",
        f"<h1>{html.escape(article['title'])}</h1>",
        f"<p class='lead'>{html.escape(article['description'])}</p>",
        f"<img class='article-hero-image' src='{thumb_for(article)}' alt=''>",
    ]
    for idx, (heading, text) in enumerate(article["sections"]):
        parts.append(f"<h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p>")
    parts.append(product_cards(products, article.get("products", []), affiliate_links))
    parts.append("<p class='fineprint'>Senast uppdaterad: juli 2026. Guiden är skriven för vanliga hem, inte för perfekta labbmiljöer.</p></article>")
    return "\n".join(parts)


def thumb_for(article: dict) -> str:
    slug = article.get("slug", "")
    category = article.get("category", "")
    if "vatten" in slug:
        return "/assets/photos/kitchen.jpg"
    if "robot" in slug:
        return "/assets/photos/vacuum-room.jpg"
    if "lampa" in slug or "nattljus" in slug or "laggdags" in slug or "barnsovrum" in slug:
        return "/assets/photos/bedroom.jpg"
    if "dashboard" in slug or "kalender" in slug or "kok" in slug:
        return "/assets/photos/tablet-desk.jpg"
    if "zigbee" in slug or "hub" in slug or "aqara" in slug or "ikea" in slug or "home-assistant" in slug:
        return "/assets/photos/tech-desk.jpg"
    if "knapp" in slug or "plug" in slug or "under-100" in slug:
        return "/assets/photos/living-room.jpg"
    if "hund" in slug or "hyresratt" in slug:
        return "/assets/photos/hallway.jpg"
    if "rutin" in slug or category == "rutiner":
        return "/assets/photos/cozy-room.jpg"
    return "/assets/photos/living-room.jpg"


def card(article: dict, large: bool = False) -> str:
    money = " money-card" if article.get("slug") in MONEY_SLUGS else ""
    size = " card-large" if large else ""
    slug = article.get("slug", "")
    category = article.get("category", "")
    return (
        f"<div class='card{money}{size}'>"
        f"<a class='card-image' href='/artiklar/{slug}.html'><img src='{thumb_for(article)}' alt=''></a>"
        f"<div class='card-body'><span class='pill'>{html.escape(category)}</span>"
        f"<h2><a href='/artiklar/{slug}.html'>{html.escape(article['title'])}</a></h2>"
        f"<p>{html.escape(article['description'])}</p></div>"
        "</div>"
    )


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    assets_src = ROOT / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, SITE / "assets")
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    affiliate_links = json.loads(AFFILIATE_LINKS.read_text(encoding="utf-8")) if AFFILIATE_LINKS.exists() else {}
    site_config = json.loads(SITE_CONFIG.read_text(encoding="utf-8")) if SITE_CONFIG.exists() else {}

    cards = []
    money_cards = []
    by_slug = {}
    for a in articles:
        by_slug[a.get("slug")] = a
        out = SITE / "artiklar" / f"{a['slug']}.html"
        render_page(a["title"], a["description"], article_html(a, products, affiliate_links), out)
        c = card(a)
        cards.append(c)
        if a.get("slug") in MONEY_SLUGS:
            money_cards.append(c)

    featured_slugs = [
        "basta-vattenlackagesensorer-smart-hem",
        "smart-kok-for-barnfamiljer",
        "basta-smarta-nattljus-for-barn",
    ]
    featured_cards = "".join(card(by_slug[s], large=True) for s in featured_slugs if s in by_slug)

    home = """
    <section class='hero'>
      <div class='hero-main'>
        <img src='/assets/photos/hero-home.jpg' alt='Ljust skandinaviskt hem'>
        <div class='hero-copy'>
          <span class='kicker'>Smart hem för barnfamiljer</span>
          <h1>Smarta prylar som löser vardagsproblem.</h1>
          <p class='lead'>Köpguider, jämförelser och Home Assistant-idéer för kök, barnrum, hall, nattljus, läckor och robotdammsugare.</p>
          <div class='actions'><a class='cta' href='/artiklar.html'>Läs bloggen</a><a class='ghost' href='/koprad.html'>Gå till köpråd</a></div>
        </div>
      </div>
      <div class='hero-side'>
        <a class='side-card' href='/artiklar/basta-vattenlackagesensorer-smart-hem.html'><img src='/assets/photos/kitchen.jpg' alt='Kök'><div><span class='kicker'>Säkerhet</span><h2>Vattenläckagesensorer</h2></div></a>
        <a class='side-card' href='/artiklar/basta-smarta-nattljus-for-barn.html'><img src='/assets/photos/cozy-room.jpg' alt='Vardagsrum i kvällsljus'><div><span class='kicker'>Barnrum</span><h2>Nattljus som inte väcker alla</h2></div></a>
      </div>
    </section>

    <nav class='category-nav' aria-label='Kategorier'>
      <a href='/koprad.html'>Köpguider</a>
      <a href='/artiklar/basta-vattenlackagesensorer-smart-hem.html'>Säkerhet</a>
      <a href='/artiklar/basta-smarta-nattljus-for-barn.html'>Barnrum</a>
      <a href='/artiklar/smart-kok-for-barnfamiljer.html'>Kök</a>
      <a href='/artiklar/bygg-familjedashboard-surfplatta.html'>Dashboard</a>
      <a href='/artiklar/zigbee-vs-wifi-smarta-prylar.html'>Zigbee</a>
      <a href='/artiklar/basta-robotdammsugare-barnfamiljer.html'>Städning</a>
    </nav>

    <section>
      <div class='section-title'><h2>Utvalt</h2><a href='/artiklar.html'>Alla guider</a></div>
      <div class='grid'>%s</div>
    </section>

    <section>
      <div class='section-title'><h2>Ämnen</h2></div>
      <div class='topic-strip'>
        <a class='topic' href='/artiklar/basta-vattenlackagesensorer-smart-hem.html'><strong>Vattenläcka</strong><span>Kök, tvätt, badrum</span></a>
        <a class='topic' href='/artiklar/basta-smarta-nattljus-for-barn.html'><strong>Nattljus</strong><span>Barnrum och hall</span></a>
        <a class='topic' href='/artiklar/smart-kok-for-barnfamiljer.html'><strong>Smart kök</strong><span>Dashboard och listor</span></a>
        <a class='topic' href='/artiklar/basta-robotdammsugare-barnfamiljer.html'><strong>Städning</strong><span>Robotar och schema</span></a>
        <a class='topic' href='/artiklar/smarta-knappar-10-anvandningar-hemma.html'><strong>Knappar</strong><span>Fysiska genvägar</span></a>
      </div>
    </section>

    <section>
      <div class='section-title'><h2>Senaste</h2><a href='/artiklar.html'>Öppna blogg</a></div>
      <div class='compact-grid'>%s</div>
    </section>

    <section>
      <div class='section-title'><h2>Köpråd</h2><a href='/koprad.html'>Alla köpråd</a></div>
      <div class='compact-grid'>%s</div>
    </section>

    <section class='newsletter'><div><h2>Börja med rätt kategori.</h2><p>Välj ett problem hemma och läs guiden innan du köper.</p></div><a href='/kom-igang.html'>Kom igång</a></section>
    """ % (featured_cards, "".join(cards[:12]), "".join(money_cards[:8]))
    render_page("Smart Familj Hemma", "Smarta hem-guider för barnfamiljer: Home Assistant, familjedashboard och vardagsrutiner.", home, SITE / "index.html")

    start = """<article><span class='pill'>Börja här</span><h1>Kom igång utan att drunkna i prylar</h1>
    <p class='lead'>Det vanligaste felet är att köpa femton smarta saker och sedan försöka hitta problem åt dem. Gör tvärtom.</p>
    <h2>Välj en jobbig stund</h2><p>Ta morgonen, läggningen eller hallen. Bara en. Skriv ner vad som faktiskt går fel där: glömda väskor, fel ljus, barn som inte ser nästa steg, vuxna som tjatar tills alla blir trötta.</p>
    <h2>Bygg en lösning som syns</h2><p>För familjer vinner synliga signaler över notiser. En skärm i köket, en färg på lampan eller en knapp vid dörren gör mer nytta än en automation som bara finns i en app.</p>
    <h2>Köp inte allt direkt</h2><p>En bra första runda är en smart knapp, en lampa, en sensor och en gammal surfplatta. Om det inte hjälper i vardagen efter två veckor var problemet fel valt.</p>
    <p><a class='cta' href='/koprad.html'>Se första köpråden</a></p></article>"""
    render_page("Kom igång", "Börja med smart hem hemma utan att köpa fel prylar.", start, SITE / "kom-igang.html")

    render_page("Alla guider", "Alla guider från Smart Familj Hemma.", "<section><div class='section-title'><h1>Alla guider</h1></div><div class='grid'>" + "".join(cards) + "</div></section>", SITE / "artiklar.html")

    render_page("Köpråd", "Köpguider för smart hem i barnfamiljer.", "<section><div class='section-title'><h1>Köpråd</h1></div><div class='grid'>" + "".join(money_cards) + "</div></section>", SITE / "koprad.html")

    product_bits = []
    for p in products:
        link = affiliate_links.get(p["id"], {})
        link_html = ""
        if link.get("status") == "active" and link.get("url"):
            link_html = f"<a class='buy-link' href='{html.escape(link['url'])}' rel='sponsored nofollow noopener' target='_blank'>{html.escape(link.get('label', 'Se alternativ'))}</a>"
        product_bits.append(
            "<div class='card product-card'>"
            f"<span class='pill'>{html.escape(p['category'])}</span>"
            f"<h2>{html.escape(p['name'])}</h2>"
            f"<p>{html.escape(p['best_for'])}</p>"
            f"<p class='muted'>Typiskt pris: {html.escape(p['price_hint'])}</p>"
            f"<p class='fineprint'>{html.escape(p.get('note', ''))}</p>"
            f"{link_html}"
            "</div>"
        )
    product_html = "".join(product_bits)
    products_page = "<section><div class='section-title'><h1>Prylar</h1></div><div class='grid'>" + product_html + "</div></section>"
    render_page("Produktkategorier", "Prylar för smart hem i barnfamiljer.", products_page, SITE / "produkter.html")

    about = """<article><h1>Om Smart Familj Hemma</h1>
    <p class='lead'>Den här sajten handlar om smart hem där det faktiskt bor folk: barn, trötta vuxna, hund, tvätt, skolväskor och middagar som inte alltid går enligt plan.</p>
    <p>Jag är mer intresserad av lugnare vardag än av perfekta dashboards. Om en automation inte används av familjen är den inte klar, hur snygg den än ser ut.</p>
    <h2>Principen</h2><p>Börja med en verklig friktion. Lös den enkelt. Vänta. Bygg vidare först när det märks att lösningen hjälper.</p></article>"""
    render_page("Om", "Om Smart Familj Hemma.", about, SITE / "om.html")

    disclosure = """<article><h1>Transparens</h1>
    <p>Smart Familj Hemma använder affiliate-länkar, bland annat via Amazon Associates. Som Amazon-partner tjänar sajten pengar på kvalificerade köp.</p>
    <p>Det kostar inte extra för dig att använda en sådan länk.</p>
    <p>Rekommendationer ska bygga på praktisk nytta i ett familjehem: stabilitet, pris, enkelhet och hur lite underhåll produkten kräver.</p>
    <h2>Annonser</h2><p>Annonser ska märkas tydligt och får inte blandas ihop med redaktionella rekommendationer.</p></article>"""
    render_page("Transparens", "Transparens om länkar, annonser och rekommendationer.", disclosure, SITE / "affiliate.html")

    privacy = """<article><h1>Integritet</h1>
    <p>Den här versionen av sajten samlar inte in personuppgifter, har inga formulär och sätter inga egna cookies.</p>
    <p>Om analys, annonser eller affiliate-nätverk läggs till senare ska den här sidan uppdateras först.</p></article>"""
    render_page("Integritet", "Integritetspolicy för Smart Familj Hemma.", privacy, SITE / "integritet.html")

    paths = ["/", "/kom-igang.html", "/artiklar.html", "/koprad.html", "/produkter.html", "/om.html", "/affiliate.html", "/integritet.html"] + [f"/artiklar/{a['slug']}.html" for a in articles]
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
