# Bildsystem för Smart Familj Hemma

Mål: varje viktig sida ska kännas som nordisk vardag, inte generisk stockbild. Bilder ska stödja artikeln, inte bara fylla yta.

## Kluster

1. **Rutiner / morgon / läggdags** — hall, skolväskor, barnrum, varm morgon/kväll, fysisk knapp.
2. **Dashboard / kalender / köksskärm** — kök, väggtablet, veckoplanering som abstrakta block utan läsbar text.
3. **Sensorer / vatten / tvättstuga** — diskmaskin, underskåp, tvättmaskin, liten sensor nära golv.
4. **Home Assistant / Zigbee** — hubb, dongel, sensorer på träbord hemma, inte serverhall.
5. **Belysning / barnrum / gardiner** — mjukt ljus, nattväg, gardiner, inga varumärken/leksaksfigurer.
6. **Städning / robotdammsugare / husdjur** — kök, hall, smulor, skor, robot i realistisk miljö.
7. **Säkerhet / dörr / brand / förråd** — ytterdörr, lås, brandvarnare, brevlåda, garage/förråd.
8. **Budget / köpråd / startpaket** — enkel produktgrupp på köksbord, inga loggor.

## FAL-prompter

Använd landscape 16:9, fotorealistiskt, inga texter/loggor.

- `generated/rutiner/morgonhall-smart-knapp.jpg`  
  Photorealistic Scandinavian family apartment hallway in soft winter morning light, school bags, small shoes, jackets, a subtle smart wall button near the door, warm practical atmosphere, editorial interior photography, no readable text, no logos, no brand names.

- `generated/rutiner/adhd-morgon-kok-hall.jpg`  
  Photorealistic Nordic kitchen and hallway transition during a busy family morning, warm smart lights changing gently, a wall tablet showing only abstract colored blocks and icons, school bag ready by the door, calm organized mood, no readable text, no logos.

- `generated/belysning-barnrum/laggdags-barnrum-smart-lampa.jpg`  
  Photorealistic Scandinavian child bedroom at bedtime, dim warm smart lamp, small motion sensor on shelf, cozy bedding, curtains partly closed, calm evening atmosphere, no readable text, no logos, no cartoon characters.

- `generated/dashboard/familjedashboard-kok.jpg`  
  Photorealistic Scandinavian family kitchen with a wall mounted tablet dashboard, screen content blurred into simple colored blocks and icons with no readable text, groceries and family objects on counter, natural daylight, no logos.

- `generated/dashboard/veckokalender-vagg.jpg`  
  Photorealistic Nordic dining nook with a family wall screen showing an abstract weekly planner layout with colored blocks but no readable text, breakfast dishes, school bag nearby, soft daylight, no logos.

- `generated/sensorer-vatten/lackage-diskmaskin-sensor.jpg`  
  Photorealistic close-up under a Scandinavian kitchen dishwasher, small white water leak sensor on the floor, subtle reflection of water droplets, clean realistic home environment, safety focused, no readable text, no logos.

- `generated/sensorer-vatten/tvattstuga-sensor.jpg`  
  Photorealistic Nordic laundry room with washing machine, laundry baskets, small leak sensor near the floor, soft utility lighting, tidy but lived-in family home, no readable text, no logos.

- `generated/sensorer-vatten/badrum-nattljus-sensor.jpg`  
  Photorealistic Scandinavian bathroom at night, very soft motion activated floor light, small sensor near doorway, towels and child step stool, calm safe atmosphere, no readable text, no logos.

- `generated/home-assistant-zigbee/hub-sensorer-bord.jpg`  
  Photorealistic cozy Scandinavian home office corner with a small smart home hub, USB dongle, a few unbranded sensors and smart buttons on a wooden desk, laptop screen blurred, warm desk lamp, no readable text, no logos.

- `generated/home-assistant-zigbee/zigbee-setup-bord.jpg`  
  Photorealistic overhead view of a Nordic living room table with several small unbranded smart home devices: button, sensor, bulb, hub, arranged naturally like a setup session, family home background, no readable text, no logos.

- `generated/stadning/robotdammsugare-kok-hall.jpg`  
  Photorealistic Scandinavian family kitchen and hallway floor, robot vacuum cleaning crumbs after breakfast, shoes and school bags neatly to the side, realistic lived-in home, no readable text, no logos.

- `generated/stadning/robotdammsugare-hund.jpg`  
  Photorealistic Nordic living room with dog hair on a rug, a robot vacuum working near a calm family dog, warm daylight, practical home setting, no readable text, no logos.

- `generated/sakerhet/ytterdorr-smart-las-sensor.jpg`  
  Photorealistic Scandinavian apartment entrance door with a discreet unbranded smart lock and small door sensor, shoes and coat rack nearby, secure but welcoming mood, no readable text, no logos.

- `generated/sakerhet/brandvarnare-hall.jpg`  
  Photorealistic Scandinavian hallway ceiling with a clean smoke detector, warm family home below with coats and soft lighting, safety focused editorial photo, no readable text, no logos.

- `generated/budget-kopguide/startpaket-smart-hem.jpg`  
  Photorealistic Nordic kitchen table with an unbranded smart home starter kit: small button, smart bulb, motion sensor, smart plug, simple hub, family apartment background, natural light, no readable text, no logos.

## Prioriterad ersättning

Fasa ut först: `zigbee-desk.jpg`, `family-living.jpg`, `water-sink.jpg`, `budget-home.jpg`, `morning-hall.jpg`, `tablet-kitchen.jpg`, `kids-bedroom.jpg`, `smart-plug.jpg`, `commons-air-quality.jpg`, `commons-mailbox.jpg`.

Regel: samma bild bör inte användas mer än 2–3 gånger. Skapa variationer per vinkel, rum, tid på dagen och närbild/rumsvy.
