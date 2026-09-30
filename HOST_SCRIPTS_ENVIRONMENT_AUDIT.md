# Audyt `host_scripts`, aplikacji `src/*` i konfiguracji środowiska

Data audytu: 2026-09-29

## 1. Podsumowanie

Repozytorium ma 18 publicznych wrapperów w `host_scripts/`. Wszystkie są
cienkimi adapterami Bash: ustalają fizyczny katalog repozytorium i wywołują
entrypoint Pythona z niezmienionym `"$@"`. Wyjątkiem jest
`asystem-env-export.sh`, który dodatkowo pilnuje, aby eksport do bieżącej
powłoki odbywał się przez funkcję załadowaną poleceniem `source`.

Najważniejsze ustalenia:

1. `src/agents-system` jest faktycznie obsługiwany przez wrappery i ma
   kontrakty flag w plikach JSON.
2. `src/app_api` obsługuje konsolę `asystem`, ale wszystkie komendy sekcji
   `agents` nadal kończą się wynikiem `Not implemented yet.`. Nie wywołują
   jeszcze przeniesionego `src/agents-manager`.
3. `src/agents-manager`, `src/agents-data` i `src/agents-data-runtime` mają
   własne parsery CLI, lecz nie mają jeszcze bezpośrednich wrapperów w
   `host_scripts/`.
4. `src/agents-data-backend` jest wyłącznie szkieletem i nie przyjmuje flag.
5. Kontrakt `resources/app_env.template.json` jest zsynchronizowany z
   `internal_scripts/render-app-env.json` i obejmuje 49 zmiennych wraz z
   przełącznikiem `BASH_SOURCE`.
6. Kod aplikacji korzysta z kanonicznych nazw kontraktu; zmienne systemowe i
   per-agent pozostają jawnie oddzielone.

Audyt jest analizą statyczną kodu i kontraktów. Nie uruchamia usług, nie zmienia
konfiguracji hosta i nie zakłada, że migrowane aplikacje są już zintegrowane.

## 2. Co robią wrappery `host_scripts`

Podczas instalacji nazwa pliku jest publikowana w `/usr/local/bin` bez
rozszerzenia, a myślniki są zamieniane na podkreślenia. Przykład:
`host_scripts/asystem-app-add.sh` staje się `asystem_app_add`.

Wszystkie komendy control plane obsługują także `-h/--help`, nawet jeśli tabela
nie powtarza tej flagi w każdym wierszu.

