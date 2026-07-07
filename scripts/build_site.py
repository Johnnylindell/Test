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
    ]
    for idx, (heading, text) in enumerate(article["sections"]):
        parts.append(f"<h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p>")
    parts.append(product_cards(products, article.get("products", []), affiliate_links))
    parts.append("<p class='fineprint'>Senast uppdaterad: juli 2026. Guiden är skriven för vanliga hem, inte för perfekta labbmiljöer.</p></article>")
    return "\n".join(parts)


def card(article: dict) -> str:
    money = " money-card" if article.get("slug") in MONEY_SLUGS else ""
    slug = article.get("slug", "")
    category = article.get("category", "")
    icon = "⌂"
    if "vatten" in slug:
        icon = "💧"
    elif "robot" in slug:
        icon = "◉"
    elif "lampa" in slug or "nattljus" in slug or "laggdags" in slug:
        icon = "✦"
    elif "dashboard" in slug or "kalender" in slug:
        icon = "▦"
    elif "zigbee" in slug or "hub" in slug:
        icon = "⌁"
    elif "knapp" in slug or "plug" in slug:
        icon = "●"
    elif "hund" in slug:
        icon = "🐾"
    elif "hyresratt" in slug:
        icon = "⌂"
    return (
        f"<div class='card{money}'>"
        f"<div class='card-art'><span>{icon}</span></div>"
        f"<span class='pill'>{html.escape(category)}</span>"
        f"<h2><a href='/artiklar/{slug}.html'>{html.escape(article['title'])}</a></h2>"
        f"<p class='muted'>{html.escape(article['description'])}</p>"
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
    for a in articles:
        out = SITE / "artiklar" / f"{a['slug']}.html"
        render_page(a["title"], a["description"], article_html(a, products, affiliate_links), out)
        c = card(a)
        cards.append(c)
        if a.get("slug") in MONEY_SLUGS:
            money_cards.append(c)

    home = """<section class='hero'>
      <div class='hero-copy'>
        <span class='eyebrow'>Smart hem för riktiga barnfamiljer</span>
        <h1>Det smarta hemmet för familjer som redan har fullt upp.</h1>
        <p class='lead'>Praktiska köpguider och Home Assistant-idéer för hallen, köket, läggningen, läckor, lampor och allt det där som brukar glömmas bort en vanlig tisdag.</p>
        <div class='actions'><a class='cta' href='/koprad.html'>Se rekommenderade prylar →</a><a class='ghost' href='/kom-igang.html'>Börja lugnt</a></div>
        <div class='trust-row'><span>✓ Inga fejkade topplistor</span><span>✓ Fokus på familjevardag</span><span>✓ Amazon-länkar tydligt märkta</span></div>
      </div>
      <div class='hero-art-wrap'><img class='hero-art' src='/assets/hero-smart-home.svg' alt='Illustration av familj, vardagsrum och smart hem-dashboard'><div class='hero-badge'>Svenska guider • uppdaterad juli 2026</div></div>
    </section>

    <section class='feature-strip'>
      <div class='feature'><div class='icon'>⌂</div><h3>Trygghet</h3><p>Vattenläcka, nattljus och tydliga varningar när något faktiskt spelar roll.</p></div>
      <div class='feature'><div class='icon'>◷</div><h3>Rutiner</h3><p>Morgon, läggning, skola och medicin utan att allt blir ännu en app.</p></div>
      <div class='feature'><div class='icon'>♧</div><h3>Energikoll</h3><p>Lampor, scheman och smarta val som inte kräver teknikhobby.</p></div>
      <div class='feature'><div class='icon'>▤</div><h3>Barnrum</h3><p>Smart belysning och nattljus som hjälper snarare än stör.</p></div>
      <div class='feature'><div class='icon'>👥</div><h3>Familjekoll</h3><p>Dashboard, kalender och köksvy där alla faktiskt passerar.</p></div>
    </section>

    <section>
      <div class='section-head'><span class='pill'>Smarta lösningar</span><h2>Guider för familjens vardag</h2><p>Inte prylar för prylarnas skull. Sidorna börjar i konkreta situationer: hallen, badrummet, köket, barnrummet och morgonen.</p></div>
      <div class='grid solution-grid'>%s</div>
    </section>

    <section>
      <div class='section-head'><span class='pill'>Välj startspår</span><h2>Vad passar hemma hos er?</h2><p>Börja där irritationen är störst. En liten fungerande lösning är bättre än ett halvklart smart hem.</p></div>
      <div class='paths'>
        <div class='path-card'><span class='pill'>Liten start</span><h3>Under 100 €</h3><p class='muted'>För dig som vill testa utan att bygga system.</p><ul><li>Smart knapp</li><li>Två lampor</li><li>En enkel sensor</li></ul><a class='ghost' href='/artiklar/billigt-smart-hem-under-100-euro.html'>Se startpaket</a></div>
        <div class='path-card popular'><span class='pill'>Mest rimligt</span><h3>Familjerutiner</h3><p class='muted'>För morgon, läggning och hallkaos.</p><ul><li>Dashboard i köket</li><li>Smarta knappar</li><li>Nattljus och påminnelser</li></ul><a class='cta' href='/koprad.html'>Välj köpråd</a></div>
        <div class='path-card'><span class='pill'>Trygghet</span><h3>Säkerhet först</h3><p class='muted'>För läckor, badrum och saker du helst vill upptäcka tidigt.</p><ul><li>Vattenläckagesensor</li><li>Tydliga larm</li><li>Dashboard-varning</li></ul><a class='ghost' href='/artiklar/basta-vattenlackagesensorer-smart-hem.html'>Se sensorer</a></div>
      </div>
    </section>

    <section>
      <div class='section-head'><span class='pill'>Köpråd</span><h2>Populära köpguider</h2><p>Kategorier som kan ge mest nytta hemma och som också passar bra för affiliate-länkar.</p></div>
      <div class='grid'>%s</div>
    </section>

    <section>
      <div class='section-head'><span class='pill'>Typiska effekter</span><h2>Små saker som märks i vardagen</h2></div>
      <div class='quote-grid'><div class='quote-card'><p>Kvällsljus gör läggningen tydligare utan att någon behöver förklara rutinen om och om igen.</p><strong>Läggning</strong></div><div class='quote-card'><p>En väggskärm i köket blir familjens gemensamma minne när kalendern i mobilen inte räcker.</p><strong>Veckoplanering</strong></div><div class='quote-card'><p>Vattenläckagesensorer är tråkiga tills de behövs. Då är tydliga larm viktigare än alla smarta effekter.</p><strong>Trygghet</strong></div></div>
    </section>

    <section class='newsletter'><div><h2>Vill du bygga vidare?</h2><p class='muted'>Börja med köpråden. När fler affiliateprogram och annonser är klara kan sajten byggas ut med fler jämförelser.</p></div><a class='cta' href='/artiklar.html'>Se alla guider</a></section>
    """ % ("".join(money_cards[:5]), "".join(money_cards[:9]))
    render_page("Smart Familj Hemma", "Smarta hem-guider för barnfamiljer: Home Assistant, familjedashboard och vardagsrutiner.", home, SITE / "index.html")

    start = """<article><span class='pill'>Börja här</span><h1>Kom igång utan att drunkna i prylar</h1>
    <p class='lead'>Det vanligaste felet är att köpa femton smarta saker och sedan försöka hitta problem åt dem. Gör tvärtom.</p>
    <h2>Välj en jobbig stund</h2><p>Ta morgonen, läggningen eller hallen. Bara en. Skriv ner vad som faktiskt går fel där: glömda väskor, fel ljus, barn som inte ser nästa steg, vuxna som tjatar tills alla blir trötta.</p>
    <h2>Bygg en lösning som syns</h2><p>För familjer vinner synliga signaler över notiser. En skärm i köket, en färg på lampan eller en knapp vid dörren gör mer nytta än en automation som bara finns i en app.</p>
    <h2>Köp inte allt direkt</h2><p>En bra första runda är en smart knapp, en lampa, en sensor och en gammal surfplatta. Om det inte hjälper i vardagen efter två veckor var problemet fel valt.</p>
    <p><a class='cta' href='/koprad.html'>Se första köpråden</a></p></article>"""
    render_page("Kom igång", "Börja med smart hem hemma utan att köpa fel prylar.", start, SITE / "kom-igang.html")

    render_page("Alla guider", "Alla guider från Smart Familj Hemma.", "<section><div class='section-head'><div><span class='pill'>Bibliotek</span><h1>Alla guider</h1></div><p class='muted'>Kort, praktiskt och skrivet för hem där vardagen redan är full.</p></div><div class='grid'>" + "".join(cards) + "</div></section>", SITE / "artiklar.html")

    render_page("Köpråd", "Köpguider för smart hem i barnfamiljer.", "<section><div class='section-head'><div><span class='pill'>Köpråd</span><h1>Köpguider som är värda att börja med</h1></div><p class='muted'>De här sidorna är byggda för sökningar där läsaren faktiskt funderar på att köpa något: lampor, knappar, sensorer, robotdammsugare och väggskärm.</p></div><div class='grid'>" + "".join(money_cards) + "</div></section>", SITE / "koprad.html")

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
    products_page = "<section><div class='section-head'><div><span class='pill'>Produktkategorier</span><h1>Prylar jag skulle börja med</h1></div><p class='muted'>Inga fejkade topplistor. Bara kategorier som brukar göra nytta i ett familjehem.</p></div><div class='grid'>" + product_html + "</div></section>"
    render_page("Produktkategorier", "Prylar som kan vara värda att börja med för ett smartare familjehem.", products_page, SITE / "produkter.html")

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
