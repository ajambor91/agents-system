#!/usr/bin/env bash
set -euo pipefail

# Lokalne renderowanie resources/agents-system.module.json: --system albo --dev.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"

exec python3 "$APPLICATION_ROOT/src/internal_scripts/test_render_modules.py" "$@"