| Wrapper / komenda | Docelowa komenda Pythona | Flagi i argumenty | Rzeczywiste działanie |
| --- | --- | --- | --- |
| `asystem-app-add.sh` / `asystem_app_add` | `agents-system app-add` | `-r/--repo-name` wymagane, `--repository-path` lub `--repo-path`, `--entrypoint`, `--start` | Rejestruje entrypoint modułu w `modules.json`; może uruchomić wspólny runtime. |
| `asystem-app-call.sh` / `asystem_app_call` | `agents-system app-call` | `-n/--name` wymagane, `-p/--payload JSON` | Wysyła żądanie JSON do modułu przez Unix socket wspólnego runtime. |
| `asystem-app-list.sh` / `asystem_app_list` | `agents-system app-list` | brak poza help | Odczytuje i wypisuje rejestr modułów. |
| `asystem-app-remove.sh` / `asystem_app_remove` | `agents-system app-remove` | `-n/--name` wymagane | Usuwa wpis modułu z rejestru; nie usuwa repozytorium. |
| `asystem-env-init.sh` / `asystem_env_init` | `agents-system env-init` | dokładnie jedno z `-d/--default`, `-f/--file PATH`, `-i/--interactive`; opcjonalnie `--force` | Waliduje dokument, zapisuje `resources/app_env.json`, tworzy centralny symlink, generuje `environment.sh` i jako root `/etc/profile.d/agents-system.sh`. |
| `asystem-env-export.sh` / `asystem_env_export` | `agents-system env-export` | `-l/--local` albo `-f/--file PATH` | Renderuje bezpiecznie cytowane instrukcje `export`. Wywołany bezpośrednio na TTY zwraca błąd; funkcja z `/etc/profile.d/agents-system.sh` przechwytuje wynik i wykonuje `eval` w bieżącej powłoce. |
| `get-var.sh` / `get_var` | `agents-system get-var` | `-l/--local`, opcjonalny positional `NAME` | Czyta jedną wartość albo wszystkie wartości. Domyślnie używa centralnej konfiguracji, z `--local` pliku repozytorium. |
| `asystem-install.sh` / `asystem_install` | `agents-system install` | `-u/--user`, `--yes` | Wymaga roota; tworzy konto i katalogi, kopiuje checkout, publikuje wrappery i inicjalizuje środowisko. Bez `--yes` tylko opisuje operację. |
| `asystem-reinstall.sh` / `asystem_reinstall` | `agents-system reinstall` | `-u/--user`, `--yes` | Jak instalacja, ale przy istniejącym lokalnym `app_env.json` publikuje go ponownie zamiast zaczynać od szablonu. |
| `asystem-runtime-start.sh` / `asystem_runtime_start` | `agents-system runtime-start` | brak poza help | Uruchamia wspólny runtime przez `fork`; nie wywołuje `systemctl`. |
| `asystem-runtime-status.sh` / `asystem_runtime_status` | `agents-system runtime-status` | brak poza help | Czyta PID, socket i rejestr modułów wspólnego runtime. |
| `asystem-runtime-stop.sh` / `asystem_runtime_stop` | `agents-system runtime-stop` | brak poza help | Wysyła `SIGTERM` do PID zapisanego przez wspólny runtime. |
| `asystem-status.sh` / `asystem_status` | `agents-system system-status` | `--json` | Zbiera stan runtime, rejestr repozytoriów, ostatnią historię i katalogi agentów. |
| `ausers-create.sh` / `ausers_create` | `agents-system user-create` | `-u/--user`, `--yes` | Tworzy grupę, konto systemowe, `repositories` i `.agents`; wymaga sudo. |
| `ausers-get.sh` / `ausers_get` | `agents-system user-get` | `-u/--user`; maksymalnie jedno z `--home`, `-n/--name`, `-g/--group` | Odczytuje konto z bazy passwd/group. |
| `ausers-list.sh` / `ausers_list` | `agents-system user-list` | brak poza help | Wypisuje konta nierootowe posiadające katalog pod `/home`. |
| `ausers-set.sh` / `ausers_set` | `agents-system user-set` | wymagane `-u/--user`, `--yes` | Zapisuje wybrane konto do `user.json` w katalogu stanu runtime. |
| `asystem.sh` / `asystem` | `src/app_api/main.py` | globalne `--human`, `--human-raw`, `--agent`, `--json`, `--interactive`, `-h/--help`; dalej sekcja, komenda i jej flagi | Ładuje manifesty menu, opcjonalnie próbuje wspólnego runtime, a potem przekazuje zwalidowaną kopertę do `console-dispatch`. Sekcja `agents` jest obecnie tylko kontraktem UI. |

### Uwagi do wrapperów

- Wszystkie używają `set -euo pipefail`, `readlink -f` i `exec`, więc kod
  zakończenia pochodzi z aplikacji Pythona.
- Wrappery nie parsują domenowych flag i nie zmieniają granic argumentów.
- Komentarz `asystem-env-export.sh` nie wymienia publicznych `--local/--file`,
  choć implementacja je obsługuje.
- Nie istnieją jeszcze wrappery dla standalone `agents-manager`,
  `agents-data` ani `agents-data-runtime`.

## 3. Aplikacje pod `src/*`

