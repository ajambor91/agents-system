#!/usr/bin/env bash
set -euo pipefail

SYSTEM_USER="user-system"
YES=false
SOURCE_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Użycie: sudo asystem_install --yes [--user NAZWA]

Tworzy lub przygotowuje użytkownika systemowego Agents System, jego katalog
repositories oraz publikuje host_scripts jako komendy.
EOF
}

fail() { printf 'Błąd: %s\n' "$*" >&2; exit 1; }

while (( $# > 0 )); do
  case "$1" in
    --yes) YES=true; shift ;;
    -u|--user)
      (( $# >= 2 )) || fail "$1 wymaga nazwy"
      SYSTEM_USER="$2"
      shift 2
      ;;
    --user=*) SYSTEM_USER="${1#*=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "nieznana opcja: $1" ;;
  esac
done

SYSTEM_HOME="/home/$SYSTEM_USER"
if [[ "$YES" != true ]]; then
  printf 'Ta operacja utworzy lub przygotuje użytkownika systemowego %s, katalog %s/repositories, konto nologin i linki komend w /usr/local/bin.\n' "$SYSTEM_USER" "$SYSTEM_HOME"
  printf 'Uruchom ponownie z --yes, aby potwierdzić.\n'
  exit 2
fi

[[ "$EUID" -eq 0 ]] || fail "uruchom przez sudo"
getent group "$SYSTEM_USER" >/dev/null || groupadd --system "$SYSTEM_USER"
if ! getent passwd "$SYSTEM_USER" >/dev/null; then
  nologin="$(command -v nologin || printf '/usr/sbin/nologin')"
  useradd --system --gid "$SYSTEM_USER" --home-dir "$SYSTEM_HOME" --create-home --shell "$nologin" "$SYSTEM_USER"
fi
install -d -m 2770 -o "$SYSTEM_USER" -g "$SYSTEM_USER" "$SYSTEM_HOME" "$SYSTEM_HOME/repositories" "$SYSTEM_HOME/.agents"
install -d -m 0755 /usr/local/bin /etc/profile.d
printf 'export USER_SYSTEM_USER=%q\nexport USER_SYSTEM_HOME=%q\n' "$SYSTEM_USER" "$SYSTEM_HOME" > /etc/profile.d/agents-system.sh
chown root:root /etc/profile.d/agents-system.sh
chmod 0644 /etc/profile.d/agents-system.sh

TARGET="$SYSTEM_HOME/repositories/agents-system"
if [[ "$(readlink -f -- "$SOURCE_ROOT")" != "$(readlink -m -- "$TARGET")" ]]; then
  install -d -m 2770 -o "$SYSTEM_USER" -g "$SYSTEM_USER" "$TARGET"
  cp -a -- "$SOURCE_ROOT/." "$TARGET/"
fi
chown -R "$SYSTEM_USER:$SYSTEM_USER" "$TARGET"
chmod -R u=rwX,g=rwX,o= "$TARGET"
for script in "$TARGET"/host_scripts/*.sh; do
  [[ -f "$script" ]] || continue
  command_name="$(basename "$script" .sh | tr '-' '_')"
  destination="/usr/local/bin/$command_name"
  [[ ! -e "$destination" || -L "$destination" ]] || fail "istnieje zwykły plik: $destination"
  ln -sfn -- "$script" "$destination"
done
printf 'Agents System zainstalowany dla %s w %s.\n' "$SYSTEM_USER" "$TARGET"
