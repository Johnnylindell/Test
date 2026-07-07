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
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")


def slugify(text: str) -> str:
    text = text.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def render_page(title: str, description: str, body: str, out: Path) -> None:
    page = BASE.replace("{{ title }}", html.escape(title)).replace("{{ description }}", html.escape(description)).replace("{{ body }}", body)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


def product_cards(products: list[dict], ids: list[str]) -> str:
    by_id = {p["id"]: p for p in products}
    cards = []
    for pid in ids:
        p = by_id.get(pid)
        if not p:
            continue
        cards.append(
            "<div class='mini-card'>"
            f"<span class='pill'>{html.escape(p['category'])}</span>"
            f"<h3>{html.escape(p['name'])}</h3>"
            f"<p>{html.escape(p['best_for'])}</p>"
            f"<small>Typiskt pris: {html.escape(p['price_hint'])}</small>"
            "</div>"
        )
    if not cards:
        return ""
    return "<section class='related-products'><h2>Prylar som nämns i guiden</h2><p class='muted'>Inga köplänkar än. Jag lägger hellre in riktiga rekommendationer än låtsaslänkar.</p><div class='mini-grid'>" + "".join(cards) + "</div></section>"


def article_html(article: dict, products: list[dict]) -> str:
    parts = [
        "<article>",
        f"<span class='pill'>{html.escape(article['category'])}</span>",
        f"<h1>{html.escape(article['title'])}</h1>",
        f"<p class='lead'>{html.escape(article['description'])}</p>",
    ]
    for heading, text in article["sections"]:
        parts.append(f"<h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p>")
    parts.append(product_cards(products, article.get("products", [])))
    parts.append("<p class='fineprint'>Senast uppdaterad: juli 2026. Guiden är skriven för vanliga hem, inte för perfekta labbmiljöer.</p></article>")
    return "\n".join(parts)