| Aplikacja | Stan i odpowiedzialność | Czy przyjmuje flagi z powłoki? |
| --- | --- | --- |
| `src/agents-system` | Działający control plane. Parser jest generowany z `app/specs/*.json`; wykonuje środowisko, użytkowników, instalację, rejestr modułów i lifecycle wspólnego runtime. | Tak, przez komendę jako pierwszy argument i flagi opisane w tabeli wrapperów. Żaden spec nie deklaruje obecnie fallbacku `env` ani `var` dla pojedynczej flagi. |
| `src/runtime` | Wspólny rezydentny runtime aplikacji Python, rejestr modułów i Unix socket. `main.py` uruchamia bezpośrednio `serve()`. | Nie. Bezpośredni entrypoint nie ma parsera CLI; ścieżki bierze ze środowiska. Start/status/stop są wystawione przez control plane. |
| `src/app_api` | Hierarchiczna konsola manifest-driven, runtime-first z bezpiecznym fallbackiem lokalnym. | Tak: globalne tryby wyjścia, sekcja, komenda i flagi z manifestu. `--interactive` wymaga TTY. |
| `src/agents-manager` | Przeniesiona aplikacja desktopowa z własnym `argparse`. Nie jest jeszcze podłączona do `asystem agents`. | Tak, pełny zestaw opisano niżej. |
| `src/agents-data` | CLI wiadomości oraz placeholdery memory/sync. | Tak. `messege_send` ma rozbudowane flagi; pozostałe podkomendy są placeholderami. |
| `src/agents-data-runtime` | Osobny broker Unix socket ↔ Redis Streams ↔ backend HTTP. | Tak: wymagany positional `action` i opcjonalne flagi transportu. |
| `src/agents-data-backend` | Szkielet wypisujący opis JSON. | Nie. |
| `src/internal_scripts` | Dwa renderery instalatora: środowisko oraz manifest modułów. | Tak, ale są to komendy wewnętrzne, niepublikowane do `/usr/local/bin`. |

## 4. Flagi aplikacji niewystawionych bezpośrednio przez `host_scripts`

### `src/agents-manager`

| Podkomenda | Flagi |
| --- | --- |
| `install` | `-n/--name`, `-u/--user`, `-m/--model`, `-g/--gateway/--gateway-user`, `--force`, `--dry-run`, `-v/--verbose` |
| `exec` | wymagane `-n/--name`, `-c/--command`; opcjonalne `-r/--requested-by` |
| `delete` | wymagane `-n/--name`; implementacja nadal jest placeholderem |
| `update` | wymagane `-n/--name`; `-g/--gateway/--gateway-user`, `--dry-run`, `-v/--verbose` |
| `list` | `--json` |
| `status` | wymagane `-n/--name`; `--json` |
| `tools` | wymagane `-n/--name`; `--json` |
| `wakeup` | wymagane `-n/--name`; `-g/--gateway-user`, `--timeout` (domyślnie 600), `-v/--verbose`; koperta JSON przychodzi na stdin |

Manager buduje parser dopiero po utworzeniu `ApplicationContext`, więc nawet
`--help` wymaga poprawnego użytkownika stanu i znalezionego programu OpenClaw.

### `src/agents-data`

`messege_send` przyjmuje:

- `-s/--sender` albo nadawcę z `AGENT_NAME`;
- `--admin`, wzajemnie wykluczające się z `--sender`;
- wymagane i powtarzalne `-r/--receiver/--receivers`;
- `-t/--type info|question`;
- `-c/--content`, `--content-file` albo treść na stdin;
- `--app-comm-url`, `--timeout`, `--no-local-copy`, `--json`, `-v/--verbose`.

Nazwa `messege_send` nadal zawiera historyczną literówkę. `memory_write`,
`memory_get`, `memory_find`, `drive_sync` i `sync` nie mają jeszcze flag i
zwracają placeholder.

### `src/agents-data-runtime`

- wymagany positional `action`: `start`, `status`, `stop` albo `clients`;
- `--socket`;
- `--redis-url`;
- `--data-url`;
- `--consumer-group`;
- `--retry-seconds`.

### `src/app_api`

Globalnie przyjmuje jeden z trybów `--human`, `--human-raw`, `--agent`,
`--json`, `--interactive`. Dalej oczekuje `SECTION COMMAND [FLAGS]`.
Aktualnie jedyną sekcją jest `agents`, a jej manifest deklaruje `install`,
`update`, `exec`, `delete`, `list`, `status`, `tools`, `wakeup` oraz lifecycle
gatewaya. Wszystkie mają `implementation_status: not-implemented` i control
plane zwraca `Not implemented yet.`.

### `src/internal_scripts`

- `render_app_env.py`: wymagane `-m/--mode system|dev` oraz
  `-d/--install-dir`; opcjonalne `--user-system`, `--user-group`,
  `--user-system-home`, `--config-dir`, `--data-dir`, `--runtime-dir`,
  `-o/--output`, `-f/--force`, `-v/--verbose`.
- `render_modules_manifest.py`: wymagane `-a/--app-dir`; opcjonalne
  `-o/--output`, `-f/--force`, `-v/--verbose`.


