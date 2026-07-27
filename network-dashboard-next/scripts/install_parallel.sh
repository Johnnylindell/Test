#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/.venv"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/network-dashboard-next.service"
ENV_FILE="$HOME/.config/network-dashboard-next.env"
RUNTIME_FILE="$HOME/.cache/network-dashboard-next/runtime.env"
LIVE_DB_PATH="${LIVE_DASHBOARD_DB_PATH:-$HOME/.hermes/state/family_budget.sqlite3}"
NEXT_DB_PATH="${DASHBOARD_DB_PATH:-$HOME/.hermes/state/family_budget_next.sqlite3}"
BACKUP_DIR="$HOME/.local/share/network-dashboard-next/backups"

mkdir -p "$APP_DIR" "$SERVICE_DIR" "$(dirname "$RUNTIME_FILE")" "$BACKUP_DIR" "$(dirname "$NEXT_DB_PATH")"
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

cat > "$ENV_FILE" <<EOF
LEGACY_ORIGIN=http://127.0.0.1:8792
DASHBOARD_DB_PATH=$NEXT_DB_PATH
DASHBOARD_RUNTIME_FILE=$RUNTIME_FILE
DASHBOARD_READ_ONLY=true
ALLOW_LEGACY_WRITES=false
EXTERNAL_SIDE_EFFECTS=false
PORT=0
COOKIE_SECURE=false
EOF

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
Gamla appen på http://127.0.0.1:8792 har inte ändrats.

Status:
  systemctl --user status network-dashboard-next.service --no-pager
Logg:
  journalctl --user -u network-dashboard-next.service -n 100 --no-pager
Jämför API-kontrakt:
  $VENV/bin/python $APP_DIR/scripts/compare_parallel.py --next $ORIGIN
Rollback av parallellinstallationen:
  $APP_DIR/scripts/rollback_parallel.sh
EOF
