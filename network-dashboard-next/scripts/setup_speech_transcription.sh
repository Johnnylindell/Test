#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/network-dashboard-next}"
VENV="${VENV:-$APP_DIR/.venv}"
ENV_FILE="${ENV_FILE:-$HOME/.config/network-dashboard-next.env}"
SERVICE="${SERVICE:-network-dashboard-next.service}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/setup_speech_transcription.sh status
  bash scripts/setup_speech_transcription.sh enable /absolute/path/to/faster-whisper-model
  bash scripts/setup_speech_transcription.sh enable small --allow-download
  bash scripts/setup_speech_transcription.sh disable
EOF
}

set_env() {
  local key="$1"
  local value="$2"
  python3 - "$ENV_FILE" "$key" "$value" <<'PY'
from __future__ import annotations

import os
import tempfile
from pathlib import Path
import sys

path = Path(sys.argv[1]).expanduser()
key = sys.argv[2]
value = sys.argv[3]
path.parent.mkdir(parents=True, exist_ok=True)
lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
replacement = f"{key}={value}"
result = []
replaced = False
for line in lines:
    if line.startswith(key + "="):
        if not replaced:
            result.append(replacement)
            replaced = True
        continue
    result.append(line)
if not replaced:
    result.append(replacement)
fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent, text=True)
temporary = Path(temporary_name)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(result) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    os.chmod(path, 0o600)
finally:
    temporary.unlink(missing_ok=True)
PY
}

restart_service() {
  if systemctl --user is-active "$SERVICE" >/dev/null 2>&1; then
    systemctl --user restart "$SERVICE"
  else
    echo "Tjänsten kör inte; inställningen används nästa gång $SERVICE startas."
  fi
}

status_cmd() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Konfigurationsfilen saknas: $ENV_FILE"
    exit 1
  fi
  grep -E '^SPEECH_TRANSCRIPTION_(ENABLED|MODEL|DEVICE|COMPUTE_TYPE|MAX_BYTES|ALLOW_MODEL_DOWNLOAD)=' "$ENV_FILE" || true
  if [[ -x "$VENV/bin/python" ]]; then
    "$VENV/bin/python" - <<'PY'
import importlib.util
print("faster-whisper installerat:", bool(importlib.util.find_spec("faster_whisper")))
PY
  fi
}

action="${1:-status}"
case "$action" in
  status)
    status_cmd
    ;;
  enable)
    model="${2:-}"
    option="${3:-}"
    if [[ -z "$model" ]]; then
      usage >&2
      exit 2
    fi
    allow_download=false
    if [[ "$option" == "--allow-download" ]]; then
      allow_download=true
    elif [[ -n "$option" ]]; then
      usage >&2
      exit 2
    fi
    if [[ "$allow_download" != true ]]; then
      if [[ ! -d "$model" ]]; then
        echo "Modellsökvägen är inte en katalog: $model" >&2
        exit 1
      fi
      model="$(realpath -e "$model")"
    fi
    if [[ ! -x "$VENV/bin/pip" ]]; then
      echo "Next-miljön saknas: $VENV" >&2
      exit 1
    fi
    "$VENV/bin/pip" install -e "$APP_DIR[speech]"
    set_env SPEECH_TRANSCRIPTION_ENABLED true
    set_env SPEECH_TRANSCRIPTION_MODEL "$model"
    set_env SPEECH_TRANSCRIPTION_DEVICE cpu
    set_env SPEECH_TRANSCRIPTION_COMPUTE_TYPE int8
    set_env SPEECH_TRANSCRIPTION_MAX_BYTES 8388608
    set_env SPEECH_TRANSCRIPTION_ALLOW_MODEL_DOWNLOAD "$allow_download"
    restart_service
    status_cmd
    ;;
  disable)
    set_env SPEECH_TRANSCRIPTION_ENABLED false
    restart_service
    status_cmd
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
