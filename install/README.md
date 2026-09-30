# Agents System installer

Ta aplikacja jest implementacją nadrzędnego kontraktu
[`install.json`](install.json). Nie jest komendą control plane z
`src/agents-system`; ma własny entrypoint `main.py`, klasę `Installer` oraz
rollback sterowany dziennikiem.

## Uruchomienie

Instalacja wymaga roota. Bez `--mode` wybierany jest `system`:

```bash
sudo ./self/install.sh --mode dev --invoker "$USER"
sudo ./self/install.sh --mode system --invoker "$USER"
```

Przy zwykłym `sudo` opcję `--invoker` można pominąć, ponieważ instalator użyje
`SUDO_USER`. W trybie `dev` bezpośrednie uruchomienie z konta root bez `SUDO_USER` wymaga
`--invoker`; tryb `system` nie potrzebuje konta wywołującego.

`dev` bez `--clone-repo` nie kopiuje repozytorium: tworzy wyłącznie dowiązanie instalacyjne do bieżącego checkoutu i używa konta wywołującego. `dev --clone-repo` tworzy lub wykorzystuje dedykowane konto `USER_SYSTEM` i kopiuje pełne repozytorium wyłącznie do katalogu domowego `USER_SYSTEM` (`USER_SYSTEM_HOME/agents-system`); nie kopiuje go do katalogu invokera.
Tryb `system` ma fallbacki `/opt`, `/etc/<APP_NAME>`, `/var/lib/<APP_NAME>`
i `/run/<APP_NAME>`. Wartości są rozwiązywane kolejno: jawna flaga CLI,
`resources/default_install.json` (jeśli istnieje), `install/default_install.json`,
a na końcu fallback trybu.

Istniejące cele zatrzymują instalację. `--force` pozwala zastąpić wyłącznie
cele oznaczone markerem tego instalatora; obce katalogi, jednostki i komendy są
odrzucane.

Na samym końcu instalacji, po pozostałych mutacjach, instalator zapisuje
`APP_DIR/src/.env`. Plik zawiera dokładnie jedną zmienną:

```dotenv
ABSOLUTE_CONFIG_PATH=<wyrenderowany APP_ENV_PATH>
```

Zmiana jest rejestrowana w dzienniku i podlega rollbackowi.

## Dziennik i rollback

Każda operacja tworzy katalog `0700` należący do root:

```text
/tmp/agents-system-install_<UTC>_<losowy-sufiks>/
```

Po błędzie rollback wykonuje się automatycznie. Po sukcesie ścieżka dziennika
jest zwracana w wyniku i można użyć jej ręcznie:

```bash
sudo ./self/rollback.sh --journal /tmp/agents-system-install_...
```

Rollback akceptuje wyłącznie dokładny, zweryfikowany katalog dziennika i
odwraca operacje w kolejności odwrotnej. Nie usuwa zasobów, których pochodzenia
nie potwierdza dziennik.
