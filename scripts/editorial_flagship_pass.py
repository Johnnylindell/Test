#!/usr/bin/env python3
"""Apply the hand-edited flagship article pass.

Kept as a script so later automated runs do not silently replace these texts with
boilerplate. It is safe to run more than once.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "content" / "articles" / "articles.json"

UPDATES = {
    "home-assistant-for-familjer-nyborjarguide": {
        "description": "En lugn start med Home Assistant: vad som behövs, vad som kan vänta och vilka tre automationer familjen faktiskt märker.",
        "intro": "Home Assistant blir lätt ett kvällsprojekt utan slut. För en familj är ett bättre mål att få en knapp, en sensor och en tydlig skärm att fungera även när ingen vill felsöka.",
        "sections": [
            ["Börja med ett enda rum", "Ta köket eller hallen först. Där passerar alla och det går snabbt att märka om lösningen hjälper. En knapp vid dörren, ett mjukt morgonljus och en synlig veckovy räcker som första version. Låt resten av huset vara vanligt tills den delen fungerar stabilt."],
            ["Hårdvaran som behövs", "Home Assistant Green är enklast om du vill slippa installera operativsystem. En befintlig mini-PC eller hemmaserver går också bra. För Zigbee behövs en kompatibel radio, till exempel Home Assistant Connect ZBT-1 eller Sonoff Zigbee 3.0 USB Dongle Plus. Placera radion en bit från datorn med USB-förlängning."],
            ["Tre första automationer", "Tänd hallen svagt före frukost, skicka ett tydligt vattenlarm med platsnamn och skapa en fysisk godnatt-knapp. De löser tre olika behov: rytm, säkerhet och avslut. Undvik att börja med avancerad närvarospårning eller trettio notiser."],
            ["Familjen ska kunna använda allt utan app", "En vanlig strömbrytare och en fysisk knapp måste fortfarande fungera. Sätt namn som 'Hall tak' och 'Vatten under diskmaskin', inte tekniska enhetsnamn. Om någon behöver leta efter rätt mobilapp har systemet gjort vardagen svårare."],
            ["Backup innan finlir", "Ta en fullständig backup när de första funktionerna fungerar och spara en kopia utanför Home Assistant-enheten. Skriv även ner var Zigbee-radion sitter och vilka lampor som måste ha ström. Den anteckningen är mer värd än ännu ett snyggt dashboardkort när något slutar svara."],
            ["När det är dags att bygga vidare", "Vänta två veckor. Lägg bara till nästa sak om familjen använder det som redan finns. Bra fortsättning är vattenlarm, temperatur i barnrum eller energimätning på en enskild apparat. Då vet du varför varje pryl finns."],
        ],
        "examples": [
            "Hallknappen tänder vanligt ljus även om Home Assistant tillfälligt är nere.",
            "Vattenlarmet säger 'vatten under diskmaskinen' i stället för ett kryptiskt sensornamn.",
            "Köksskärmen visar dagens tider och middag, inte fyrtio små tekniska mätvärden.",
        ],
    },
    "adhd-vanliga-morgonrutiner-smarta-hem": {
        "description": "En morgonrutin med ljus, tre synliga steg och en fysisk klar-knapp. Utan fler mobilnotiser.",
        "intro": "En morgon blir sällan lugnare av fler larm. Den blir lugnare när nästa steg syns där man står och när samma signal betyder samma sak varje vardag.",
        "sections": [
            ["Kartlägg de sista tjugo minuterna", "Skriv ner var morgonen faktiskt fastnar: kläder, tandborste, medicin, matsäck eller ytterkläder. Välj en enda flaskhals. Om gympapåsen glöms är en synlig rad på hallskärmen bättre än att automatisera hela huset."],
            ["Använd ljus som bakgrundssignal", "Låt köks- eller hallbelysningen ändras i tre lugna steg. Varmt ljus när det är dags att vakna, normalt arbetsljus under frukosten och ett tydligare men inte blinkande ljus tio minuter före avfärd. Färg ska stödja rutinen, inte bli en ny sak att tolka."],
            ["Visa högst tre saker", "En skärm i köket kan visa 'äta', 'tänder' och 'väska'. Det räcker. Lägg dagens avvikelse under listan, till exempel utflykt eller gympa. En komplett kalender med små färgkoder blir ofta bakgrundsbrus när tiden är knapp."],
            ["En fysisk knapp avslutar", "Sätt knappen där familjen tar på skorna. Ett tryck markerar morgonen klar och släcker onödiga lampor. Knappen ska inte kräva dubbeltryck, långtryck eller en instruktion på väggen. Det enkla trycket är hela poängen."],
            ["Bygg för dåliga dagar", "Testa rutinen när någon sovit dåligt och mjölken är slut, inte bara en lugn söndag. Ha alltid en manuell strömbrytare och låt skärmen vara läsbar även om kalenderkopplingen misslyckas. Tekniken får inte göra en sen morgon senare."],
            ["Justera efter två veckor", "Ta bort det som ingen tittar på. Flytta knappen om den inte nås naturligt. Ändra bara en signal åt gången så att familjen hinner lära sig den. En kort rutin som överlever vardagen slår en smart rutin som ständigt behöver förklaras."],
        ],
        "examples": [
            "07.25 blir hallen något ljusare. Ingen signal blinkar eller låter.",
            "På skärmen står bara 'frukost, tänder, väska' plus dagens gympapåse.",
            "Knappen vid skohyllan markerar klart och släcker köket när sista personen går.",
        ],
    },
    "familjekalender-pa-vaggskarm": {
        "description": "Bygg en familjekalender som går att läsa på tre meters håll och fortfarande är begriplig en stressig måndag.",
        "intro": "Det svåra är inte att visa kalendern på en skärm. Det svåra är att välja bort tillräckligt mycket för att någon ska titta på den.",
        "sections": [
            ["Placera skärmen där frågor uppstår", "Köket eller hallen fungerar bäst eftersom familjen redan stannar där. Undvik en vägg som bara ser snygg ut på bild. Skärmen ska kunna läsas utan att någon går fram, loggar in eller trycker på en liten meny."],
            ["Visa idag och sex dagar framåt", "Börja med dagens tider i större text. Lägg nästa sex dagar under eller bredvid. Markera vem händelsen gäller med namn eller en diskret färg, men använd inte färg som enda information. Måltid och hämtning får gärna ligga nära kalendern eftersom de ofta avgör kvällens plan."],
            ["Separera rutin från undantag", "Tandborstning och läggdags behöver inte fylla kalendern varje dag. Lägg återkommande rutiner i en liten fast yta och låt kalendern visa sådant som avviker: läkartid, gympapåse, sen arbetsdag eller utflykt."],
            ["Välj hårdvara efter platsen", "En begagnad surfplatta räcker ofta. Kontrollera skärmens ljusstyrka, laddning och hur den ska sitta säkert. Stäng av batterioptimering för dashboardappen, dölj onödiga systemknappar och sänk ljuset på kvällen. Använd inte en sliten laddkabel permanent bakom en möbel."],
            ["Gör redigering enkel", "Kalendern ska hämtas från den tjänst familjen redan använder. Lägg inte till ett nytt formulär bara för väggskärmen. Om någon ändrar en tid i mobilen ska den dyka upp utan att dashboarden måste startas om."],
            ["Mät om den används", "Efter två veckor: fråga vilka uppgifter familjen faktiskt tittar på. Ta bort resten. Om alla fortfarande frågar vem som hämtar är den informationen för liten, felplacerad eller otydlig. Designproblemet löses sällan med fler widgets."],
        ],
        "examples": [
            "Dagens hämtning står bredvid nästa kalenderhändelse i stället för längst ner på skärmen.",
            "Gympapåsen syns bara de dagar den behövs.",
            "Kvällsläget dämpar skärmen automatiskt men lämnar morgondagens första tid läsbar.",
        ],
    },
    "basta-vattenlackagesensorer-smart-hem": {
        "description": "Aqara, Shelly och Eve jämförda för diskmaskin, tvättstuga och varmvattenberedare. Med fokus på larmväg och placering.",
        "intro": "En läckagesensor är bara bra om den ligger där vattnet börjar och om larmet når någon. Radioprotokoll och app är sekundärt.",
        "sections": [
            ["Aqara Water Leak Sensor", "Den lilla Zigbee-sensorn passar bra under diskmaskin och handfat. Den kan kopplas lokalt till Home Assistant via en kompatibel Zigbee-koordinator. Fördelen är låg profil och utbytbart batteri. Kontrollera att Zigbee-nätet når golvnivå bakom skåp och att sensorn inte hamnar ovanpå ett spilltråg som leder vattnet förbi kontakterna."],
            ["Shelly Flood", "Shelly Flood använder wifi och har en kabelgivare som kan täcka en större yta. Det kan passa vid varmvattenberedare eller i ett teknikutrymme. Nackdelen är att wifi och batteritid måste fungera där sensorn placeras. Kontrollera aktuell modell och integrationsstöd före köp, eftersom Shellys sortiment förändras över tid."],
            ["Eve Water Guard", "Eve Water Guard är en nätansluten lösning med lång sensorkabel. Den passar när du vill bevaka en längre sträcka, till exempel under en köksrad eller runt en tvättmaskin. Den kostar mer och kräver ett uttag. Kontrollera Thread/Matter-stöd och kompatibilitet med ditt system för den version som säljs i din region."],
            ["Placering slår specifikationer", "Lägg sensorn vid slanganslutningar, pump, filter och framkant där vatten kan samlas. Under en diskmaskin behöver den ligga så att några droppar faktiskt når kontakterna. Testa med en fuktad trasa efter installationen och gör om testet när batteriet byts."],
            ["Bygg rätt larmkedja", "Skicka notis till de vuxna och visa exakt plats. Lägg gärna till ljud eller röd indikator hemma, men stäng inte automatiskt en apparat om lösningen inte är byggd och testad för det. Ett meddelande som bara heter 'Leak sensor 03' är inte färdigt."],
            ["Vårt val beror på hemmet", "Aqara är ett rimligt budgetval för ett redan stabilt Zigbee-nät. Shelly är intressant där wifi är starkt och kabelgivaren gör nytta. Eve passar bättre när en lång bevakad sträcka motiverar priset. Ingen av dem ersätter rätt slangar, spilltråg eller avstängningsventil."],
        ],
        "examples": [
            "Under diskmaskinen testas sensorn med fuktad trasa efter varje batteribyte.",
            "Notisen säger både rum och apparat: 'Vatten under tvättmaskinen'.",
            "En lokal varningslampa tänds även om mobilen är på ljudlöst.",
        ],
    },
    "basta-zigbee-hubbar-for-familjer": {
        "description": "Home Assistant Green, Hue Bridge och IKEA Dirigera jämförda för familjer som vill ha stabila knappar, lampor och sensorer.",
        "intro": "Rätt hubb beror mindre på antalet funktioner och mer på vem som ska sköta den när något slutar svara.",
        "sections": [
            ["Home Assistant Green med Zigbee-radio", "Green tillsammans med Home Assistant Connect ZBT-1 ger störst frihet och lokal kontroll. Det passar den som accepterar backup, uppdateringar och lite felsökning. Använd en USB-förlängningskabel så radion kommer bort från dator och USB 3-störningar. Green har inte inbyggd Zigbee-radio, så räkna in den i priset."],
            ["Philips Hue Bridge", "Hue Bridge är enkel och stabil för Hue-lampor, knappar och sensorer. Appen är begriplig och familjen kan fortsätta använda vanliga Hue-brytare. Den är mindre flexibel för blandade Zigbee-produkter. Välj den när belysning är huvudmålet och du inte vill administrera ett helt Home Assistant-system."],
            ["IKEA Dirigera", "Dirigera passar bra om hemmet främst använder IKEA-lampor, pluggar, gardiner och sensorer. Produkterna är lätta att köpa lokalt och priset är ofta rimligt. Kontrollera vilka tredjepartsprodukter som stöds; en Zigbee-logga betyder inte automatiskt att allt går att lägga till i IKEA-appen."],
            ["Sonoff Dongle och andra koordinatorer", "En Sonoff Zigbee 3.0 USB Dongle Plus kan vara ett prisvärt alternativ till ZBT-1 för Home Assistant. Modellvariant och firmware spelar roll. Köp från en seriös återförsäljare, använd förlängningskabel och dokumentera vilken port den sitter i innan du bygger ett stort nät."],
            ["Stabilitet byggs med nätanslutna noder", "Zigbee-hubben är bara halva nätet. Lampor och pluggar med fast ström fungerar ofta som routrar. Batterisensorer gör det normalt inte. Sprid några stabila nätanslutna enheter mellan hubben och avlägsna rum innan du skyller på sensorerna."],
            ["En enkel beslutsregel", "Välj Hue för främst belysning, Dirigera för ett IKEA-tungt hem och Home Assistant med separat radio för blandade märken och lokala automationer. Undvik att starta tre parallella hubbar första veckan. Börja med den som täcker det viktigaste rummet."],
        ],
        "examples": [
            "En USB-förlängning flyttar Zigbee-radion bort från störande USB 3-portar.",
            "Två nätanslutna pluggar skapar en stabil väg till sensorn längst bort i bostaden.",
            "Familjen kan fortfarande tända lamporna med en fysisk knapp när servern uppdateras.",
        ],
    },
    "basta-robotdammsugare-barnfamiljer": {
        "description": "Roborock Q5 Pro och Dreame L10s Ultra bedömda för smulor, mattor, leksaker och husdjur. Utan låtsas-testvinnare.",
        "intro": "Barnfamiljens viktigaste specifikation är inte maximal sugkraft. Det är hur ofta roboten kan köra utan att någon först måste rädda den från strumpor och sladdar.",
        "sections": [
            ["Roborock Q5 Pro", "Q5 Pro är intressant för den som vill ha bra dammsugning och stor dammbehållare utan en dyr helautomatisk docka. Dubbel gummiborste kan vara praktisk med hår och smulor. Den enklare moppningen är inte huvudskälet att köpa den. Kontrollera tröskelhöjd, mattor och aktuell appfunktion för den modell som säljs."],
            ["Dreame L10s Ultra", "L10s Ultra kombinerar dammsugning med en docka som tömmer damm och hanterar moppar. Det sparar handarbete men tar plats, kräver rent och smutsigt vatten och behöver fortfarande rengöras. Den passar bättre där hårda golv moppas ofta än i ett hem med många höga trösklar och lösa leksaker."],
            ["Kartlägg kök och hall först", "Dela upp kartan i verkliga zoner: under matbordet, framför köksbänken och hallens grusyta. Kör korta zonstädningar efter middag i stället för hela bostaden varje gång. Det minskar både ljud och risken att roboten hittar ett stökigt barnrum."],
            ["Leksaker och sladdar avgör", "Objektigenkänning hjälper men är ingen garanti. Tunna laddkablar, små strumpor och leksaksdelar kan fortfarande fastna. Skapa en enkel golvfri rutin före körning och lägg no-go-zoner runt gardiner, matskålar eller känsliga mattor."],
            ["Tänk på förbrukningen", "Räkna med filter, sidoborstar, huvudborste, dammpåsar och eventuellt moppdelar. Kontrollera att reservdelar finns från normal återförsäljare. En billig robot blir dyr om kompatibla delar försvinner efter ett år."],
            ["Välj efter underhåll, inte reklambild", "Q5 Pro passar när dammsugning och enklare ägande väger tyngst. L10s Ultra passar när moppning och dockautomation motiverar mer plats, pris och rengöring. I båda fallen bör du mäta trösklar och dockans yta innan köp."],
        ],
        "examples": [
            "Efter middagen kör roboten bara zonen under bordet och framför diskbänken.",
            "Barnrum ligger utanför schemat tills golvet markerats som klart.",
            "Dockan står där vatten och dammpåse kan hanteras utan att blockera hallen.",
        ],
    },
    "billigt-smart-hem-under-100-euro": {
        "description": "Tre fungerande startpaket under 100 euro: belysning, säkerhet eller energimätning. Med tydliga kompromisser.",
        "intro": "Hundra euro räcker om allt i paketet löser samma problem. Det räcker sämre om pengarna sprids på fem prylar som kräver varsin app.",
        "sections": [
            ["Paket 1: kvällsljus", "Lägg pengarna på en smart lampa och en fysisk knapp. IKEA STYRBAR med kompatibel IKEA-belysning är ett enkelt spår. Philips Hue kostar mer men har ett moget belysningssystem. Kontrollera om hubb behövs; den kan spräcka budgeten om du inte redan äger en."],
            ["Paket 2: vatten och dörr", "Två eller tre Aqara-sensorer kan rymmas i budgeten om en kompatibel Zigbee-hubb redan finns. Prioritera vatten under diskmaskin och dörrsensor i hall eller förråd. Utan hubb är ett wifi-baserat alternativ enklare, men kontrollera batteritid och hur larmet levereras."],
            ["Paket 3: mät en energitjuv", "En TP-Link Tapo P110 eller Shelly Plug S kan mäta förbrukning och styra en enskild apparat. Kontrollera maximal last och använd inte en vanlig smart plug till utrustning den inte är klassad för. Målet är att förstå en verklig förbrukare, inte att samla grafer."],
            ["Köp inte allt samtidigt", "Beställ en funktion först och använd den i två veckor. Då märks det om placering, app eller räckvidd är fel innan resten av budgeten går åt. Returrätt är mer användbar än en rabatt på ett stort blandpaket."],
            ["Glöm inte det som kostar runtomkring", "Hubb, USB-förlängning, väggfäste, bra laddkabel och reservbatterier räknas också. Ett paket på 89 euro är inte under hundra om det kräver en hubb för 70 euro för att göra något vettigt."],
            ["Vårt enkla val", "Har du ingen hubb: börja med en smart plug med energimätning eller ett komplett belysningspaket. Har du redan Zigbee: lägg pengarna på vattenlarm och en fysisk knapp. Båda vägarna ger en funktion som går att utvärdera direkt."],
        ],
        "examples": [
            "Ett vattenlarm under diskmaskinen gör mer nytta än fyra slumpmässiga temperatursensorer.",
            "En enda fysisk knapp används oftare än tre nya appscener.",
            "Priset räknas inklusive hubb, fäste och batterier, inte bara produkten i kundvagnen.",
        ],
    },
    "basta-smarta-lampor-barnsovrum": {
        "description": "IKEA, Philips Hue och Tapo jämförda för läsning, nattljus och lugnare kvällar i barnrum.",
        "intro": "I ett barnrum är en bra smart lampa först och främst en bra lampa: flimmerfri, tillräckligt varm på kvällen och enkel att tända utan mobil.",
        "sections": [
            ["IKEA TRÅDFRI och STYRBAR", "IKEA är ett rimligt budgetspår när du vill kombinera dimbar belysning med en fysisk fjärrkontroll. Välj en ljuskälla med justerbar vittemperatur om samma lampa ska användas för lek, läsning och kväll. Kontrollera armaturens sockel och om Dirigera-hubb krävs för den automation du vill ha."],
            ["Philips Hue White Ambiance", "Hue kostar mer men har stabila knappar, bred ljusstyrning och ett moget ekosystem. White Ambiance räcker oftast; färgversionen behövs bara om färg faktiskt ingår i rutinen. En Hue Dimmer Switch gör att barnet kan styra ljuset utan app."],
            ["Tapo L530 och wifi-lampor", "Tapo L530 är ett billigt färgalternativ som inte kräver separat hubb. Varje lampa ligger däremot på wifi och appberoendet blir större. Det kan vara rimligt för en enda lampa, men mindre attraktivt när många rum ska byggas ut."],
            ["Kvällsljus ska vara enkelt", "Använd en varm, låg nivå före läggdags och en separat nivå för läsning. Undvik blinkande effekter och färgbyten som kräver förhandling varje kväll. Automationen får gärna föreslå kväll, men barnet eller en vuxen ska kunna ändra med vanlig knapp."],
            ["Strömbrytaren är en del av systemet", "Om väggbrytaren stänger strömmen tappar en smart lampa kontakten. Lös det med en tydlig vana, en kompatibel smart knapp eller en installation som elektriker bedömt. Tejpa inte över brytaren som permanent lösning i ett barnrum."],
            ["Vad vi skulle välja", "IKEA passar en stram budget och fysisk fjärrkontroll. Hue passar när stabilitet och enkel utbyggnad väger tyngre än priset. En ensam Tapo-lampa kan vara tillräcklig för att prova idén. Börja med vittemperatur och dimring före färg."],
        ],
        "examples": [
            "Knappen vid sängen växlar mellan läsljus och ett svagt varmt nattljus.",
            "Kvällsläget startar automatiskt men går alltid att ändra manuellt.",
            "Lampan tänds svagt på natten utan att takbelysningen väcker resten av rummet.",
        ],
    },
}


def main() -> None:
    articles = json.loads(PATH.read_text(encoding="utf-8"))
    by_slug = {article["slug"]: article for article in articles}
    missing = sorted(set(UPDATES) - set(by_slug))
    if missing:
        raise SystemExit(f"Missing slugs: {', '.join(missing)}")
    for slug, changes in UPDATES.items():
        by_slug[slug].update(changes)

    # Keep a repeated sentence only where it first appears. Repetition across
    # different articles is more conspicuous than an absent example box.
    seen: set[str] = set()
    for article in articles:
        unique = []
        for item in article.get("examples", []):
            normalized = " ".join(str(item).lower().split())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(item)
        article["examples"] = unique

    PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(UPDATES)} flagship articles; {len(articles)} total articles")


if __name__ == "__main__":
    main()
