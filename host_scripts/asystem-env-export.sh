#!/usr/bin/env bash
set -euo pipefail
# Backend funkcji powłoki: renderuje zwalidowane exporty dla eval/source.
SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd)"

for argument in "$@"; do
    if [[ "$argument" == "-h" || "$argument" == "--help" ]]; then
        exec python3 "$ROOT_DIR/src/agents-system/main.py" env-export "$@"
    fi
done

if [[ -t 1 ]]; then
    printf '%s\n' \
        'Błąd: asystem_env_export nie jest jeszcze funkcją bieżącej powłoki.' \
        'Wykonaj: source /etc/profile.d/agents-system.sh' \
        'Następnie ponownie wykonaj: asystem_env_export' >&2
    exit 2
fi

exec python3 "$ROOT_DIR/src/agents-system/main.py" env-export "$@"
