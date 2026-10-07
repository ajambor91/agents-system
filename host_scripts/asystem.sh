#!/usr/bin/env bash
set -euo pipefail
# system modules: --installed (pliki JSON) lub --running (runtime Unix socket).
# Flagi globalne: -h/--help, --human, --human-raw, --agent, --json, --interactive.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"
PYTHONPATH="$ROOT_DIR/src:$ROOT_DIR/src/lib${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python3 -m agents_system_cli "$@"
