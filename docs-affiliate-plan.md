# Affiliate-plan

## Viktig gräns

Jag kan inte skapa affiliate-konton åt dig eftersom de kräver personliga uppgifter, betalningsuppgifter, skatteinformation och godkännande av villkor. Jag har därför förberett:

- affiliate-programlista i `data/affiliate_programs.json`
- produktdatabas med `AFFILIATE_PLACEHOLDER_*`
- disclosure-text på sajten
- ansökningsunderlag nedan

När du har skapat konton och fått riktiga länkar kan jag byta in dem i `data/products.json`.

## Rekommenderad ordning

1. Publicera sajten först.
2. Ansök till Adtraction.
3. Ansök till Amazon Associates.
4. Lägg in riktiga länkar på de produktkategorier som matchar annonsörer.
5. Mät klick innan du skriver fler artiklar.

## Kort beskrivning att använda i ansökningar

**Namn på webbplats:** Smart Familj Hemma

**Beskrivning:**
Smart Familj Hemma är en svensk guidesajt för barnfamiljer som vill använda smart hem, Home Assistant, väggdashboard och enkla vardagsautomationer för att minska stress och skapa bättre rutiner. Sajten publicerar praktiska guider, jämförelser och köpguider inom smart belysning, sensorer, smarta knappar, robotdammsugare och familjedashboards.

**Målgrupp:**
Svenska och nordiska barnfamiljer, teknikintresserade föräldrar och hushåll som vill ha praktisk vardagsautomation.

**Trafikkällor:**
SEO, organiskt sök, eventuellt sociala medier och relevanta forum efter godkännande.

**Innehållstyper:**
Köpguider, jämförelser, nybörjarguider, praktiska rutinguider och digitala templates.

## Disclosure-text

Sajten använder denna grundtext:

> Vissa länkar kan vara affiliate-länkar. Det betyder att vi kan få provision om du köper via länken, utan extra kostnad för dig. Rekommendationer ska baseras på praktisk nytta för barnfamiljer, inte bara provision.

## När riktiga länkar finns

Uppdatera `data/products.json`:

```json
"affiliate_url": "https://riktig-affiliate-lank.example/..."
```

Bygg sedan om sajten:

```bash
python3 scripts/build_site.py
```
