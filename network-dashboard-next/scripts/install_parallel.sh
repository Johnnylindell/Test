#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$APP_DIR/.venv"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/network-dashboard-next.service"
ENV_FILE="$HOME/.config/network-dashboard-next.env"

mkdir -p "$APP_DIR" "$SERVICE_DIR"
rsync -a --delete --exclude '.git' --exclude '.venv' "$SOURCE_DIR/" "$APP_DIR/"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -e "$APP_DIR[dev]"

cat > "$ENV_FILE" <<EOF
LEGACY_ORIGIN=http://127.0.0.1:8792
DASHBOARD_DB_PATH=$HOME/.hermes/state/family_budget.sqlite3
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

[Install]
WantedBy=default.target
EOF

"$VENV/bin/pytest" "$APP_DIR/tests"
systemctl --user daemon-reload
systemctl --user enable --now network-dashboard-next.service
sleep 2
systemctl --user status network-dashboard-next.service --no-pager

echo
echo "Den gamla appen på port 8792 har inte ändrats."
echo "Se vald port med: journalctl --user -u network-dashboard-next.service -n 30 --no-pager"