## 5. Konfiguracja po ujednoliceniu

Wszystkie aplikacje czytają jeden kontrakt `resources/app_env.json` przez
`ApplicationEnvironment`. W trybie systemowym nadrzędny jest plik wskazany
przez `APP_ENV_PATH`, a kopia obok kodu jest fallbackiem. W trybie `dev`
aktywny pozostaje lokalny artefakt repozytorium.

| Aplikacja | Kanoniczne wartości |
| --- | --- |
| `src/runtime` i control plane | `APP_DATA_DIR`, `APP_RUNTIME_PATH`, `SYSTEM_AGENT_RUNTIME_PID`, `USER_SYSTEM`, `USER_SYSTEM_HOME` |
| `src/app_api` | `APP_RUNTIME_PATH` |
| `src/agents-manager` | `USER_SYSTEM`, `APP_DATA_DIR`; `SUDO_USER` pozostaje kontekstem wywołania |
| `src/agents-data` | `AGENTS_DATA_COMMUNICATION_APP`, `USER_SYSTEM_HOME`; `AGENT_NAME`, `AGENT_HOME`, `HOME` i `SUDO_USER` pozostają kontekstem procesu |
| `src/agents-data-runtime` | `AGENTS_DATA_RUNTIME_PATH`, `AGENTS_DATA_COMMUNICATION_APP` |

`COMM_REDIS_URL` i `COMM_RUNTIME_GROUP` nie zostały przemianowane na sztuczne
odpowiedniki. Ponieważ nie występują w odświeżonym kontrakcie, są odpowiednio
lokalnym domyślnym URL-em i opcjonalnymi flagami runtime.

## 6. Kolejność źródeł

- `INSTALL_MODE=dev` oraz `BASH_SOURCE=true`: zmienna powłoki, flaga CLI,
  `app_env.json`, wartość domyślna;
- każdy inny przypadek: flaga CLI, `app_env.json`, wartość domyślna;
- `INSTALL_MODE` i `BASH_SOURCE` są zawsze odczytywane z JSON-u, więc sama
  powłoka nie może włączyć własnego pierwszeństwa;
- `EnvironmentService` nie jest automatycznie aktywowany przez composition root.
  Jawne `load_into_environment()` działa tylko poza trybem `repo`;
- `BASH_SOURCE` nie jest eksportowane, ponieważ Bash rezerwuje tę nazwę dla
  własnej tablicy stosu plików źródłowych.

## 7. Stan instalatora

W trybie `dev` bez `--clone-repo` instalator nie kopiuje repozytorium: tworzy dowiązanie do bieżącego checkoutu. Z `--clone-repo` kopiuje pełne repozytorium wyłącznie do katalogu domowego `USER_SYSTEM`. W obu wariantach renderuje `resources/app_env.json` i publikuje zarządzaną konfigurację. W trybie `system` kopiuje
kod pod `/opt`, zapisuje kopię konfiguracji przy kodzie oraz publikuje ją w
`APP_CONFIG_DIR/app_env.json`. Oba tryby zapewniają aplikacji lokalny dostęp do
konfiguracji; tryb systemowy preferuje ścieżkę centralną.

Oba szablony systemd używają obecnie tych samych nazw: `INSTALL_MODE`,
`APP_NAME`, `APP_DIR`, `USER_SYSTEM`, `USER_SYSTEM_HOME`, `APP_CONFIG_DIR`,
`APP_DATA_DIR`, `APP_RUNTIME_DIR`, `APP_RUNTIME_PATH`, `APP_ENV_PATH` oraz
`MODULES_MANIFEST_PATH`.

## 8. Nadal otwarte kwestie

1. `asystem agents ...` nadal zwraca placeholder i nie uruchamia jeszcze
   przeniesionego `src/agents-manager`.
2. `agents-data-runtime` nadal nie ma osobnej publicznej jednostki systemd.
3. `agents-data` zachowuje historyczną nazwę komendy `messege_send`.
4. URL Redis Streams i nazwa consumer group nie są częścią globalnego
   `app_env.json`; przed wdrożeniem produkcyjnym trzeba zdecydować, czy należą
   do kontraktu aplikacji, czy do sekretnej konfiguracji usługi.
