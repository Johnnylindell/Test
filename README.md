# Smart Familj Hemma

En svensk affiliate-/SEO-sajt om smart hem, Home Assistant, familjedashboard och ADHD-vänliga vardagsrutiner för barnfamiljer.

## Viktigt

Det här är en lokal MVP. Den publicerar inget, skickar inget och använder bara affiliate-placeholder-länkar tills Johnny godkänner riktiga affiliate-konton/länkar.

## Bygg sajten

```bash
cd /home/johnn/smart-family-affiliate-site
python3 scripts/build_site.py
python3 -m http.server 8787 -d site
```

Öppna:

```text
http://127.0.0.1:8787/
```

## Veckorapport / nya artikelidéer

```bash
python3 scripts/weekly_ideas.py
```

Rapport sparas i `reports/`.

## Monetisering

1. Affiliate-länkar för smart hem-produkter.
2. Digital produkt: Family Dashboard template.
3. Lead-gen: hjälp med installation/dashboard.

## Approval gates

Kräver godkännande innan:

- riktiga affiliate-länkar läggs in
- domän köps
- sajt publiceras
- annonser köps
- outbound/cold outreach skickas
