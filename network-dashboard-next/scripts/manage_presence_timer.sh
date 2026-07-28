#!/usr/bin/env bash
set -Eeuo pipefail

ACTION="${1:-status}"
APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
PYTHON="${PYTHON:-$APP_DIR/.venv/bin/python}"
BRIDGE="$APP_DIR/scripts/presence_bridge.py"
ENV_FILE="${ENV_FILE:-$HOME/.config/network-dashboard-next.env}"
CONFIG_FILE="${PRESENCE_CONFIG:-$HOME/.config/network-dashboard-next-presence.json}"
STATE_FILE="${PRESENCE_STATE:-$HOME/.hermes/state/lan_new_device_watch.json}"
RUNTIME_FILE="${RUNTIME_FILE:-$HOME/.cache/network-dashboard-next/runtime.env}"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="network-dashboard-next-presence.service"
TIMER_NAME="network-dashboard-next-presence.timer"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME"
TIMER_FILE="$SERVICE_DIR/$TIMER_NAME"
INTERVAL_SECONDS="${PRESENCE_INTERVAL_SECONDS:-60}"

usage() {
  cat <<'EOF'
Hantera den uttryckligt aktiverade närvarobryggan för Dashboard Next.

Användning:
  bash scripts/manage_presence_timer.sh enable
  bash scripts/manage_presence_timer.sh disable
  bash scripts/manage_presence_timer.sh status
  bash scripts/manage_presence_timer.sh uninstall

Bryggan gör ingen nätverksskanning. Den läser endast den befintliga LAN-watcherns
statusfil och skickar observationer för uttryckligt konfigurerade telefoner.
EOF
}

validate_interval() {
  if [[ ! "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || (( INTERVAL_SECONDS < 60 || INTERVAL_SECONDS > 3600 )); then
    echo "PRESENCE_INTERVAL_SECONDS måste vara ett heltal mellan 60 och 3600." >&2
    exit 2
  fi
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "$label saknas: $path" >&2
    exit 1
  fi
}

validate_setup() {
  validate_interval
  require_file "$PYTHON" "Next Python-miljö"
  require_file "$BRIDGE" "Närvarobryggan"
  require_file "$ENV_FILE" "Next miljöfil"
  require_file "$CONFIG_FILE" "Närvarokonfiguration"
  require_file "$STATE_FILE" "LAN-watcherns statusfil"
  chmod 600 "$CONFIG_FILE"

  local dry_run configured
  dry_run="$(
    "$PYTHON" "$BRIDGE" \
      --state "$STATE_FILE" \
      --config "$CONFIG_FILE" \
      --runtime-file "$RUNTIME_FILE" \
      --dry-run
  )"
  configured="$(printf '%s' "$dry_run" | "$PYTHON" -c 'import json,sys; print(int(json.load(sys.stdin).get("configured", 0)))')"
  if (( configured < 1 )); then
    echo "Ingen aktiverad och komplett telefonkoppling finns i $CONFIG_FILE." >&2
    echo "Aktiveringen avbryts utan att någon timer skapas." >&2
    exit 1
  fi
  echo "Validerade telefonkopplingar: $configured"
}

write_units() {
  mkdir -p "$SERVICE_DIR"
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Dashboard Next privacy-preserving presence bridge
After=network-dashboard-next.service
Wants=network-dashboard-next.service

[Service]
Type=oneshot
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart="$PYTHON" "$BRIDGE" --state "$STATE_FILE" --config "$CONFIG_FILE" --runtime-file "$RUNTIME_FILE"
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only

[Install]
WantedBy=default.target
EOF

  cat > "$TIMER_FILE" <<EOF
[Unit]
Description=Run Dashboard Next presence bridge periodically

[Timer]
OnActiveSec=15s
OnUnitActiveSec=${INTERVAL_SECONDS}s
AccuracySec=10s
Persistent=true
Unit=$SERVICE_NAME

[Install]
WantedBy=timers.target
EOF
  chmod 600 "$SERVICE_FILE" "$TIMER_FILE"
}

enable_timer() {
  validate_setup
  write_units
  systemctl --user daemon-reload
  systemctl --user enable --now "$TIMER_NAME"
  echo "Närvarobryggan är aktiverad med intervall ${INTERVAL_SECONDS} sekunder."
  echo "Ingen skanning startades; bryggan läser endast $STATE_FILE."
  systemctl --user list-timers "$TIMER_NAME" --no-pager || true
}

disable_timer() {
  systemctl --user disable --now "$TIMER_NAME" 2>/dev/null || true
  echo "Närvarotimern är avstängd. Konfiguration och unit-filer finns kvar."
}

uninstall_timer() {
  systemctl --user disable --now "$TIMER_NAME" 2>/dev/null || true
  rm -f "$SERVICE_FILE" "$TIMER_FILE"
  systemctl --user daemon-reload
  systemctl --user reset-failed "$SERVICE_NAME" 2>/dev/null || true
  echo "Närvarotimerns unit-filer är borttagna. Telefonkonfigurationen har lämnats orörd."
}

show_status() {
  echo "Timer: $TIMER_FILE"
  echo "Service: $SERVICE_FILE"
  echo "Konfiguration: $CONFIG_FILE"
  echo "Källstatus: $STATE_FILE"
  systemctl --user status "$TIMER_NAME" --no-pager 2>/dev/null || true
  systemctl --user list-timers "$TIMER_NAME" --no-pager 2>/dev/null || true
}

case "$ACTION" in
  enable|--enable)
    enable_timer
    ;;
  disable|--disable)
    disable_timer
    ;;
  uninstall|--uninstall)
    uninstall_timer
    ;;
  status|--status)
    show_status
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
