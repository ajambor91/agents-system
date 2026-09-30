#!/usr/bin/env bash
set -euo pipefail
# Modes: -m/--mode system|dev (system by default). See --help for account, path and clone flags.

SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"

exec python3 "$APPLICATION_ROOT/install/main.py" "$@"
