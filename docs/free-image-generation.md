# Gratis bildgenerering

FAL ger ofta bättre och mer stabila bilder, men sajten kan använda gratisalternativ tills en betald nyckel finns.

## Pollinations.ai

Ingen API-nyckel krävs. Scriptet finns här:

```bash
python3 scripts/generate_pollinations_images.py morgonhall-smart-knapp
python3 scripts/generate_pollinations_images.py --all
```

Bilder sparas i:

```text
assets/photos/generated/
```

Nackdelar:

- kvaliteten varierar
- ibland behövs flera seed-försök
- kontrollen är sämre än FAL
- externa gratis-tjänster kan ändra villkor eller rate limits

För sajten duger det för redaktionella miljöbilder: hall, kök, barnrum, tvättstuga, sensorer. Undvik ansikten, text och loggor.

## Licenssäkra alternativ utan AI

- Wikimedia Commons, men kurera hårt. Många bilder känns fel för nordisk familjevardag.
- Egna mobilbilder hemma, beskärda och utan barnansikten. Bäst trovärdighet.
- Unsplash/Pexels kan fungera, men kolla licens och undvik samma stockbilder som alla andra använder.

## Rekommendation

1. Pollinations för första egna bildsystemet.
2. Byt senare till FAL eller egna foton för viktigaste money pages.
3. Samma bild ska helst inte användas på fler än 2-3 artiklar.
