# WSL-installation – Lindells app Next

Kör från repots projektkatalog:

```bash
cd network-dashboard-next
chmod +x scripts/*.sh
bash scripts/install.sh
```

`scripts/install.sh` kör först en preflight som kontrollerar:

- Python 3.12 eller senare,
- `python3-venv`,
- `rsync`, `openssl`, `systemctl` och `realpath`,
- fungerande `systemctl --user`,
- att live-databasen finns.

Om preflighten är grön fortsätter `install_parallel.sh` automatiskt med isolerad databaskopia, credentialadoption, tester, migreringar, separat systemd-tjänst och full readiness.

## Installationen får inte ändra

```text
http://127.0.0.1:8792
/home/johnn/network-dashboard
/home/johnn/.hermes/state/family_budget.sqlite3
homelab-control-center.service
```

## Filer som skapas för Next

```text
~/network-dashboard-next
~/.hermes/state/family_budget_next.sqlite3
~/.config/network-dashboard-next.env
~/.config/network-dashboard-next/integration-secrets.json
~/.config/network-dashboard-next/google_client_secret.json
~/.config/network-dashboard-next/google_token.json
~/.cache/network-dashboard-next/runtime.env
~/.cache/network-dashboard-next/legacy-config-import.json
~/.cache/network-dashboard-next/readiness-report.json
```

Hemlighets- och rapportfiler ska ha filrättighet `0600`.

## Vid lyckad installation

Terminalen visar en separat Next-origin. Öppna den origin som står i:

```bash
cat ~/.cache/network-dashboard-next/runtime.env
```

Kontrollera tjänsten:

```bash
systemctl --user status network-dashboard-next.service --no-pager
```

Kör readiness igen:

```bash
source ~/.cache/network-dashboard-next/runtime.env
~/network-dashboard-next/.venv/bin/python \
  ~/network-dashboard-next/scripts/readiness_report.py \
  --origin "$ORIGIN"
```

## Om installationen stoppas

Installationsskriptet stoppar bara Next-tjänsten. Liveappen ska fortsätta svara på port 8792.

Visa dessa filer/kommandon vid felsökning:

```bash
cat ~/.cache/network-dashboard-next/readiness-report.json
cat ~/.cache/network-dashboard-next/legacy-config-import.json
journalctl --user -u network-dashboard-next.service -n 150 --no-pager
systemctl --user status homelab-control-center.service --no-pager
curl -I http://127.0.0.1:8792/
```

Skicka inte innehållet i följande filer eftersom de innehåller hemligheter:

```text
~/.config/network-dashboard-next.env
~/.config/network-dashboard-next/integration-secrets.json
~/.config/network-dashboard-next/google_client_secret.json
~/.config/network-dashboard-next/google_token.json
```

## Rollback av endast Next

```bash
bash ~/network-dashboard-next/scripts/rollback_parallel.sh
```

Rollback ska inte stoppa eller ändra liveappen.
