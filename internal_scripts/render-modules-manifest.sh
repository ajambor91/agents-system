#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"

exec python3 "$APPLICATION_ROOT/src/internal_scripts/render_modules_manifest.py" "$@"
