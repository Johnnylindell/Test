# Network Dashboard Next

Modulär parallell ersättare för den nuvarande familjedashboarden.

## Viktiga regler

- Nuvarande live-app på port 8792 ändras inte under utvecklingen.
- Version 2 ligger fortsatt bakom lösenordsskyddad adminsession på `/preview-v2`.
- Den parallella installationen skapar en uttrycklig SQLite-kopia i `family_budget_next.sqlite3`; live-databasen migreras eller skrivs inte.
- Next startar skrivskyddad och med externa sidoeffekter avstängda tills verifierad aktivering görs separat.
- Nya domänmoduler flyttas över en i taget. Övriga `/api/*` går till ett tidsbegränsat kompatibilitetslager mot den gamla appen.
- Ingen fil ska växa till en ny monolit. Router, service, repository och schema hålls separerade.

## Säker parallellinstallation

Från repots rot:

```bash
cd network-dashboard-next
bash scripts/install_parallel.sh
```

Installationen:

1. lämnar liveappen på port 8792 orörd,
2. tar en konsekvent SQLite-kopia till Next-databasen,
3. kör kompilering, Ruff, tester och migreringar,
4. startar `network-dashboard-next.service` på en ledig port,
5. kör en readinessrapport och stoppar Next igen om en kritisk kontroll misslyckas.

## Manuell utvecklingsstart

```bash
cd network-dashboard-next
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
COOKIE_SECURE=false DASHBOARD_READ_ONLY=true python run.py
```

`run.py` provar i ordning 8793, 8794, 8795, 8800, 8801 och 8810. Om alla är upptagna väljs en ledig dynamisk port. Sätt `PORT=8794` för ett uttryckligt val; starten avbryts om den porten är upptagen.

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

Konfigurationsfilen innehåller den lokala källidentifieraren och ska ha filrättighet `0600`. API:t lagrar endast HMAC-kopplingen, inte rå identifierare.

Granska först utan att skicka något:

```bash
~/.local/share/network-dashboard-next/.venv/bin/python \
  ~/network-dashboard-next/scripts/presence_bridge.py --dry-run
```

Vid standardinstallationen ligger Python normalt i `~/network-dashboard-next/.venv/bin/python`; använd den faktiska sökvägen om installationen ligger någon annanstans.

Aktivera därefter systemd-timern uttryckligen:

```bash
cd ~/network-dashboard-next
bash scripts/manage_presence_timer.sh enable
```

Status, avstängning och full borttagning av timerfiler:

```bash
bash scripts/manage_presence_timer.sh status
bash scripts/manage_presence_timer.sh disable
bash scripts/manage_presence_timer.sh uninstall
```

Timern läser Next-porten ur `~/.cache/network-dashboard-next/runtime.env` och vägrar skicka närvarotoken till en publik origin.

## Miljövariabler

| Variabel | Standard | Syfte |
|---|---|---|
| `LEGACY_ORIGIN` | `http://127.0.0.1:8792` | Tillfälligt kompatibilitetslager |
| `DASHBOARD_DB_PATH` | `~/.hermes/state/family_budget_next.sqlite3` | Isolerad Next-databas |
| `DASHBOARD_STATIC_ROOT` | `./static` | Live- och V2-filer |
| `DASHBOARD_READ_ONLY` | `false` manuellt, `true` i parallellinstallationen | Blockerar mutationer |
| `EXTERNAL_SIDE_EFFECTS` | `false` | Blockerar externa skrivningar och styrning |
| `PORT` | `0` | Automatisk portdetektering |
| `COOKIE_SECURE` | `true` | Secure-cookie i produktionslik miljö |
| `PRESENCE_INGEST_TOKEN` | saknas | Autentiserar sanerade närvaroobservationer |

## Arkitektur

```text
app/
  auth/          sessioner, identitet och adminspärr
  compat/        tillfällig proxy mot gamla API:t
  core/          konfiguration, portval och gemensam infrastruktur
  database/      SQLite-anslutning och transaktioner
  modules/       fristående domänmoduler
  web/           live- och V2-routing
```

Varje framtida domänmodul får normalt:

```text
modules/planning/
  router.py
  service.py
  repository.py
  schemas.py
  errors.py
```

## Migreringsordning

1. Auth, statiska routes och hälsokontroller.
2. Home-sammanfattning och read-only projections.
3. Planning, family och shopping.
4. Inventory, food och budget.
5. Notifications och integrationer.
6. Admin/homelab sist.
7. Ta bort kompatibilitetsproxyn när alla kontrakt är egna.

## Säker driftsättning

Den nya tjänsten körs parallellt på vald ledig port. Port 8792 byts först efter kontraktstester, webbläsartester, databasbackup och verifierad rollback.
