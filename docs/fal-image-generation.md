# FAL image generation setup

Bildgenerering i Hermes kräver en FAL-nyckel eller annan bildprovider.

## Viktigt

Agenten kan inte skapa ett FAL-konto eller en API-nyckel åt användaren. Nyckeln måste skapas av kontots ägare på fal.ai och läggas in som hemlighet lokalt. Lägg aldrig FAL_KEY i GitHub-repot.

## Steg

1. Gå till https://fal.ai
2. Skapa/logga in på konto.
3. Skapa API key.
4. Lägg in nyckeln i Hermes env-fil:

```bash
nano /home/johnn/.hermes/.env
```

Lägg till:

```bash
FAL_KEY=<din-fal-nyckel>
```

5. Starta om Hermes-sessionen/gatewayn så miljövariabeln laddas.
6. Testa med en bildgenerering.

## Bildpolicy för Smart Familj Hemma

- Ingen text i bilderna.
- Inga produktloggor.
- Fotorealistisk nordisk familjehemsmiljö.
- Hall, kök, barnrum, tvättstuga, dashboard, sensorer.
- En bild per artikelkluster så sajten inte ser repetitiv ut.

## Exempelprompt

Photorealistic Scandinavian family apartment hallway in morning light, school bags and shoes neatly by the door, subtle smart home wall button and small dashboard tablet, warm natural light, editorial magazine photography, no text, no logos.
