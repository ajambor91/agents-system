#!/usr/bin/env bash
set -euo pipefail
# Required flag: --journal ABSOLUTE_JOURNAL_DIRECTORY.

SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
APPLICATION_ROOT="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"

exec python3 "$APPLICATION_ROOT/install/main.py" rollback "$@"
