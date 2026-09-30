#!/usr/bin/env bash
set -euo pipefail
# Flagi globalne: -h/--help, --human, --human-raw, --agent, --json, --interactive.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"
exec python3 "$ROOT_DIR/src/app_api/main.py" "$@"
