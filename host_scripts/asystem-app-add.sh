#!/usr/bin/env bash
set -euo pipefail
# Flagi: --repo-name, --repository-path/--repo-path, --entrypoint, --start.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"
exec python3 "$ROOT_DIR/src/agents-system/main.py" app-add "$@"
