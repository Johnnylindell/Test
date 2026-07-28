# Lindells app Next

Modulär ersättare för den nuvarande familjedashboarden. Next installeras först som en separat, skrivskyddad parallellversion och får inte påverka liveappen, live-databasen eller port 8792.

## Säkerhetsgränser

- Liveappen ligger kvar på `http://127.0.0.1:8792`.
- Live-databasen är normalt `~/.hermes/state/family_budget.sqlite3`.
- Next använder en separat SQLite-kopia, normalt `~/.hermes/state/family_budget_next.sqlite3`.
- Next väljer en annan ledig port och skriver den till en runtime-fil.
- `DASHBOARD_READ_ONLY=true`, `ALLOW_LEGACY_WRITES=false` och `EXTERNAL_SIDE_EFFECTS=false` används under parallelltestet.
- Bankimport, Excelimport, notifieringsutskick, Home Assistant-kommandon och driftkommandon kräver uttrycklig bekräftelse och rätt driftläge.
- Familjeprofiler har serververkställda sektioner och kan vara skrivskyddade.
- Råa telefon-, nätverks- och credentialvärden returneras aldrig av familje- eller admin-API:t.

## Rekommenderad WSL-installation

Kör från projektets rot:

```bash
cd network-dashboard-next
chmod +x scripts/install_parallel.sh scripts/rollback_parallel.sh
./scripts/install_parallel.sh
```

Installationsskriptet utför följande i ordning:

1. Kopierar koden till `~/network-dashboard-next`.
2. Skapar en separat Python 3.12-miljö och installerar beroenden.
3. Verifierar att live- och Next-databasen inte är samma fil.
4. Skapar en konsekvent SQLite-kopia av live-databasen.
5. Skapar eller bevarar admin-, närvaro- och assistenthemligheter.
6. Letar efter tillåtna integrationsvärden i den gamla appen.
7. Skriver Next-konfiguration med filrättighet `0600`.
8. Kör `compileall`, Ruff och hela pytest-sviten.
9. Tar en backup och kör alla databasmigreringar på Next-kopian.
10. Startar `network-dashboard-next.service` på en separat port.
11. Kör den fullständiga readiness-rapporten.
12. Stoppar endast Next-tjänsten om en kritisk kontroll misslyckas.

Liveappen och live-databasen ändras inte av ett misslyckat installationsförsök.

## Automatiskt återanvända inställningar

Installationen försöker adoptera endast uttryckligt tillåtna värden:

- `home_assistant_url`
- `home_assistant_token`
- `discord_webhook_url`
- `vapid_public_key`
- `vapid_private_key`
- `vapid_subject`

Källor kontrolleras i följande ordning:

1. Next-hemlighetsfilen.
2. Den gamla databasens JSON-inställningar eller `app_settings`.
3. Tillåtna miljövariabler från den gamla systemd-tjänsten.

Google OAuth-filer söks endast på kända gamla platser och måste ha ett validerat Google-format innan de kopieras.

Den gamla appens webbläsarbaserade `ADMIN_TOKEN` migreras inte. Det är en sessionshemlighet och ska inte återanvändas som servercredential.

## Administrativ konfiguration

Öppna `/preview-v2` som admin och gå till **Integrationer**. Där kan följande göras utan att ett hemligt värde visas igen:

- se om en variabel saknas,
- se om värdet kommer från gammal databas, miljö eller Next-hemlighetsfil,
- ersätta ett värde,
- rensa ett Next-värde och återgå till äldre fallback,
- adoptera upptäckta gamla värden,
- generera ett atomiskt VAPID-nyckelpar,
- ladda upp Google client secret,
- ladda upp en validerad Google OAuth-token,
- radera isolerade Google-filer.

Setup-skrivningar till Next-hemlighetsfiler är tillåtna under parallelläget. Vanliga domänskrivningar och externa sidoeffekter är fortfarande blockerade.

## Skyddade filer

Normala sökvägar:

```text
~/.config/network-dashboard-next.env
~/.config/network-dashboard-next/integration-secrets.json
~/.config/network-dashboard-next/google_client_secret.json
~/.config/network-dashboard-next/google_token.json
~/.config/network-dashboard-next-presence.json
```

Rapporter och runtime-information:

```text
~/.cache/network-dashboard-next/runtime.env
~/.cache/network-dashboard-next/legacy-config-import.json
~/.cache/network-dashboard-next/readiness-report.json
~/.cache/network-dashboard-next/last-install.env
```

Hemlighets- och rapportfilerna ska ha filrättighet `0600`.

## Readiness

Kör rapporten igen efter installationen:

```bash
source ~/.cache/network-dashboard-next/runtime.env
~/network-dashboard-next/.venv/bin/python \
  ~/network-dashboard-next/scripts/readiness_report.py \
  --origin "$ORIGIN"
```

Rapporten blockerar bland annat:

- Next som pekar på live-databasen,
- trasig SQLite-integritet,
- pending eller checksummeändrade migreringar,
- osäkra filrättigheter,
- saknade genererade systemhemligheter,
- hemlighetsvärden i legacy-importloggen,
- Next-tjänst eller readiness-endpoint som inte svarar,
- liveappen på port 8792 som inte längre svarar.

Saknade valfria integrationer, exempelvis Google eller Discord, rapporteras som varningar och kan konfigureras senare i admin.

## Närvarobrygga

Närvarobryggan startar ingen nätverksskanning. Den läser den befintliga LAN-watcherns statusfil och skickar endast observationer för telefoner som uttryckligen aktiverats i:

```text
~/.config/network-dashboard-next-presence.json
```

Exempel:

