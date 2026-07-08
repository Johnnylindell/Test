#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "content" / "articles" / "articles.json"
articles = json.loads(path.read_text(encoding="utf-8"))
by_slug = {a["slug"]: a for a in articles}

def tags_for(slug: str, category: str) -> list[str]:
    tags = []
    if category == "köpguide": tags.append("kopguide")
    else: tags.append(category)
    checks = {
        "home-assistant": ["home-assistant", "home assistant"],
        "sensorer": ["sensor", "rorelse", "rörelse", "narvaro", "vatten"],
        "belysning": ["lampa", "lampor", "ljus", "nattljus"],
        "barnrum": ["barn", "sovrum", "nattljus"],
        "kok": ["kok", "kök", "inkop", "inköp", "disk", "mat"],
        "zigbee": ["zigbee", "aqara", "ikea", "hue", "hub"],
        "städning": ["robot", "dammsugare", "stad", "städ"],
        "vattenlackage": ["vatten", "lack", "läck"],
        "budget": ["budget", "100-euro", "billigt"],
        "hyresratt": ["hyresratt", "hyresrätt"],
        "hund": ["hund"],
        "morgon": ["morgon", "skola"],
        "laggdags": ["laggdags", "läggdags", "natt"],
        "kalender": ["kalender", "veckovy"],
        "notiser": ["notis", "paminn", "påminn"],
        "knappar": ["knapp"],
        "pluggar": ["plug"],
    }
    hay = slug.lower()
    for tag, needles in checks.items():
        if any(n in hay for n in needles): tags.append(tag)
    return sorted(dict.fromkeys(tags))[:8]

def examples_for(a: dict) -> list[str]:
    slug = a["slug"]
    if "vatten" in slug:
        return ["Sensorn ligger under diskmaskinen och skickar larm innan vattnet hunnit ut i hallen.", "En extra sensor under handfatet fångar droppet som annars märks först när lådan luktar fukt.", "När barnen badar kan ett larm i tvättstugan vara skillnaden mellan handduk och försäkringsärende."]
    if "morgon" in slug or "skola" in slug:
        return ["Kökslampan går från varm till klar när det är dags att ta på ytterkläder.", "Väggskärmen visar bara tre saker: frukost, tandborste, väska.", "Knappen i hallen markerar 'klar' så ingen behöver ropa genom huset."]
    if "natt" in slug or "laggdags" in slug or "sovrum" in slug:
        return ["Barnrummet får varmare ljus efter kvällsmat och släcks stegvis i stället för tvärt.", "Ett svagt nattljus tänds i hallen utan att resten av familjen vaknar.", "Godnatt-knappen stänger kökslampor och lämnar bara en liten väg till badrummet."]
    if "robot" in slug or "dammsugare" in slug:
        return ["Robotdammsugaren kör efter lämning när lego och strumpor hunnit plockas upp.", "Köket får en kort extra körning efter middag, inte hela huset.", "Hallen städas oftare under grusperioden och mer sällan på sommaren."]
    if "dashboard" in slug or "kalender" in slug or "veckovy" in slug:
        return ["Alla ser på samma skärm vem som hämtar och vad som ska med till skolan.", "Inköpslistan står kvar i köket där man märker att mjölken är slut.", "Söndagskvällen blir fem minuters genomgång i stället för måndagsöverraskningar."]
    if "kok" in slug or "inkop" in slug:
        return ["En knapp vid kylen lägger till standardvaror på listan utan att någon tar fram mobilen.", "Köksskärmen visar middag och nästa kalenderhändelse medan maten lagas.", "Diskmaskinsensor och vattenlarm ligger där skadan faktiskt börjar."]
    if "zigbee" in slug or "hub" in slug or "aqara" in slug:
        return ["När internet strular ska hallknappen fortfarande kunna tända lampan.", "Billiga sensorer blir mer användbara när de slipper ligga på hemmets wifi.", "En stabil hubb gör att barnrummets kvällsljus känns som en del av huset, inte som en app."]
    return ["Placera styrningen där vanan redan sker, inte där tekniken ser snyggast ut.", "Testa lösningen på en stressig vardag, inte bara när du har tid att pilla.", "Om familjen inte använder den efter två veckor behöver lösningen bli enklare."]

