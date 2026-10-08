# Agents System installer

Ta aplikacja jest implementacją nadrzędnego kontraktu
[`src/resources/installer.json`](src/resources/installer.json). Nie jest komendą control plane z
`src/agents_system`; ma własny entrypoint `src/__main__.py`, klasę `Installer` oraz
rollback sterowany dziennikiem.

## Uruchomienie

Instalacja wymaga roota. Bez `--mode` wybierany jest `system`:

```bash
sudo ./install/install.sh --yes --mode dev --invoker "$USER"
sudo ./install/install.sh --yes --mode system --invoker "$USER"
```

Przy zwykłym `sudo` opcję `--invoker` można pominąć, ponieważ instalator użyje
`SUDO_USER`. W trybie `dev` bezpośrednie uruchomienie z konta root bez `SUDO_USER` wymaga
`--invoker`; tryb `system` wybiera wtedy użytkownika wywołującego.

`dev` bez `--clone-repo` nie kopiuje repozytorium: tworzy dowiązanie instalacyjne do bieżącego checkoutu i używa konta wywołującego. `dev --clone-repo` tworzy lub wykorzystuje dedykowane konto `USER_SYSTEM` i kopiuje pełne repozytorium wyłącznie do katalogu domowego `USER_SYSTEM` (`USER_SYSTEM_HOME/agents-system`); nie kopiuje go do katalogu invokera.
Tryb `system` ma fallbacki `/opt`, `/etc/<APP_NAME>`, `/var/lib/<APP_NAME>`
i `/run/<APP_NAME>`. Wartości są rozwiązywane kolejno: jawna flaga CLI,
`resources/default_install.json` (jeśli istnieje), `install/src/resources/default_install.json`,
a na końcu fallback trybu.

Istniejące cele zatrzymują instalację. `--force` pozwala zastąpić wyłącznie
cele oznaczone markerem tego instalatora; obce katalogi, jednostki i komendy są
odrzucane.

Po przygotowaniu katalogów danych instalator kopiuje `resources/agents-system.json`
do `INSTALLED_MODULES_DIR/agents-system.json`. Ścieżkę odczytuje z wyrenderowanego
`app_env.json`. Plik ma uprawnienia `0660` i właściciela aplikacji; zapis jest atomowy
i objęty rollbackiem. Istniejący plik wymaga `--force`.

