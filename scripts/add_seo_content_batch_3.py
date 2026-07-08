#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "content" / "articles" / "articles.json"
articles = json.loads(path.read_text(encoding="utf-8"))
existing = {a["slug"] for a in articles}

COMMON_END = [
    ["Vanliga misstag", "Det vanligaste felet är att börja för stort: för många notiser, för många lampor och för lite manuell kontroll. Börja med en tydlig signal på rätt plats och bygg bara vidare om familjen faktiskt använder den."],
    ["Börja enkelt", "Välj en zon, en tidpunkt och en sak som ska bli lättare. Om lösningen fungerar i två veckor kan du lägga till nästa steg. Om den inte används: flytta den, förenkla den eller ta bort den."],
]

def article(slug, title, desc, category, products, tags, intro, examples, sections):
    return {
        "slug": slug,
        "title": title,
        "description": desc,
        "category": category,
        "products": products,
        "tags": tags,
        "intro": intro,
        "examples": examples,
        "sections": sections + COMMON_END,
    }

NEW = [
article(
"tvattmaskinen-klar-smart-paminnelse",
"Tvättmaskinen blev klar – men ingen tömde den",
"Så använder du smart plug, notiser och vardagslogik för att slippa blöt tvätt som glöms kvar.",
"guide", ["smart-plug", "door-window-sensor", "temperature-sensor"], ["guide", "tvätt", "energi", "notiser", "home-assistant"],
"Det svåra med tvättmaskinspåminnelser är inte att veta när maskinen är klar. Det svåra är att påminna vid rätt tidpunkt. En notis mitt i nattningen försvinner lätt, och ett pip från tvättstugan hörs inte när alla står i köket.",
["Maskinen blir klar 18:12 men påminnelsen väntar tills kökslampan är tänd efter middagen.", "Om luckan inte öppnats efter 30 minuter kommer en ny diskret signal.", "På helgen går påminnelsen till den vuxen som faktiskt är hemma."],
[["Hur smart pluggen märker att maskinen är klar", "En smart plug med energimätning kan se när tvättmaskinen går från hög förbrukning till nästan ingenting. I Home Assistant kan det bli en enkel status: tvättar, klar eller avstängd."], ["Påminn rätt person", "Skicka inte allt till hela familjen. En bättre lösning är att visa status på köksskärmen och bara skicka notis om tvätten riskerar att bli liggande."], ["Luckan är viktig", "En dörrsensor på eller nära luckan kan användas för att se om någon faktiskt tömt maskinen. Det minskar falska påminnelser."], ["Utan Home Assistant", "Även utan automation kan en smart plug med app och energihistorik hjälpa dig se mönster och sätta bättre timer."]]
),
article(
"smart-hem-delad-vardnad-packlista",
"Smart hem för delad vårdnad: kalender, packlista och lugnare byten",
"Dashboard, checklistor och knappar för bytesdagar utan att allt måste kommas ihåg muntligt.",
"guide", ["tablet-wall", "smart-button", "door-window-sensor"], ["guide", "dashboard", "kalender", "rutiner", "barn"],
"Bytesdagar är ofta logistik mer än teknik: gympapåse, laddare, medicin, läxbok och favorittröja ska hamna i rätt hem utan att barnet blir projektledare.",
["Fredag 16:10 visar hallskärmen tre saker: iPad, laddare och gympapåse.", "En knapp markerar att packlistan är klar innan ytterdörren öppnas.", "Kalendern visar bara det barnet behöver veta: var sover jag ikväll och vem hämtar?"],
[["Visa mindre än du tror", "En bytesdagsskärm ska inte visa hela vuxenkalendern. Den ska visa plats, hämtning och packning."], ["Fysisk kvittens", "En knapp för 'packat' kan vara bättre än att någon ska bocka i en app."], ["Integritet", "Visa inte konflikter, detaljer eller vuxenlogistik på en skärm som barnen använder."], ["När teknik inte behövs", "Om en papperslista vid dörren fungerar bättre ska den vinna. Tekniken ska bara ta bort friktion."]]
),
article(
"barn-glommer-saker-smart-checklista",
"Smarta rutiner för barn som glömmer saker",
"Väska, läxa, gympa och nycklar: gör checklistan synlig där sakerna faktiskt finns.",
"guide", ["tablet-wall", "smart-button", "door-window-sensor"], ["guide", "rutiner", "morgon", "dashboard", "checklista"],
"Det är lätt att säga 'kom ihåg gympapåsen'. Det är svårare klockan 07:38 när någon letar vantar och frukten står kvar i köket.",
["Mellan 07:00 och 08:00 visar dashboarden bara väska, frukt och gympa.", "När ytterdörren öppnas efter 07:45 visas en sista check i hallen.", "En knapp vid kroken betyder att väskan är packad."],
[["Hallzonen", "Saker som ska med ut ska synas i hallen, inte i en app på förälderns telefon."], ["Kökzonen", "Frukt, vattenflaska och medicin hör ofta hemma i köket. En separat köksrad kan vara bättre än en jättelista."], ["Tidsstyr checklistan", "Visa bara morgonlistan när den behövs. Annars blir den bakgrundsbrus."], ["Låt barnet förstå signalen", "Text, ikon och färg ska vara begripliga utan vuxenförklaring."]]
),
article(
"smart-hall-vinterfamilj",
"Smart hall för vinterfamiljer: mörker, blöta kläder och sista-minuten-saker",
"Så gör du hallen lättare på vintermorgnar med ljus, små checklistor och få automationer.",
"guide", ["motion-sensor", "smart-bulb", "smart-button", "temperature-sensor"], ["guide", "hall", "morgon", "vinter", "belysning"],
"Hallen 07:45 i november är ett stresstest: mörkt ute, blöta vantar från igår och någon hittar inte reflexen. Här ska smart hem inte imponera. Det ska bara göra sista fem minuterna tydligare.",
["Efter 16:00 visar hallskärmen 'häng upp blöta kläder'.", "Morgonljuset är starkare vardagar men mjukare på helgen.", "En knapp vid dörren stänger av hallpåminnelser när alla gått."],
[["Ljuset först", "Bra halljus löser mer än många sensorer. Det ska tända snabbt men inte blända."], ["Tre saker räcker", "Visa inte hela dagen i hallen. Visa det som måste med ut."], ["Torkpåminnelser", "Fukt och temperatur kan hjälpa om hallen ofta fylls av blöta kläder."], ["Undvik larmkänsla", "Hallen behöver tydliga signaler, inte stressljud."]]
),
article(
"god-natt-knapp-familj-home-assistant",
"Så gör du en god natt-knapp som hela familjen faktiskt använder",
"En kvällsknapp som släcker rätt lampor, kollar dörren och lämnar nattljuset på.",
"guide", ["smart-button", "smart-bulb", "door-window-sensor"], ["guide", "knappar", "laggdags", "home-assistant", "belysning"],
"Kvällen blir ofta fem små rundor: lampor, ytterdörr, tv, vattenflaska och kök. En bra god natt-knapp tar bort rundorna utan att göra hemmet mörkt och svårt att använda.",
["Knappen i hallen släcker nedre våningen men lämnar trappans nattljus på.", "Om ytterdörren är öppen visar köksskärmen en tydlig rad i stället för ett högt larm.", "Ett andra tryck inom tio sekunder ångrar scenen."],
[["Vad knappen ska göra", "Börja med tre saker: släck valda lampor, sätt kvällsläge och visa om ytterdörren är öppen."], ["Vad den inte ska göra", "Lås inte in familjen i en scen som inte går att ångra. Någon kommer alltid på att något glömts."], ["Barnvänligt nattljus", "Total mörkläggning är sällan bäst. Lämna hall eller badrum svagt tända."], ["Felsäkert", "Alla lampor och knappar måste fortfarande gå att styra manuellt."]]
),
article(
"smart-kyl-frys-utan-dyrt-kylskap",
"Smart kyl och frys utan dyrt kylskåp",
"Dörrsensorer och temperaturlarm kan ge vardagsnytta utan att köpa nytt kylskåp.",
"guide", ["door-window-sensor", "temperature-sensor", "zigbee-hub"], ["guide", "dorrar", "klimat", "frys", "sensorer"],
"Du behöver inte ett uppkopplat kylskåp för att få bättre koll. Ofta räcker en dörrsensor, en temperatursensor och rimliga gränser för när familjen ska störas.",
["Efter lördagsgodisjakten står frysen i garaget på glänt.", "Kylskåpsdörren har varit öppen mer än tre minuter och köksskärmen visar en rad.", "Sommarstugans frys varnar om temperaturen stiger för länge."],
[["Dörr öppen", "Dörrlarm är användbart om det inte triggar för snabbt. Ge familjen några minuter innan signalen kommer."], ["Temperatur i frys", "Mätning i kyla kräver rätt sensor och koll på batteri. Testa innan du litar på larmet."], ["Varning när ingen är hemma", "Det är då larmet är mest värt. Hemma märker man ofta problemet själv."], ["Undvik falsklarm", "Larma först när problemet varat en stund, inte vid varje öppning."]]
),
article(
"barnrum-utan-appkaos-tre-lagen",
"Barnrum utan appkaos: tre lägen som räcker",
"Lek, läsning och sova räcker ofta längre än 18 scener och färgregnbågar.",
"guide", ["smart-bulb", "smart-button", "motion-sensor"], ["guide", "barnrum", "belysning", "knappar", "laggdags"],
"Barnrummet behöver sällan fler val. Det behöver färre val som barnet förstår utan att en vuxen letar i mobilen.",
["Ett tryck vid sängen ger läsljus, nästa tryck ger nattläge.", "Lekläget är ljust nog för lego men inte kallt som ett kontor.", "Nattläget tänder bara svagt om någon går upp."],
[["Lek", "Lekläget ska vara enkelt och robust. Ingen behöver färgeffekter för att hitta strumpor."], ["Läsning", "Varmt, tydligt ljus på rätt plats gör mer nytta än en avancerad scen."], ["Sova", "Sovläget ska vara förutsägbart. Undvik rörelsesensorer som tänder för starkt."], ["Barnets knapp", "En fysisk knapp gör rummet begripligt och minskar behovet av appstyrning."]]
),
article(
"barn-ensamma-hemma-smart-hem-utan-kamera",
"När barnen är ensamma hemma en stund: smart hem utan övervakningskänsla",
"Trygghet med dörrsensor, låsstatus och hjälpknapp – utan kamera i hemmet.",
"guide", ["door-window-sensor", "smart-lock", "smart-button", "tablet-wall"], ["guide", "integritet", "säkerhet", "dorrar", "barn"],
"När barn börjar vara hemma själva en stund är det lockande att lösa allt med kamera. Men ofta räcker mindre: dörrstatus, en hjälpknapp och tydlig information.",
["Barnet kommer hem 14:20 och vuxen får bara 'hemma'.", "Hjälpknappen i hallen skickar en lugn signal till vuxen.", "Dashboarden visar vad barnet behöver göra: mellis, läxa, aktivitet."],
[["Vad vuxna behöver veta", "Hemma, dörr stängd och inga akuta larm räcker ofta."], ["Vad barnen behöver", "Barnet behöver enkel hjälpväg, inte känslan av att vara övervakat."], ["Dörr och lås", "Dörrsensor och låsstatus kan ge trygghet utan bild eller ljud."], ["Ålder och ansvar", "Teknik ska anpassas efter barnet. Den ersätter inte överenskommelser."]]
),
article(
"robotdammsugare-stadzoner-kok-hall-matbord",
"Städzoner med robotdammsugare: kök, hall och under matbordet",
"Robotdammsugaren gör mest nytta där smulor, grus och vardagskaos faktiskt hamnar.",
"guide", ["robot-vacuum", "smart-button"], ["guide", "städning", "robotdammsugare", "kok", "hall"],
"En robotdammsugare som ska köra hela hemmet varje dag fastnar ofta i leksaker, sladdar och stolar. Zoner är mer realistiskt: kök efter middag, hall efter skola, under matbordet när golvet är fritt.",
["Efter kvällsmaten kör roboten bara under matbordet.", "Hallen körs när ytterdörren varit stängd i 20 minuter efter hemkomst.", "Barnet trycker 'golv fritt' när legot är undanplockat."],
[["Hela hemmet är sällan första steget", "Börja där smutsen återkommer. Ett litet område som körs ofta ger mer nytta än en stor körning som ofta avbryts."], ["Karta och zoner", "Om du köper robot för barnfamilj är zonstädning mer värdefullt än många extrafunktioner."], ["Knapp som start", "En knapp kan vara bättre än schema när hemmet är olika stökigt varje dag."], ["Realistiska krav", "Robotar städar inte undan leksaker. Bygg rutinen runt det."]]
),
article(
"familjens-krislage-dashboard-vatten-brand-strom",
"Familjens krisläge: vattenläcka, brandvarning och strömavbrott på samma översikt",
"När något händer ska hemmet visa färre saker, inte fler.",
"guide", ["water-leak-sensor", "smart-smoke-detector", "temperature-sensor", "zigbee-hub"], ["guide", "säkerhet", "vattenlackage", "brand", "dashboard"],
"När något händer hemma behöver familjen inte en avancerad dashboard. Den behöver en tydlig översikt: vad är problemet, var är det och vad gör vi nu?",
["Vattenlarmet under diskmaskinen visar 'stäng av vattnet under vasken'.", "Brandvarning tänder hallen svagt och visar väg ut, men ersätter inte vanligt larm.", "Vid internetavbrott visar dashboarden vilka lokala funktioner som fortfarande fungerar."],
[["Krisskärmen", "Visa bara aktiva larm, plats och första åtgärd. Resten kan döljas."], ["Vattenläcka", "Vattenlarm är ofta mest konkret: hitta larmet, stäng vatten, torka upp."], ["Brand", "Smart funktion är extra lager. Brandvarnare måste fungera lokalt även om nätet är nere."], ["Ström och internet", "Välj lösningar som inte blir värdelösa så fort internet försvinner."]]
),
article(
"produktguide-forsta-zigbee-sensorerna-rum-for-rum",
"Produktguide: första Zigbee-sensorerna för barnfamiljer – rum för rum",
"Vilka sensorer är värda att köpa först för hall, barnrum, kök och badrum?",
"köpguide", ["motion-sensor", "door-window-sensor", "temperature-sensor", "water-leak-sensor", "zigbee-hub"], ["kopguide", "zigbee", "sensorer", "barnrum", "kok"],
"Sensorer blir mest värda när de hamnar på rätt plats. Det bästa första köpet är inte den mest avancerade sensorn, utan den som löser något ni märker varje vecka.",
["Hallen får rörelsesensor först eftersom ljuset används varje dag.", "Köket får vattenlarm under diskmaskinen innan ni köper fler lampor.", "Barnrummet får temperatur eller knapp, inte kamera."],
[["Hall", "Rörelse och dörrstatus är mest användbart i hallen. Ljuset ska tända snabbt och dörren kan trigga checklistor."], ["Barnrum", "Temperatur, nattljus och en enkel knapp gör mer nytta än många sensorer."], ["Kök", "Vattenläcka, kyl/frys och vardagliga checklistor är starka användningsfall."], ["Köpordning", "Börja med hubb, en rörelsesensor, en dörrsensor och ett vattenlarm. Bygg vidare först när du ser nyttan."]]
),
article(
"spara-el-home-assistant-familj",
"Spara el med Home Assistant: 7 enkla automationer för familjer",
"El, värme och standby utan att hemmet känns som ett teknikprojekt.",
"guide", ["smart-plug", "smart-thermostat", "temperature-sensor"], ["guide", "energi", "home-assistant", "varme", "budget"],
"Energisparande hemma fungerar bara om familjen orkar leva med det. De bästa automationerna är små: stäng standby, styr värme försiktigt och visa när något drar el i onödan.",
["TV-hörnan stängs av efter midnatt om ingen är vaken.", "Element i barnrum sänks lite när rummet vädras.", "Tvättmaskinen föreslås köras senare, men bara om det inte stör vardagen."],
[["Standby först", "Smarta pluggar med energimätning visar vilka hörn som faktiskt drar el."], ["Värme försiktigt", "Sänk inte så mycket att familjen börjar överstyra allt manuellt."], ["Elpris utan stress", "Visa rekommendationer i stället för att låsa viktiga rutiner till timpris."], ["Mät före köp", "Mät en vecka innan du köper fler prylar."]]
),
article(
"smart-plug-energimatning-vad-kan-man-mata",
"Smart plug med energimätning: vad kan man faktiskt mäta hemma?",
"Köpguide för smarta pluggar: tvätt, standby, värme och när mätning inte behövs.",
"köpguide", ["smart-plug"], ["kopguide", "energi", "pluggar", "budget"],
"En smart plug med energimätning låter praktisk, men den ska inte sitta överallt. Den är bäst där mätningen leder till ett beslut: tvätt klar, standby slöseri eller apparat som drar mer än väntat.",
["Tvättmaskinens effektfall används som klar-signal.", "TV-bänken visar om flera apparater står på i onödan.", "En gammal frys mäts en vecka innan familjen bestämmer om den ska bytas."],
[["Tvättmaskin och diskmaskin", "Här är energimätning användbar, men kontrollera alltid maxlast och säker användning."], ["Standby", "Mät först. Många små apparater kostar mindre än man tror."], ["Värmeapparater", "Var extra försiktig med hög last. Alla pluggar är inte lämpliga för element."], ["När vanlig plug räcker", "Om du bara ska tända en lampa behövs oftast inte energimätning."]]
),
article(
"home-assistant-startpaket-vad-behover-man-kopa",
"Vad behöver man köpa för att börja med Home Assistant?",
"En rimlig första inköpslista för familjer: hubb, Zigbee, knapp, sensor och väggskärm.",
"köpguide", ["zigbee-hub", "smart-button", "motion-sensor", "water-leak-sensor", "tablet-wall"], ["kopguide", "home-assistant", "zigbee", "nyborjare"],
"Det är lätt att börja Home Assistant med för många prylar. En bättre start är ett litet paket som löser tre riktiga problem hemma: ljus, påminnelse och trygghet.",
["Första veckan: en knapp i hallen och en rörelsesensor för nattljus.", "Andra veckan: vattenlarm under diskmaskinen.", "Tredje veckan: en enkel dashboard i köket."],
[["Basen", "Välj en Home Assistant-enhet eller server som du orkar underhålla."], ["Zigbee", "En Zigbee-hubb eller dongel öppnar för billiga sensorer och knappar."], ["Första sensorerna", "Rörelse, dörr och vattenlarm ger snabb vardagsnytta."], ["Vänta med lyx", "Köp inte smarta gardiner, lås eller avancerade dashboards först."]]
),
article(
"smart-hem-hyresratt-startpaket-under-100-euro",
"Smart hem i hyresrätt: startpaket under 100 euro",
"Flyttbara prylar utan borrning: lampor, knapp, sensor och vattenlarm.",
"köpguide", ["smart-bulb", "smart-button", "motion-sensor", "water-leak-sensor"], ["kopguide", "hyresratt", "budget", "zigbee"],
"I hyresrätt ska smart hem gå att ta bort utan märken och utan att ringa elektriker. Det gör små, flyttbara prylar mer värdefulla än fasta installationer.",
["En lampa i hallen tänds automatiskt utan att byta strömbrytare.", "En knapp vid sängen styr nattläge utan kabeldragning.", "Vattenlarm under diskmaskinen följer med vid flytt."],
[["Börja utan borr", "Lampor, pluggar, knappar och sensorer med tejp räcker långt."], ["Prioritera problem", "Välj en mörk hall, en jobbig kvällsrutin eller risk för vattenläcka."], ["Budget", "Under 100 euro räcker ofta till två lampor, en knapp och en sensor om du väljer enkelt."], ["Flyttbarhet", "Spara originaldelar och undvik lösningar som kräver fast installation."]]
),
article(
"vackningsljus-barn-smart-lampa-eller-vackarklocka",
"Väckningsljus för barn: smart lampa eller väckarklocka?",
"När färgat ljus hjälper morgonen och när en vanlig barnväckarklocka är bättre.",
"köpguide", ["smart-bulb", "smart-blinds"], ["kopguide", "barnrum", "morgon", "belysning"],
"För tidiga morgnar handlar inte bara om att väcka barn. Ibland handlar det om att visa när det fortfarande är natt och när det är okej att gå upp.",
["Rött betyder vila kvar, grönt betyder morgon.", "Helgens schema är senare än vardagens utan att någon ändrar appen på kvällen.", "Lampan tänds långsamt i mörka vintermorgnar."],
[["Smart lampa", "Bra om du redan har system och vill styra färger och tider flexibelt."], ["Väckarklocka", "Bättre om du vill ha något barnet förstår utan Home Assistant eller app."], ["Gardiner", "Smarta gardiner kan hjälpa med ljus, men är dyrare och mer mekaniska."], ["Undvik för starkt ljus", "Målet är signal, inte att blända ett sömnigt barn."]]
),
]

added = 0
for item in NEW:
    if item["slug"] not in existing:
        articles.append(item)
        existing.add(item["slug"])
        added += 1

path.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"added_articles={added}")
print(f"total_articles={len(articles)}")
