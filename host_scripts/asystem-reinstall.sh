#!/usr/bin/env bash
set -euo pipefail
# Flags: --yes, --journal PATH, -h/--help; see JSON help for operation-specific flags.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"
ENTRYPOINT="$APPLICATION_ROOT/src/install/__main__.py"
if [[ ! -f "$ENTRYPOINT" ]]; then
    ENTRYPOINT="$APPLICATION_ROOT/install/src/__main__.py"
fi
exec python3 "$ENTRYPOINT" reinstall "$@"