Po pozostałych zmianach plików, przed uruchomieniem runtime, instalator zapisuje
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
sudo ./install/rollback.sh --yes --journal /tmp/agents-system-install_...
```

Rollback akceptuje wyłącznie dokładny, zweryfikowany katalog dziennika i
odwraca operacje w kolejności odwrotnej. Nie usuwa zasobów, których pochodzenia
nie potwierdza dziennik.

## Aktualny entrypoint i operacje lifecycle

Wszystkie wrappery są w `install/` i uruchamiają wspólny entrypoint
`install/src/__main__.py` przez bezpośrednie wywołanie Pythona.
Każdy use-case (`Installer`, `Uninstaller`, `Reinstaller`, `Reconfigure`,
`InstallationRollback`) dziedziczy po `InstallerParent`. Wspólne operacje
plikowe, parsowanie, walidacja pochodzenia i transakcje należą do `shared/`,
a stałe do `consts/`.

```bash
sudo ./install/install.sh --yes --mode system
sudo ./install/reinstall.sh --yes --journal /tmp/agents-system-install_...
sudo ./install/reinstall.sh --yes --journal /tmp/agents-system-install_... --source /path/to/checkout
sudo ./install/reconfigure.sh --yes --journal /tmp/agents-system-install_... --envs /path/to/new/app_env.json
sudo ./install/uninstall.sh --yes --journal /tmp/agents-system-install_...
sudo ./install/uninstall.sh --yes --journal /tmp/agents-system-install_... --purge-data
sudo ./install/rollback.sh --yes --journal /tmp/agents-system-install_...
```

Używaj dziennika zwróconego przez ostatnią udaną operację. Reinstalacja jest
transakcyjnym zastąpieniem aplikacji z zachowaniem aktywnego `app_env.json`
i danych. Odinstalowanie usuwa sprawdzone wrappery, jednostkę systemd,
konfigurację, katalog runtime oraz aplikację. W trybie dev bez klonowania
usuwa dowiązanie instalacyjne, wskaźnik `src/.env` i wygenerowaną paczkę `src/install`; checkout pozostaje.
Dane i konta są zachowane. `--purge-data` usuwa także oznaczony katalog danych.

`--envs` wskazuje pełny, wyrenderowany dokument `kind:
"agents-system-environment"`, `schema_version: 1`. Jest odczytywany i walidowany
przed otwarciem dziennika, zatrzymaniem usługi i utworzeniem kopii zapasowych.
Wymagane są zmienne kontraktu, ich opisy i przykłady, prawidłowe typy, nazwy,
bezpieczne ścieżki oraz zgodność powiązanych ścieżek. Model odrzuca duplikaty,
niepoprawne wartości i nierozwiązane placeholdery; `{{agent_name}}` pozostaje
obsługiwanym placeholderem szablonów agenta.

Reconfigure zmienia konfigurację, odtwarza klasę `Configuration` i manifest
listy modułów oraz aktualizuje jednostkę systemd. Ścieżki instalacji, danych,
runtime, aktywnego JSON i konta nie mogą się zmienić; taka zmiana wymaga
osobnej migracji zasobów. Usługa systemowa jest zatrzymywana przed zmianami
i ponownie uruchamiana po ich zastosowaniu. W dev runtime musi być zatrzymany,
a jego sockety usunięte przed operacją lifecycle.

Każda operacja mutująca tworzy własny dziennik. Błąd powoduje próbę rollbacku,
obejmującą konfigurację, wygenerowane pliki, dowiązania i wcześniejszy stan
usługi. Odinstalowanie także można cofnąć przez jego dziennik. Operacje nie
pobierają niczego z sieci; `--source` wybiera istniejący lokalny checkout.
Kontrakty i manifesty API poszczególnych wrapperów znajdują się w `install/`.

Generator wywołany przez instalator otrzymuje kontrolowane środowisko procesu
z wcześniej rozwiązaną tożsamością instalacji i systemowym `PATH`. Nie odczytuje
konfiguracji poprzedniej instalacji przez hostowy `get_var`. Reguły pierwszeństwa
konfiguracji aplikacji i samodzielnie wywoływanego renderera pozostają opisane
w kontrakcie środowiska.

Instalator kopiuje `install/src` do `MODULES_DIR/install`, czyli `APP_DIR/src/install`
według aktywnego `app_env.json`, również w trybie dev. W `/usr/local/bin`
publikuje dowiązania `asystem-uninstall`, `asystem-reinstall` i
`asystem-reconfigure` do wrapperów aplikacji. Tryb dev pozwala jawnie wybrać
inny katalog przez `--commands-dir`.

Każda operacja wymaga `--yes`. `--help` i `-h` działają bez potwierdzenia
i bez roota. Metoda `InstallerParent.help()` wybiera JSON w `resources/`
paczki: `installer.json`, `uninstaller.json`, `reinstaller.json`,
`reconfigure.json` albo `rollback.json`. Pomoc przedstawia użycie i opcje
konkretnej komendy. Przykład: `asystem-reconfigure --help`.

## Dostęp grupowy

Instalator przygotowuje `APP_DATA_DIR` i `APP_RUNTIME_DIR`; aplikacja nie
przygotowuje katalogu danych podczas listowania. Katalogi współdzielone mają
tryb `2770` (dziedziczenie grupy), pliki `0660`, a pliki wykonywalne `0770`.
Grupa dostępu ma nazwę rozwiązanego `USER_SYSTEM`, również gdy pierwotna grupa
konta `USER_GROUP` ma inną nazwę. Konto aplikacji należy do grupy dostępu.

Na końcu instalacji użytkownik z `--invoker`, następnie `SUDO_USER`, a w trybie
system bez sudo użytkownik wywołujący, zostaje dodany do tej grupy bez usuwania
pozostałych członkostw. Nowe członkostwo zacznie działać po ponownym logowaniu.
W trybie dev bez klonowania uprawnienia obejmują bieżący checkout. Zmiany jego
metadanych, istniejących katalogów stanu i członkostwa można cofnąć rollbackiem.
