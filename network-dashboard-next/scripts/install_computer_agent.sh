#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -lt 2 ]]; then
  echo "Användning: $0 <Next-origin> <engångstoken> [agentnamn]" >&2
  exit 2
fi

ORIGIN="${1%/}"
TOKEN="$2"
AGENT_NAME="${3:-$(hostname)}"
APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
VENV="$APP_DIR/.venv"
CONFIG="$HOME/.config/network-dashboard-next-agent.json"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/network-dashboard-next-agent.service"

if [[ ! "$ORIGIN" =~ ^https?:// ]]; then
  echo "Origin måste börja med http:// eller https://" >&2
  exit 2
fi
if [[ ${#TOKEN} -lt 20 ]]; then
  echo "Agenttoken verkar vara ogiltig" >&2
  exit 2
fi
if [[ ! -x "$VENV/bin/python" ]] || [[ ! -f "$APP_DIR/scripts/computer_agent.py" ]]; then
  echo "Installera Network Dashboard Next först: $APP_DIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$CONFIG")" "$SERVICE_DIR"
"$VENV/bin/python" - <<PY
import json
from pathlib import Path
path = Path("$CONFIG")
payload = {
    "origin": "$ORIGIN",
    "token": "$TOKEN",
    "name": "$AGENT_NAME",
    "dashboard_url": "$ORIGIN",
    "interval_seconds": 60,
    "verify_tls": True,
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
path.chmod(0o600)
PY

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Lindells restricted computer agent
After=default.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$VENV/bin/python $APP_DIR/scripts/computer_agent.py --config $CONFIG
Restart=on-failure
RestartSec=15
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now network-dashboard-next-agent.service

cat <<EOF
Agent installerad som användartjänst.
Konfiguration: $CONFIG (läge 600)
Status: systemctl --user status network-dashboard-next-agent.service --no-pager
Logg: journalctl --user -u network-dashboard-next-agent.service -n 100 --no-pager
EOF
