# Network Dashboard Next

Modulär parallell ersättare för den nuvarande familjedashboarden.

## Viktiga regler

- Nuvarande live-app på port 8792 ändras inte under utvecklingen.
- Version 2 ligger fortsatt bakom lösenordsskyddad adminsession på `/preview-v2`.
- Den befintliga databasen används utan att schema eller data kopieras i hemlighet.
- Nya domänmoduler flyttas över en i taget. Övriga `/api/*` går till ett tidsbegränsat kompatibilitetslager mot den gamla appen.
- Ingen fil ska växa till en ny monolit. Router, service, repository och schema hålls separerade.

## Start

```bash
cd network-dashboard-next
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
COOKIE_SECURE=false python run.py
```

`run.py` provar i ordning 8793, 8794, 8795, 8800, 8801 och 8810. Om alla är upptagna väljs en ledig dynamisk port. Sätt `PORT=8794` för ett uttryckligt val; starten avbryts om den porten är upptagen.

## Miljövariabler

| Variabel | Standard | Syfte |
|---|---|---|
| `LEGACY_ORIGIN` | `http://127.0.0.1:8792` | Tillfälligt kompatibilitetslager |
| `DASHBOARD_DB_PATH` | `~/.hermes/state/family_budget.sqlite3` | Befintlig familjedatabas |
| `DASHBOARD_STATIC_ROOT` | `./static` | Live- och V2-filer |
| `PORT` | `0` | Automatisk portdetektering |
| `COOKIE_SECURE` | `true` | Secure-cookie i produktionslik miljö |

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
