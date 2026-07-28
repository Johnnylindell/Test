# Lokal servertranskribering

Familjeassistenten använder i första hand webbläsarens `SpeechRecognition`. När det API:t saknas eller slutar fungera kan Next använda en lokal `faster-whisper`-modell som reserv.

## Säkerhetsgränser

- Funktionen är avstängd som standard.
- Ljud accepteras bara från en inloggad profil och ett same-origin-anrop.
- Tillåtna format är WebM, Ogg, WAV, MP3 och M4A.
- Standardgränsen är 8 MiB per inspelning.
- Webbläsaren stoppar automatiskt inspelningen efter 15 sekunder.
- Servern använder en temporär fil och raderar den i ett `finally`-block.
- Bara en transkribering körs åt gången.
- Ingen extern transkriberingstjänst används.
- Modellhämtning är avstängd om den inte aktiveras uttryckligen.

## Rekommenderad aktivering med lokal modell

Installera eller ladda ned en CTranslate2-kompatibel faster-whisper-modell till en lokal katalog. Aktivera därefter funktionen:

```bash
cd ~/network-dashboard-next
bash scripts/setup_speech_transcription.sh enable /absolut/sökväg/till/modellen
```

Kontrollera status:

```bash
bash scripts/setup_speech_transcription.sh status
```

Stäng av funktionen:

```bash
bash scripts/setup_speech_transcription.sh disable
```

## Aktivering med tillåten modellhämtning

Detta är ett uttryckligt opt-in-läge. Första transkriberingen kan då hämta modellen via faster-whisper:

```bash
bash scripts/setup_speech_transcription.sh enable small --allow-download
```

För en server utan GPU är `cpu` och `int8` standard. Modellen `small` ger bättre svenska resultat än de minsta modellerna men kräver mer minne och CPU-tid.

## Miljövariabler

| Variabel | Standard | Syfte |
|---|---:|---|
| `SPEECH_TRANSCRIPTION_ENABLED` | `false` | Aktiverar serverfallbacken |
| `SPEECH_TRANSCRIPTION_MODEL` | tom | Lokal modellkatalog eller modellnamn |
| `SPEECH_TRANSCRIPTION_DEVICE` | `cpu` | faster-whisper-enhet |
| `SPEECH_TRANSCRIPTION_COMPUTE_TYPE` | `int8` | Beräkningsformat |
| `SPEECH_TRANSCRIPTION_MAX_BYTES` | `8388608` | Maximal ljudstorlek |
| `SPEECH_TRANSCRIPTION_ALLOW_MODEL_DOWNLOAD` | `false` | Tillåter modellhämtning |

Status visas även under **Administration → Avancerat**. API-svaret visar aldrig ljuddata, lokala fullständiga modellsökvägar eller andra hemligheter.
