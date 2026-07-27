#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/.venv"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/network-dashboard-next.service"
ENV_FILE="$HOME/.config/network-dashboard-next.env"
CONFIG_DIR="$HOME/.config/network-dashboard-next"
PRESENCE_CONFIG="$HOME/.config/network-dashboard-next-presence.json"
RUNTIME_FILE="$HOME/.cache/network-dashboard-next/runtime.env"
LIVE_DB_PATH="${LIVE_DASHBOARD_DB_PATH:-$HOME/.hermes/state/family_budget.sqlite3}"
NEXT_DB_PATH="${DASHBOARD_DB_PATH:-$HOME/.hermes/state/family_budget_next.sqlite3}"
BACKUP_DIR="$HOME/.local/share/network-dashboard-next/backups"
GOOGLE_TOKEN_PATH="${GOOGLE_TOKEN_PATH:-$CONFIG_DIR/google_token.json}"
GOOGLE_CLIENT_SECRETS_PATH="${GOOGLE_CLIENT_SECRETS_PATH:-$CONFIG_DIR/google_client_secret.json}"

mkdir -p "$APP_DIR" "$SERVICE_DIR" "$CONFIG_DIR" "$(dirname "$RUNTIME_FILE")" "$BACKUP_DIR" "$(dirname "$NEXT_DB_PATH")"
rsync -a --delete --exclude '.git' --exclude '.venv' "$SOURCE_DIR/" "$APP_DIR/"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -e "$APP_DIR[dev]"

if [[ ! -f "$LIVE_DB_PATH" ]]; then
  echo "Live-databasen saknas: $LIVE_DB_PATH" >&2
  exit 1
fi
if [[ "$NEXT_DB_PATH" == "$LIVE_DB_PATH" ]]; then
  echo "NEXT_DB_PATH får inte vara samma som live-databasen." >&2
  exit 1
fi

"$VENV/bin/python" - <<PY
import sqlite3
from pathlib import Path
src = Path("$LIVE_DB_PATH").expanduser()
dst = Path("$NEXT_DB_PATH").expanduser()
dst.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(src) as source, sqlite3.connect(dst) as target:
    source.backup(target)
with sqlite3.connect(dst) as check:
    result = check.execute("PRAGMA integrity_check").fetchone()[0]
    assert result == "ok", result
print(f"Isolerad databaskopia skapad: {dst}")
PY

PRESENCE_HASH_SECRET=""
PRESENCE_INGEST_TOKEN=""
ASSISTANT_SIGNING_SECRET=""
HOMELAB_ADMIN_PASSWORD=""
ADMIN_PASSWORD_GENERATED=false
if [[ -f "$ENV_FILE" ]]; then
  PRESENCE_HASH_SECRET="$(grep -E '^PRESENCE_HASH_SECRET=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
  PRESENCE_INGEST_TOKEN="$(grep -E '^PRESENCE_INGEST_TOKEN=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
  ASSISTANT_SIGNING_SECRET="$(grep -E '^ASSISTANT_SIGNING_SECRET=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
  HOMELAB_ADMIN_PASSWORD="$(grep -E '^HOMELAB_ADMIN_PASSWORD=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)"
fi
[[ -n "$PRESENCE_HASH_SECRET" ]] || PRESENCE_HASH_SECRET="$(openssl rand -hex 32)"
[[ -n "$PRESENCE_INGEST_TOKEN" ]] || PRESENCE_INGEST_TOKEN="$(openssl rand -hex 32)"
[[ -n "$ASSISTANT_SIGNING_SECRET" ]] || ASSISTANT_SIGNING_SECRET="$(openssl rand -hex 32)"
if [[ -z "$HOMELAB_ADMIN_PASSWORD" ]]; then
  HOMELAB_ADMIN_PASSWORD="$(openssl rand -hex 12)"
  ADMIN_PASSWORD_GENERATED=true
fi

cat > "$ENV_FILE" <<EOF
LEGACY_ORIGIN=http://127.0.0.1:8792
DASHBOARD_DB_PATH=$NEXT_DB_PATH
DASHBOARD_RUNTIME_FILE=$RUNTIME_FILE
DASHBOARD_READ_ONLY=true
ALLOW_LEGACY_WRITES=false
EXTERNAL_SIDE_EFFECTS=false
HOMELAB_ADMIN_PASSWORD=$HOMELAB_ADMIN_PASSWORD
PRESENCE_HASH_SECRET=$PRESENCE_HASH_SECRET
PRESENCE_INGEST_TOKEN=$PRESENCE_INGEST_TOKEN
ASSISTANT_SIGNING_SECRET=$ASSISTANT_SIGNING_SECRET
NOTIFICATION_SCHEDULER_ENABLED=false
GOOGLE_TOKEN_PATH=$GOOGLE_TOKEN_PATH
GOOGLE_CLIENT_SECRETS_PATH=$GOOGLE_CLIENT_SECRETS_PATH
PORT=0
COOKIE_SECURE=false
EOF
chmod 600 "$ENV_FILE"

