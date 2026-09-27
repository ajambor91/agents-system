#!/usr/bin/env bash
set -euo pipefail
TAG=""
REMOTE=origin
while (( $# > 0 )); do
  case "$1" in
    --tag) (( $# >= 2 )) || { printf 'Błąd: --tag wymaga wartości\n' >&2; exit 2; }; TAG="$2"; shift 2 ;;
    --tag=*) TAG="${1#*=}"; shift ;;
    --remote) REMOTE="$2"; shift 2 ;;
    --remote=*) REMOTE="${1#*=}"; shift ;;
    -h|--help) printf 'Użycie: internal_scripts/push.sh --tag X.Y.Z [--remote origin]\n'; exit 0 ;;
    *) printf 'Błąd: nieznana opcja: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ "$TAG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { printf 'Błąd: push wymaga taga semver przez --tag X.Y.Z\n' >&2; exit 2; }
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
GIT=(git -c "safe.directory=$ROOT_DIR")
[[ -z "$("${GIT[@]}" status --porcelain)" ]] || { printf 'Błąd: najpierw zatwierdź lokalne zmiany.\n' >&2; exit 1; }
"${GIT[@]}" rev-parse "$TAG" >/dev/null 2>&1 && { printf 'Błąd: tag już istnieje: %s\n' "$TAG" >&2; exit 1; }
"${GIT[@]}" tag -a "$TAG" -m "Release $TAG"
"${GIT[@]}" push "$REMOTE" HEAD
"${GIT[@]}" push "$REMOTE" "$TAG"
printf 'Wypchnięto commit i tag %s.\n' "$TAG"
