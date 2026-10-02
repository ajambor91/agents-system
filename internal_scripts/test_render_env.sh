#!/usr/bin/env bash
set -euo pipefail

# Lokalne renderowanie resources/app_env.json: dokładnie --system albo --dev.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"

exec python3 "$APPLICATION_ROOT/src/internal_scripts/test_render_env.py" "$@"