if [[ ! -f "$PRESENCE_CONFIG" ]]; then
  cat > "$PRESENCE_CONFIG" <<'EOF'
{
  "devices": [
    {
      "owner": "Johnny",
      "source_identifier": "ERSÄTT-MED-TELEFONENS-MAC",
      "enabled": false
    }
  ]
}
EOF
  chmod 600 "$PRESENCE_CONFIG"
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Lindells Network Dashboard Next
After=default.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/python $APP_DIR/run.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
EOF

"$VENV/bin/python" -m compileall -q "$APP_DIR/app" "$APP_DIR/migrations" "$APP_DIR/scripts"
"$VENV/bin/ruff" check "$APP_DIR/app" "$APP_DIR/migrations" "$APP_DIR/scripts" "$APP_DIR/tests"
"$VENV/bin/pytest" "$APP_DIR/tests"

MIGRATION_RESULT="$("$VENV/bin/python" "$APP_DIR/scripts/migrate_db.py" upgrade --database "$NEXT_DB_PATH" --backup-dir "$BACKUP_DIR")"
echo "$MIGRATION_RESULT"
LATEST_BACKUP="$(printf '%s' "$MIGRATION_RESULT" | "$VENV/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["backup"])')"
printf 'LATEST_BACKUP=%q\nDATABASE=%q\nLIVE_DATABASE=%q\n' "$LATEST_BACKUP" "$NEXT_DB_PATH" "$LIVE_DB_PATH" > "$HOME/.cache/network-dashboard-next/last-install.env"

rm -f "$RUNTIME_FILE"
systemctl --user daemon-reload
systemctl --user enable --now network-dashboard-next.service

for _ in {1..20}; do
  [[ -s "$RUNTIME_FILE" ]] && break
  sleep 0.5
done

if [[ ! -s "$RUNTIME_FILE" ]]; then
  systemctl --user status network-dashboard-next.service --no-pager || true
  echo "Tjänsten startade inte eller skrev ingen runtime-fil." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$RUNTIME_FILE"
"$VENV/bin/python" - <<PY
import httpx
response = httpx.get("$ORIGIN/api/v2/health/ready", timeout=10)
response.raise_for_status()
payload = response.json()
assert payload.get("ok") is True, payload
print("Ready:", payload)
PY

cat <<EOF

Parallellversionen är installerad och kör på: $ORIGIN
Runtime-fil: $RUNTIME_FILE
Live-databas (orörd): $LIVE_DB_PATH
Next-databaskopia: $NEXT_DB_PATH
Next körs skrivskyddad och utan externa sidoeffekter.
Närvarohemligheter, assistentsignering och bootstrap-lösenord finns i $ENV_FILE med filrättighet 600.
Inaktiv närvaroexempelkonfiguration: $PRESENCE_CONFIG
Google-token för Next: $GOOGLE_TOKEN_PATH
Google client secret ska placeras i: $GOOGLE_CLIENT_SECRETS_PATH
Gamla appen på http://127.0.0.1:8792 har inte ändrats.
EOF

if [[ "$ADMIN_PASSWORD_GENERATED" == true ]]; then
  cat <<EOF

Ett nytt Next-adminlösenord skapades:
  $HOMELAB_ADMIN_PASSWORD
Spara det i en lösenordshanterare. Det kan senare bytas i adminpanelen.
EOF
else
  cat <<EOF

Befintligt Next-adminlösenord i miljöfilen har bevarats.
EOF
fi

cat <<EOF

Status:
  systemctl --user status network-dashboard-next.service --no-pager
Logg:
  journalctl --user -u network-dashboard-next.service -n 100 --no-pager
Jämför API-kontrakt:
  $VENV/bin/python $APP_DIR/scripts/compare_parallel.py --next $ORIGIN
Torrkör närvarobryggan:
  $VENV/bin/python $APP_DIR/scripts/presence_bridge.py --dry-run
Rollback av parallellinstallationen:
  $APP_DIR/scripts/rollback_parallel.sh
EOF
