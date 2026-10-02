#!/usr/bin/env bash
set -euo pipefail

# Renderuje oba lokalne JSON-y i generuje src/lib/configuration/configuration.py.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"

exec python3 "$APPLICATION_ROOT/src/internal_scripts/test_set_configuration.py" "$@"