for a in articles:
    a.setdefault("tags", tags_for(a["slug"], a.get("category", "guide")))
    a.setdefault("examples", examples_for(a))
    a.setdefault("intro", "Guiden utgår från situationer som ofta händer hemma: någon är sen, något glöms, en lampa står fel eller en pryl kräver mer uppmärksamhet än den sparar. Målet är att välja färre saker som gör tydlig nytta.")
    headings = [s[0] for s in a.get("sections", [])]
    if "Så märker du att lösningen fungerar" not in headings:
        a["sections"].append(["Så märker du att lösningen fungerar", "En bra lösning blir använd utan att någon behöver påminna familjen om den. Den syns på rätt plats, går att förstå snabbt och fortsätter fungera även när veckan är rörig."])
    if "Vanligt misstag" not in headings:
        a["sections"].append(["Vanligt misstag", "Det vanligaste misstaget är att automatisera för mycket. Börja med en signal, en knapp eller en sensor och bygg vidare först när den första lösningen faktiskt används."])

new_articles = [
  {
    "slug": "hallkaos-smart-hem-skola-forskola",
    "title": "Hallkaos före skola och förskola: smart hem som hjälper",
    "description": "Konkreta lösningar för väskor, ytterkläder, tider och sista-minuten-panik i hallen.",
    "category": "guide",
    "products": ["smart-button", "smart-bulb", "tablet-wall"],
    "tags": ["guide", "morgon", "dashboard", "knappar", "belysning"],
    "intro": "Hallen är ofta hemmets flaskhals. Alla ska ut samtidigt, någon saknar vantar, någon annan vill visa en teckning och en vuxen försöker komma ihåg jobbet. Smarta hem-lösningen ska därför vara synlig och fysisk, inte gömd i en app.",
    "examples": ["Lampan i hallen byter färg när det är tio minuter kvar.", "En checklista på väggskärmen visar väska, matlåda, nycklar och gympapåse.", "En knapp vid dörren släcker huset och markerar att alla gått."],
    "sections": [["Börja med fyra saker", "Visa bara det som faktiskt stoppar er: väska, ytterkläder, nycklar och dagens specialgrej. Mer än så blir lätt en vägg av text."], ["Fysisk knapp vid dörren", "När sista personen trycker på knappen kan lampor släckas, robotdammsugaren starta senare och dashboarden markera hemifrån-läge."], ["Ljus som tidssignal", "En färg eller ljusstyrka räcker. Grönt: gott om tid. Varmt gult: börja klä på. Rött eller starkare ljus: nu går vi."], ["Gör det mindre tjatigt", "Poängen är inte att barnen ska styras av teknik. Poängen är att familjen får en gemensam signal som inte låter som ännu en vuxen som ropar."]]
  },
  {
    "slug": "tvattstuga-sensorer-familj",
    "title": "Smart tvättstuga: sensorer som faktiskt gör nytta",
    "description": "Vattenlarm, smart plug och enkla påminnelser för tvättmaskin, torktumlare och glömda kläder.",
    "category": "guide",
    "products": ["water-leak-sensor", "smart-plug", "smart-button"],
    "tags": ["guide", "vattenlackage", "sensorer", "pluggar", "notiser"],
    "intro": "Tvättstugan är ett av de bästa rummen att börja i eftersom problemen är konkreta: vatten, fukt, glömda maskiner och kläder som behöver flyttas innan kvällen.",
    "examples": ["Vattenlarm under maskinen skickar larm direkt.", "Smart plug kan påminna när tvättmaskinen slutat dra ström.", "En knapp vid tvättkorgen kan lägga till tvättmedel på inköpslistan."],
    "sections": [["Vatten först", "Lägg en vattenläckagesensor där vatten faktiskt hamnar: under maskin, vid golvbrunn eller under vask."], ["Påminnelse utan tjat", "Mät strömförbrukning med smart plug om maskinen tillåter det. När förbrukningen faller efter ett program skickas en lugn påminnelse."], ["Undvik onödigt komplicerat", "Du behöver inte automatisera varje tvättläge. Börja med läckage och 'tvätten är klar'."], ["När det blir vardagsnytta", "Lösningen är bra när färre maskiner glöms över natten och fuktiga handdukar inte ligger kvar i mörker."]]
  },
  {
    "slug": "matplanering-dashboard-smart-kok",
    "title": "Matplanering på köksskärmen: enklare vardagsmiddag",
    "description": "Så kan en enkel dashboard visa middagar, inköpslista och vad som måste tas fram ur frysen.",
    "category": "guide",
    "products": ["tablet-wall", "smart-button"],
    "tags": ["guide", "kok", "dashboard", "kalender"],
    "intro": "Middagsstress handlar sällan om brist på recept. Ofta är problemet att ingen ser planen förrän alla redan är hungriga.",
    "examples": ["Köksskärmen visar dagens middag redan på morgonen.", "En rad säger 'ta fram kyckling ur frysen' innan det är för sent.", "Knappen vid kylen lägger till standardvaror direkt."],
    "sections": [["Visa mindre", "Dagens middag, morgondagens middag och tre viktigaste inköpen räcker långt."], ["Placera där beslutet tas", "Skärmen ska synas där någon öppnar kyl, packar varor eller lagar mat."], ["Gör listan enkel", "En knapp för mjölk, bröd eller blöjor kan vara mer användbar än en avancerad receptintegration."], ["Koppla till kalendern", "Om träning slutar sent ska middagen vara enkel. En bra dashboard gör den kopplingen synlig." ]]
  },
  {
    "slug": "barnens-skarmtid-smarta-hem-signaler",
    "title": "Skärmtid utan bråk: använd lampor och rutiner som signaler",
    "description": "Inte en magisk lösning, men tydliga övergångar kan göra avslut mindre laddade.",
    "category": "guide",
    "products": ["smart-bulb", "smart-button", "tablet-wall"],
    "tags": ["guide", "barnrum", "rutiner", "belysning"],
    "intro": "Smarta hem ska inte uppfostra barn. Men tydliga signaler kan göra övergången från skärm till mat, läxa eller läggning mindre plötslig.",
    "examples": ["Lampan blir varm gul tio minuter före avslut.", "Dashboarden visar nästa steg: kvällsmål, pyjamas, tandborste.", "En knapp markerar när skärmen är undanlagd och tänder läslampan."],
    "sections": [["Förvarna visuellt", "En mild ljusförändring fungerar ofta bättre än att ropa från köket."], ["Gör nästa steg tydligt", "Barn fastnar lätt i avslutet om nästa aktivitet är vag. Visa konkret vad som händer efter skärmen."], ["Undvik straffkänsla", "Tekniken ska inte kännas som övervakning. Den ska göra övergången förutsägbar."], ["När det fungerar", "Du märker det när färre avslut blir diskussioner och fler blir rutiner." ]]
  },
  {
    "slug": "basta-smarta-pluggar-energi-familj",
    "title": "Bästa smarta pluggarna för familjer: energi, lampor och påminnelser",
    "description": "Vad en smart plug kan göra hemma och när den inte är rätt val.",
    "category": "köpguide",
    "products": ["smart-plug", "smart-button"],
    "tags": ["kopguide", "pluggar", "budget", "kok"],
    "intro": "Smarta pluggar är billiga och lockande, men de ska användas där de faktiskt gör vardagen enklare: lampor, kaffehörna, tvättmaskinspåminnelser och energikoll.",
    "examples": ["En plugg vid kaffemaskinen stänger av efter morgonruschen.", "En energimätande plugg kan se när tvättmaskinen är klar.", "En vanlig golvlampa blir del av kvällsläget utan att byta armatur."],
    "sections": [["Välj rätt typ", "För lampor räcker ofta enkel av/på. För tvätt eller energikoll behövs energimätning."], ["Tänk säkerhet", "Använd inte billiga pluggar till tunga laster om de inte är tydligt specade för det."], ["Bra första användning", "Gör en gammal lampa smart och styr den med knapp. Då märks nyttan direkt."], ["När du ska låta bli", "Om apparaten har känslig elektronik eller kräver fysisk knapptryckning efter strömavbrott är smart plug ofta fel väg." ]]
  },
  {
    "slug": "sensorer-i-badrum-natt-och-vatten",
    "title": "Sensorer i badrum: nattljus, fukt och vattenlarm",
    "description": "Så gör du badrummet smartare utan att göra det komplicerat.",
    "category": "guide",
    "products": ["motion-sensor", "water-leak-sensor", "smart-bulb"],
    "tags": ["guide", "sensorer", "vattenlackage", "belysning", "laggdags"],
    "intro": "Badrummet har två tydliga smart hem-problem: ingen vill bli bländad på natten och ingen vill upptäcka vatten för sent.",
    "examples": ["Rörelsesensor tänder svagt ljus efter 22.00.", "Vattenlarm ligger under handfatet eller vid toalettens anslutning.", "Fläkten kan påminnas via fuktnivå om systemet redan stödjer det."],
    "sections": [["Nattläge", "Låt badrumsljuset tändas svagt på natten och normalt på dagen."], ["Vattenlarm där det börjar", "Sensorer gör mest nytta under vask, vid rörkopplingar och nära maskiner."], ["Fukt utan överbygge", "Fuktsensor kan vara bra, men börja inte med avancerad ventilation om ett enkelt larm löser behovet."], ["Familjetestet", "Om barnen kan gå på toaletten utan att väcka alla har lösningen redan gjort nytta." ]]
  }
]

for a in new_articles:
    if a["slug"] not in by_slug:
        articles.append(a)

path.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"articles={len(articles)}")