def card(article: dict) -> str:
    return (
        "<div class='card'>"
        f"<span class='pill'>{html.escape(article['category'])}</span>"
        f"<h2><a href='/artiklar/{article['slug']}.html'>{html.escape(article['title'])}</a></h2>"
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

    cards = []
    for a in articles:
        out = SITE / "artiklar" / f"{a['slug']}.html"
        render_page(a["title"], a["description"], article_html(a, products), out)
        cards.append(card(a))

    home = """<section class='hero hero-graphic'>
      <div class='hero-copy'>
        <span class='eyebrow'>Smart hem som familjen faktiskt använder</span>
        <h1>Färre tappade trådar. Mindre tjat. Lite mer ordning hemma.</h1>
        <p class='lead'>Guider för dig som vill använda Home Assistant, väggskärm och enkla sensorer utan att förvandla hemmet till ett evighetsprojekt. Fokus är hallen, morgonen, läggningen och sakerna som annars glöms bort.</p>
        <div class='actions'><a class='cta' href='/kom-igang.html'>Börja här</a><a class='ghost' href='/artiklar.html'>Bläddra bland guider</a></div>
      </div>
      <img class='hero-art' src='/assets/hero-family-dashboard.svg' alt='Illustration av familj, kök och väggdashboard'>
    </section>

    <section class='note-panel editorial-panel'>
      <div><span class='pill'>Kort sagt</span><h2>Det här är inte en prylblogg för tekniknördar.</h2></div>
      <p>Jag skriver om smart hem ur familjevinkel: vad som märks i hallen klockan 07:35, vad som hjälper vid läggning och vad som bara blir ännu en app att underhålla. Ibland är bästa rådet att köpa en knapp. Ibland är det att låta bli.</p>
    </section>

    <section class='visual-band'>
      <div class='visual-card'><img src='/assets/routine-cards.svg' alt='Illustration av morgon- och kvällskort'><h2>Rutiner ska synas</h2><p>En färg på lampan, en knapp vid dörren eller en checklista på väggen slår ofta ännu en notis i mobilen.</p></div>
      <div class='visual-card'><img src='/assets/product-shelf.svg' alt='Illustration av smart hem-prylar'><h2>Köp färre saker</h2><p>Två bra placerade prylar kan göra mer nytta än tio som hamnar i en låda.</p></div>
    </section>

    <section>
      <div class='section-head'><div><span class='pill'>Populärt</span><h2>Guider att börja med</h2></div><p class='muted'>Läs dessa först om du vill bygga något användbart hemma, inte bara något som ser snyggt ut i en demo.</p></div>
      <div class='grid'>%s</div>
    </section>

    <section class='split'>
      <div><span class='pill'>Startpaket</span><h2>En vettig första setup</h2><p class='muted'>Börja smått. En väggskärm, två lampor, två knappar och en sensor räcker långt om de sitter på rätt plats.</p></div>
      <div class='checklist'>
        <p>Hallknapp för "vi går hemifrån"</p>
        <p>Kvällsljus i barnrum</p>
        <p>Veckovy i köket</p>
        <p>Nattljus med rörelsesensor</p>
        <p>Inköpslista som syns utan att öppna mobilen</p>
      </div>
    </section>
    """ % "".join(cards[:6])
    render_page("Smart Familj Hemma", "Smarta hem-guider för barnfamiljer: Home Assistant, familjedashboard och vardagsrutiner.", home, SITE / "index.html")

    start = """<article><span class='pill'>Börja här</span><h1>Kom igång utan att drunkna i prylar</h1>
    <p class='lead'>Det vanligaste felet är att köpa femton smarta saker och sedan försöka hitta problem åt dem. Gör tvärtom.</p>
    <h2>Välj en jobbig stund</h2><p>Ta morgonen, läggningen eller hallen. Bara en. Skriv ner vad som faktiskt går fel där: glömda väskor, fel ljus, barn som inte ser nästa steg, vuxna som tjatar tills alla blir trötta.</p>
    <h2>Bygg en lösning som syns</h2><p>För familjer vinner synliga signaler över notiser. En skärm i köket, en färg på lampan eller en knapp vid dörren gör mer nytta än en automation som bara finns i en app.</p>
    <h2>Köp inte allt direkt</h2><p>En bra första runda är en smart knapp, en lampa, en sensor och en gammal surfplatta. Om det inte hjälper i vardagen efter två veckor var problemet fel valt.</p>
    <p><a class='cta' href='/artiklar/home-assistant-for-familjer-nyborjarguide.html'>Läs nybörjarguiden</a></p></article>"""
    render_page("Kom igång", "Börja med smart hem hemma utan att köpa fel prylar.", start, SITE / "kom-igang.html")

    render_page("Alla guider", "Alla guider från Smart Familj Hemma.", "<section><div class='section-head'><div><span class='pill'>Bibliotek</span><h1>Alla guider</h1></div><p class='muted'>Kort, praktiskt och skrivet för hem där vardagen redan är full.</p></div><div class='grid'>" + "".join(cards) + "</div></section>", SITE / "artiklar.html")

    product_html = "".join(
        "<div class='card product-card'>"
        f"<span class='pill'>{html.escape(p['category'])}</span>"
        f"<h2>{html.escape(p['name'])}</h2>"
        f"<p>{html.escape(p['best_for'])}</p>"
        f"<p class='muted'>Typiskt pris: {html.escape(p['price_hint'])}</p>"
        f"<p class='fineprint'>{html.escape(p.get('note', ''))}</p>"
        "</div>"
        for p in products
    )
    products_page = "<section><div class='section-head'><div><span class='pill'>Köpråd</span><h1>Prylar jag skulle börja med</h1></div><p class='muted'>Inga låtsaslänkar. Inga fejkade topplistor. Bara kategorier som brukar göra nytta i ett familjehem.</p></div><div class='grid'>" + product_html + "</div></section>"
    render_page("Köpråd", "Prylar som kan vara värda att börja med för ett smartare familjehem.", products_page, SITE / "produkter.html")

    about = """<article><h1>Om Smart Familj Hemma</h1>
    <p class='lead'>Den här sajten handlar om smart hem där det faktiskt bor folk: barn, trötta vuxna, hund, tvätt, skolväskor och middagar som inte alltid går enligt plan.</p>
    <p>Jag är mer intresserad av lugnare vardag än av perfekta dashboards. Om en automation inte används av familjen är den inte klar, hur snygg den än ser ut.</p>
    <h2>Principen</h2><p>Börja med en verklig friktion. Lös den enkelt. Vänta. Bygg vidare först när det märks att lösningen hjälper.</p></article>"""
    render_page("Om", "Om Smart Familj Hemma.", about, SITE / "om.html")

    disclosure = """<article><h1>Transparens</h1>
    <p>Smart Familj Hemma kan längre fram använda affiliate-länkar. Om du köper via en sådan länk kan sajten få provision utan extra kostnad för dig.</p>
    <p>Just nu länkar sajten inte vidare till butiker. Jag vill hellre vänta än fylla sidorna med dåliga köplänkar.</p>
    <h2>Hur rekommendationer ska väljas</h2><p>Produkter ska rekommenderas för att de verkar praktiska i ett familjehem: stabilitet, pris, enkelhet och hur lite underhåll de kräver. Ersättning får inte styra vad som hamnar högst.</p></article>"""
    render_page("Transparens", "Transparens om länkar och rekommendationer.", disclosure, SITE / "affiliate.html")

    privacy = """<article><h1>Integritet</h1>
    <p>Den här versionen av sajten samlar inte in personuppgifter, har inga formulär och sätter inga egna cookies.</p>
    <p>Om nyhetsbrev, analys, betalning eller affiliate-nätverk läggs till senare ska den här sidan uppdateras först.</p></article>"""
    render_page("Integritet", "Integritetspolicy för Smart Familj Hemma.", privacy, SITE / "integritet.html")

    template = """<article><span class='pill'>Digitalt startpaket</span><h1>Familjedashboard startpaket</h1>
    <p class='lead'>En enkel mall för familjer som vill få upp en veckovy på väggen utan att bygga allt från noll.</p>
    <h2>Vad paketet innehåller</h2><ul><li>HTML-mall för väggskärm</li><li>exempeldata för veckovy</li><li>morgon- och kvällsrutiner</li><li>inköpslista</li><li>kort installationsguide</li></ul>
    <h2>Status</h2><p>Första versionen är byggd som zip-fil. Den behöver bara kopplas till en betalplattform innan den kan säljas.</p>
    <p><a class='ghost' href='/artiklar/bygg-familjedashboard-surfplatta.html'>Läs guiden om väggdashboard</a></p></article>"""
    render_page("Familjedashboard startpaket", "Digitalt startpaket för familjedashboard.", template, SITE / "dashboard-template.html")

    sitemap = "\n".join(["/", "/kom-igang.html", "/artiklar.html", "/produkter.html", "/dashboard-template.html", "/om.html", "/affiliate.html", "/integritet.html"] + [f"/artiklar/{a['slug']}.html" for a in articles])
    (SITE / "sitemap.txt").write_text(sitemap + "\n", encoding="utf-8")
    print(f"Built {len(articles)} articles into {SITE}")


if __name__ == "__main__":
    main()
