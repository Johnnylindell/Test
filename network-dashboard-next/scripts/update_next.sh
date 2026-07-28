#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
ENV_FILE="${ENV_FILE:-$HOME/.config/network-dashboard-next.env}"
SERVICE="network-dashboard-next.service"
BACKUP_DIR="$HOME/.local/share/network-dashboard-next/backups"
READINESS_REPORT="$HOME/.cache/network-dashboard-next/readiness-report.json"
RUNTIME_FILE="$HOME/.cache/network-dashboard-next/runtime.env"
LIVE_DB_PATH="${LIVE_DASHBOARD_DB_PATH:-$HOME/.hermes/state/family_budget.sqlite3}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Next är inte installerad: $ENV_FILE saknas." >&2
  echo "Kör scripts/install.sh första gången." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

NEXT_DB_PATH="${DASHBOARD_DB_PATH:-}"
if [[ -z "$NEXT_DB_PATH" || ! -f "$NEXT_DB_PATH" ]]; then
  echo "Befintlig Next-databas saknas: ${NEXT_DB_PATH:-inte konfigurerad}" >&2
  exit 1
fi
if [[ "$(realpath -m "$NEXT_DB_PATH")" == "$(realpath -m "$LIVE_DB_PATH")" ]]; then
  echo "Avbryter: Next-databasen pekar på live-databasen." >&2
  exit 1
fi

mkdir -p "$APP_DIR" "$BACKUP_DIR" "$(dirname "$READINESS_REPORT")"

if [[ "$(realpath -m "$SOURCE_DIR")" != "$(realpath -m "$APP_DIR")" ]]; then
  rsync -a --delete --exclude '.git' --exclude '.venv' "$SOURCE_DIR/" "$APP_DIR/"
fi

VENV="$APP_DIR/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -e "$APP_DIR[dev]"

"$VENV/bin/python" -m compileall -q "$APP_DIR/app" "$APP_DIR/migrations" "$APP_DIR/scripts" "$APP_DIR/tests" "$APP_DIR/run.py"
"$VENV/bin/ruff" check "$APP_DIR/app" "$APP_DIR/migrations" "$APP_DIR/scripts" "$APP_DIR/tests"
"$VENV/bin/pytest" "$APP_DIR/tests"

MIGRATION_RESULT="$("$VENV/bin/python" "$APP_DIR/scripts/migrate_db.py" upgrade --database "$NEXT_DB_PATH" --backup-dir "$BACKUP_DIR")"
printf '%s\n' "$MIGRATION_RESULT"
LATEST_BACKUP="$(printf '%s' "$MIGRATION_RESULT" | "$VENV/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["backup"])')"
printf 'LATEST_BACKUP=%q\nDATABASE=%q\nLIVE_DATABASE=%q\n' "$LATEST_BACKUP" "$NEXT_DB_PATH" "$LIVE_DB_PATH" > "$HOME/.cache/network-dashboard-next/last-update.env"
chmod 600 "$HOME/.cache/network-dashboard-next/last-update.env"

systemctl --user daemon-reload
systemctl --user restart "$SERVICE"

rm -f "$RUNTIME_FILE"
for _ in {1..30}; do
  [[ -s "$RUNTIME_FILE" ]] && break
  sleep 0.5
done
if [[ ! -s "$RUNTIME_FILE" ]]; then
  systemctl --user status "$SERVICE" --no-pager || true
  echo "Next skrev ingen runtime-fil efter uppdateringen." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$RUNTIME_FILE"
set +e
"$VENV/bin/python" "$APP_DIR/scripts/readiness_report.py" \
  --root "$APP_DIR" \
  --origin "$ORIGIN" \
  --live-origin "${LEGACY_ORIGIN:-http://127.0.0.1:8792}" \
  --database "$NEXT_DB_PATH" \
  --live-database "$LIVE_DB_PATH" \
  --env-file "$ENV_FILE" \
  --secrets "${INTEGRATION_SECRETS_PATH:-$HOME/.config/network-dashboard-next/integration-secrets.json}" \
  --google-token "${GOOGLE_TOKEN_PATH:-$HOME/.config/network-dashboard-next/google_token.json}" \
  --google-client "${GOOGLE_CLIENT_SECRETS_PATH:-$HOME/.config/network-dashboard-next/google_client_secret.json}" \
  --legacy-report "$HOME/.cache/network-dashboard-next/legacy-config-import.json" \
  --service "$SERVICE" > "$READINESS_REPORT"
READINESS_EXIT=$?
set -e
chmod 600 "$READINESS_REPORT"
cat "$READINESS_REPORT"

if [[ "$READINESS_EXIT" -ne 0 ]]; then
  echo "Readiness blockerade uppdateringen. Next stoppas; liveappen påverkas inte." >&2
  systemctl --user stop "$SERVICE" || true
  echo "Databasbackup före migrering: $LATEST_BACKUP" >&2
  exit "$READINESS_EXIT"
fi

cat <<EOF
Next uppdaterades utan att live-databasen kopierades om.
Next-databas: $NEXT_DB_PATH
Backup före migrering: $LATEST_BACKUP
Origin: $ORIGIN
Readiness: $READINESS_REPORT
EOF
