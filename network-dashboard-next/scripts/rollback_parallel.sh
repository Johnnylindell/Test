#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
STATE_FILE="$HOME/.cache/network-dashboard-next/last-install.env"
SERVICE="network-dashboard-next.service"

systemctl --user disable --now "$SERVICE" 2>/dev/null || true
rm -f "$HOME/.cache/network-dashboard-next/runtime.env"

if [[ "${RESTORE_DATABASE:-false}" == "true" ]]; then
  if [[ ! -f "$STATE_FILE" ]]; then
    echo "Rollbackinformation saknas: $STATE_FILE" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$STATE_FILE"
  if [[ -z "${LATEST_BACKUP:-}" || -z "${DATABASE:-}" ]]; then
    echo "Rollbackinformationen är ofullständig." >&2
    exit 1
  fi
  "$APP_DIR/.venv/bin/python" "$APP_DIR/scripts/migrate_db.py" restore \
    --database "$DATABASE" --backup "$LATEST_BACKUP"
  echo "Databasen återställdes från: $LATEST_BACKUP"
else
  echo "Parallelltjänsten stoppades. Databasen ändrades inte."
  echo "Full databaserollback: RESTORE_DATABASE=true $APP_DIR/scripts/rollback_parallel.sh"
fi

echo "Den gamla tjänsten och port 8792 berördes inte."
