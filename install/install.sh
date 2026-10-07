#!/usr/bin/env bash
set -euo pipefail
# Flags: --yes, -h/--help, --mode system|dev, paths/accounts, --force, --verbose; see --help.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
INSTALL_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd -P)"
exec python3 "$INSTALL_ROOT/src/__main__.py" install "$@"
