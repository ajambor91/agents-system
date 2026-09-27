#!/usr/bin/env bash
set -euo pipefail
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"
exec python3 "$ROOT_DIR/src/agents-system/main.py" remove "$@"
