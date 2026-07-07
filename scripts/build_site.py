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


def product_table(products: list[dict], ids: list[str]) -> str:
    by_id = {p["id"]: p for p in products}
    rows = []
    for pid in ids:
        p = by_id.get(pid)
        if not p:
            continue
        rows.append(
            f"<tr><td><b>{html.escape(p['name'])}</b></td><td>{html.escape(p['price_hint'])}</td>"
            f"<td>{html.escape(p['best_for'])}</td><td><a href='{html.escape(p['affiliate_url'])}' rel='sponsored nofollow'>Se alternativ</a></td></tr>"
        )
    if not rows:
        return ""
    return "<h2>Relevanta produkter</h2><table><tr><th>Produkt</th><th>Prisidé</th><th>Bäst för</th><th>Länk</th></tr>" + "".join(rows) + "</table>"


def article_html(article: dict, products: list[dict]) -> str:
    parts = [f"<article><span class='pill'>{html.escape(article['category'])}</span><h1>{html.escape(article['title'])}</h1><p class='muted'>{html.escape(article['description'])}</p>"]
    for heading, text in article["sections"]:
        parts.append(f"<h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p>")
    parts.append(product_table(products, article.get("products", [])))
    parts.append("<p class='muted'>Obs: produktlänkar är placeholders i MVP:n och ska bytas först efter affiliate-godkännande.</p></article>")
    return "\n".join(parts)


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))

    cards = []
    for a in articles:
        out = SITE / "artiklar" / f"{a['slug']}.html"
        render_page(a["title"], a["description"], article_html(a, products), out)
        cards.append(f"<div class='card'><span class='pill'>{html.escape(a['category'])}</span><h2><a href='/artiklar/{a['slug']}.html'>{html.escape(a['title'])}</a></h2><p class='muted'>{html.escape(a['description'])}</p></div>")

    home = """
    <section class='hero'>
      <span class='eyebrow'>🏡 Smart hem för riktiga familjer</span>
      <h1>Lugnare vardag med Home Assistant, familjedashboard och tydliga rutiner.</h1>
      <p class='muted'>Svenska guider för barnfamiljer som vill ha praktisk automation: mindre tjat, färre glömda saker och tydligare morgnar utan mer teknikstress.</p>
      <div class='actions'><a class='cta' href='/artiklar.html'>Läs guiderna</a><a class='ghost' href='/dashboard-template.html'>Se dashboard-template</a></div>
      <div class='stats'><div class='stat'><b>20</b><span>lokala guider</span></div><div class='stat'><b>0 €</b><span>spenderat hittills</span></div><div class='stat'><b>0</b><span>riktiga affiliate-länkar</span></div></div>
    </section>
    <section>
      <div class='section-head'><div><span class='pill'>Start här</span><h2>Populära guider</h2></div><p class='muted'>Evergreen-artiklar som senare kan kopplas till affiliate-länkar när konton och publicering är godkända.</p></div>
      <div class='grid'>%s</div>
    </section>
    <section>
      <div class='section-head'><div><span class='pill'>Affärsmodell</span><h2>Hur den kan tjäna pengar</h2></div><p class='muted'>Inte magi. Trafik först, monetisering sedan.</p></div>
      <div class='grid'>
        <div class='card'><span class='pill'>1</span><h3>Affiliate</h3><p class='muted'>Köpguider för sensorer, Zigbee, tablets och robotdammsugare. Placeholder-länkar byts först efter godkännande.</p></div>
        <div class='card'><span class='pill'>2</span><h3>Digital produkt</h3><p class='muted'>Family Dashboard Template: enkel nedladdning när sajten har trafik och köpvillkor är klara.</p></div>
        <div class='card'><span class='pill'>3</span><h3>Lead-gen senare</h3><p class='muted'>Om du vill: intresseformulär för dashboard-hjälp. Inte aktiverat nu, ingen data samlas in.</p></div>
      </div>
    </section>
    """ % "".join(cards[:6])
    render_page("Smart Familj Hemma", "Svenska guider om smart hem, familjedashboard och ADHD-vänliga rutiner.", home, SITE / "index.html")

    render_page("Alla artiklar", "Alla guider från Smart Familj Hemma.", "<h1>Alla artiklar</h1><div class='grid'>" + "".join(cards) + "</div>", SITE / "artiklar.html")

    product_rows = "".join(
        f"<tr><td><b>{html.escape(p['name'])}</b></td><td>{html.escape(p['category'])}</td><td>{html.escape(p['price_hint'])}</td><td>{html.escape(p['best_for'])}</td><td><a href='{html.escape(p['affiliate_url'])}' rel='sponsored nofollow'>Placeholder-länk</a></td></tr>"
        for p in products
    )
    render_page("Produkter", "Produktkategorier och affiliate-placeholders.", "<h1>Produkter</h1><p class='muted'>Affiliate-placeholders tills riktiga program godkänts.</p><table><tr><th>Produkt</th><th>Kategori</th><th>Pris</th><th>Bäst för</th><th>Länk</th></tr>" + product_rows + "</table>", SITE / "produkter.html")

    about = """
    <article><h1>Om Smart Familj Hemma</h1>
    <p>Smart Familj Hemma är en svensk guidesajt för barnfamiljer som vill använda smart hem, Home Assistant och familjedashboards på ett praktiskt sätt.</p>
    <p>Målet är låg-friktionslösningar: färre glömda saker, lugnare morgnar, tydligare veckovy och mindre vardagsstress.</p>
    <h2>Redaktionell princip</h2><p>Rekommendationer ska utgå från praktisk nytta, enkelhet och robusthet – inte bara teknikintresse.</p></article>
    """
    render_page("Om Smart Familj Hemma", "Om sajten och dess redaktionella principer.", about, SITE / "om.html")

    disclosure = """
    <article><h1>Affiliate och transparens</h1>
    <p>Vissa länkar kan vara affiliate-länkar. Det betyder att sajten kan få provision om du köper via länken, utan extra kostnad för dig.</p>
    <p>I denna MVP är länkarna placeholders tills affiliate-konton godkänts och riktiga länkar lagts in.</p>
    <p>Rekommendationer ska baseras på praktisk nytta för barnfamiljer, stabilitet och rimligt pris.</p></article>
    """
    render_page("Affiliate och transparens", "Information om affiliate-länkar och transparens.", disclosure, SITE / "affiliate.html")

    privacy = """
    <article><h1>Integritet</h1>
    <p>Den statiska MVP-sajten samlar inte in personuppgifter, har inga formulär och sätter inga egna cookies.</p>
    <p>Om analys, nyhetsbrev, betalningar eller affiliate-nätverk aktiveras senare ska denna sida uppdateras innan publicering.</p></article>
    """
    render_page("Integritet", "Integritetspolicy för Smart Familj Hemma MVP.", privacy, SITE / "integritet.html")

    template = """
    <article><span class='pill'>Digital produkt</span><h1>Family Dashboard Template</h1>
    <p class='muted'>Första digitala produkten att sälja när sajten får trafik.</p>
    <h2>Vad paketet kan innehålla</h2><ul><li>HTML-dashboard</li><li>veckovy: idag + 6 dagar</li><li>inköpslista</li><li>morgon-/kvällsrutiner</li><li>installationsguide</li></ul>
    <h2>Prisidé</h2><p>9–19 € som enkel download, senare 49–99 € med installationshjälp.</p>
    <p class='muted'>Betalning ska inte aktiveras förrän Johnny godkänt Stripe/köpvillkor/GDPR-text.</p></article>
    """
    render_page("Family Dashboard Template", "Digital produktidé för familjedashboard.", template, SITE / "dashboard-template.html")

    sitemap = "\n".join(["/", "/artiklar.html", "/produkter.html", "/dashboard-template.html", "/om.html", "/affiliate.html", "/integritet.html"] + [f"/artiklar/{a['slug']}.html" for a in articles])
    (SITE / "sitemap.txt").write_text(sitemap + "\n", encoding="utf-8")
    print(f"Built {len(articles)} articles into {SITE}")


if __name__ == "__main__":
    main()