```json
{
  "devices": [
    {
      "owner": "Johnny",
      "source_identifier": "AA:BB:CC:DD:EE:FF",
      "enabled": true
    }
  ]
}
```

Källidentifieraren används bara lokalt av bryggan. API:t lagrar en HMAC-koppling och returnerar aldrig den råa identifieraren.

Granska först utan att skicka något:

```bash
~/network-dashboard-next/.venv/bin/python \
  ~/network-dashboard-next/scripts/presence_bridge.py \
  --dry-run
```

Aktivera därefter timern uttryckligen:

```bash
cd ~/network-dashboard-next
bash scripts/manage_presence_timer.sh enable
```

Status, avstängning och borttagning:

```bash
bash scripts/manage_presence_timer.sh status
bash scripts/manage_presence_timer.sh disable
bash scripts/manage_presence_timer.sh uninstall
```

Timern vägrar aktivering om ingen komplett telefonkoppling finns. Den läser Next-porten ur runtime-filen och skickar inte närvarotoken till en publik origin.

## Driftkommandon

```bash
systemctl --user status network-dashboard-next.service --no-pager
journalctl --user -u network-dashboard-next.service -n 100 --no-pager
```

API-jämförelse:

```bash
source ~/.cache/network-dashboard-next/runtime.env
~/network-dashboard-next/.venv/bin/python \
  ~/network-dashboard-next/scripts/compare_parallel.py \
  --next "$ORIGIN"
```

## Rollback av parallellinstallationen

```bash
~/network-dashboard-next/scripts/rollback_parallel.sh
```

Rollback stoppar och tar bort Next-tjänsten. Liveappen på port 8792 påverkas inte.

## Miljövariabler

| Variabel | Standard | Syfte |
|---|---|---|
| `LEGACY_ORIGIN` | `http://127.0.0.1:8792` | Tillfälligt kompatibilitetslager |
| `DASHBOARD_DB_PATH` | `~/.hermes/state/family_budget_next.sqlite3` | Isolerad Next-databas |
| `DASHBOARD_STATIC_ROOT` | `./static` | Familje- och adminfiler |
| `DASHBOARD_READ_ONLY` | `false` manuellt, `true` i parallellinstallationen | Blockerar vanliga mutationer |
| `ALLOW_LEGACY_WRITES` | `false` | Blockerar skrivning genom legacyproxyn |
| `EXTERNAL_SIDE_EFFECTS` | `false` | Blockerar utskick, styrning och driftkommandon |
| `INTEGRATION_SECRETS_PATH` | `~/.config/network-dashboard-next/integration-secrets.json` | Skyddade integrationsvärden |
| `GOOGLE_TOKEN_PATH` | `~/.config/network-dashboard-next/google_token.json` | Isolerad OAuth-token |
| `GOOGLE_CLIENT_SECRETS_PATH` | `~/.config/network-dashboard-next/google_client_secret.json` | Google client-konfiguration |
| `HOME_ASSISTANT_VERIFY_TLS` | `true` i koden | TLS-verifiering |
| `HOME_ASSISTANT_CA_BUNDLE` | saknas | Valfri egen CA-fil |
| `NOTIFICATION_SCHEDULER_ENABLED` | `false` | Schemalagd notifieringsutvärdering |
| `PORT` | `0` | Automatisk portdetektering |
| `COOKIE_SECURE` | `true` | Secure-cookie i produktionslik miljö |
| `PRESENCE_INGEST_TOKEN` | saknas | Autentiserar sanerade närvaroobservationer |
| `ASSISTANT_SIGNING_SECRET` | saknas | Signerar tidsbegränsade assistentbekräftelser |

## Huvudfunktioner

Familjeappen omfattar bland annat:

- Home Compass och personlig dashboard,
- påminnelser, rutiner och checklistor,
- familjelistor och anteckningar,
- matsedel, recept och säker receptimport,
- inköpslista, återköpsförslag och förråd,
- önskelistor och saker hemma,
- integritetsskyddad telefonnärvaro,
- Web Push och notifieringsregler,
- Home Assistant-projektion,
- lokal familjeassistent med signerad bekräftelse före skrivning,
- installationsbar PWA.

Administration omfattar bland annat:

- budget och versionerad Excelimport/export,
- granskad CSV/CAMT-bankimport,
- Google Calendar och Tasks,
- integrationer och maskerad credentialhantering,
- backuper och verifierad återställning,
- accessprofiler, sessioner och revisionslogg,
- begränsade datoragenter och systemd-whitelist,
- readiness och diagnostik.

## Arkitektur

```text
app/
  auth/          identitet, sessioner och åtkomstprofiler
  compat/        tidsbegränsad legacyproxy
  core/          konfiguration, cache, circuit breaker och portval
  database/      SQLite och checksummebaserade migreringar
  integrations/  externa adaptergränser och credential-resolver
  modules/       separata domänmoduler
  web/           statiska familje- och adminroutes

static/
  live/          familjeapp och PWA
  shared/        gemensamt designsystem och API-klient
  v2/            administration

scripts/
  install_parallel.sh
  rollback_parallel.sh
  import_legacy_config.py
  readiness_report.py
  migrate_db.py
  compare_parallel.py
  manage_presence_timer.sh
```

## Manuell utvecklingsstart

```bash
cd network-dashboard-next
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
DASHBOARD_DB_PATH="$HOME/.hermes/state/family_budget_next.sqlite3" \
DASHBOARD_READ_ONLY=true \
EXTERNAL_SIDE_EFFECTS=false \
COOKIE_SECURE=false \
python run.py
```

`run.py` provar 8793, 8794, 8795, 8800, 8801 och 8810 och väljer därefter en dynamisk ledig port. En uttryckligen angiven upptagen port gör att starten avbryts.
