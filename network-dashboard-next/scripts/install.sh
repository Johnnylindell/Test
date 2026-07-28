#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE_DB_PATH="${LIVE_DASHBOARD_DB_PATH:-$HOME/.hermes/state/family_budget.sqlite3}"

python3 "$ROOT/scripts/preflight_install.py" --live-database "$LIVE_DB_PATH"
exec bash "$ROOT/scripts/install_parallel.sh"
