#!/usr/bin/env bash
set -euo pipefail
# Flags: --yes, -h/--help, --journal ABSOLUTE_JOURNAL_DIRECTORY, --envs ABSOLUTE_CONFIG_FILE, --verbose.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
INSTALL_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd -P)"
exec python3 "$INSTALL_ROOT/src/__main__.py" reconfigure "$@"
