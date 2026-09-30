# Agents System

Instalator systemu jest osobną aplikacją opisaną przez
[`install/install.json`](install/install.json). Instrukcja użycia, tryby
`repo`/`system` i rollback znajdują się w [`install/README.md`](install/README.md).

Repozytorium jest docelowym monorepo systemu agentów. Kanoniczny opis
architektury znajduje się w [ARCHITECTURE.md](ARCHITECTURE.md), a najbliższe
plany scalenia w [AGENT_MANAGER_MERGE.md](AGENT_MANAGER_MERGE.md) oraz
[COMMUNICATION_STACK_MERGE.md](COMMUNICATION_STACK_MERGE.md).

Stałe entrypointy aplikacji:

| Aplikacja | Entrypoint | Stan |
| --- | --- | --- |
| agents-system | `src/agents-system/main.py` | zaimplementowana |
| runtime | `src/runtime/main.py` | zaimplementowana |
| agents-data-runtime | `src/agents-data-runtime/main.py` | przeniesiony broker komunikacji |
| app_api | `src/app_api/main.py` | zaimplementowana konsola/API |
| agents-manager | `src/agents-manager/main.py` | kod przeniesiony |
| agents-data | `src/agents-data/main.py` | kod przeniesiony |
| agents-data-backend | `src/agents-data-backend/main.py` | szkielet migracji |

Ścieżki te są jawne i stabilne; repozytorium nie używa katalogu
`src/agents_system/`.

`agents-system` jest repozytorium nadrzędnym dla lokalnego systemu agentów AI. Opisuje wspólne zasady, strukturę repozytoriów, bezpieczeństwo, lifecycle i kontrakty danych. Konkretne aplikacje oraz narzędzia są dostarczane przez osobne repozytoria.

## 1. Elementy systemu

| Element | Odpowiedzialność |
| --- | --- |
| `agents-system` | standardy, architektura, użytkownik systemowy, dokumentacja i wspólne szablony |
| `repo-manager` | clone, instalacja, aktualizacja, rejestracja, usuwanie i publikacja komend repozytoriów |
| `repo-manifests` | trwały rejestr, pełne dokumenty, historia JSONL i manifesty narzędzi agentów |
| `repo-template` | wzorcowe drzewo nowego repozytorium i instrukcje generatora |
| `agents-manager` | tworzenie, uruchamianie i monitorowanie agentów |
| moduły AI | konkretne runtime'y i aplikacje, np. Ollama |

Zależności są jednokierunkowe: repozytorium aplikacji korzysta ze standardu, Repo Managera i opcjonalnie API manifestów. `repo-manifests` nie zarządza Git ani użytkownikami, a `repo-manager` nie definiuje formatów manifestów narzędzi.

## 2. Standard repozytorium

Każde repozytorium ma jeden katalog główny i, zależnie od potrzeb, następujące elementy:

```text
project/
├── AGENTS.md                 # kontrakt dla agentów kodujących
├── README.md                 # dokumentacja dla człowieka
├── manifest.json             # opis repozytorium i publicznych komend
├── required_repo             # zależności repozytoryjne
├── usage                     # czytelny spis komend
├── .env.example              # przykład konfiguracji hosta
├── .gitignore                # musi ignorować .env
├── .system                   # pusty znacznik, tylko dla repo systemowego
├── host_scripts/             # publiczne wrappery Bash
├── internal_scripts/          # skrypty tylko dla tego repozytorium
├── self/                     # hooki lifecycle Repo Managera
├── src/                      # kod aplikacji
├── resources/                # pliki źródłowe i szablony
├── available_tools/          # lokalny katalog manifestów agentów, opcjonalny
└── repo_data/                # dowiązania do danych zarządzanych centralnie
```

`manifest.json` opisuje repozytorium i jego interfejs. Nie jest tym samym co globalny rejestr Repo Managera ani co manifest pojedynczego narzędzia. `repo_data/` jest widokiem danych, a nie miejscem do ręcznej edycji centralnego rejestru.

## 3. Warstwy wykonawcze

```text
agent lub człowiek
  -> /usr/local/bin/<command>
  -> host_scripts/<command>.sh
  -> src/<package>/main.py
  -> router i jedna klasa komendy
  -> serwisy domenowe
  -> system plików, Git albo API repo-manifests
```

- `host_scripts/` to cienkie publiczne API; nie zawiera logiki biznesowej.
- `src/` zawiera decyzje, walidację i operacje aplikacji.
- Jedna publiczna komenda odpowiada jednej klasie use-case.
- `internal_scripts/` mogą wykonywać tylko zadania wewnętrzne repozytorium.
- `self/` jest wywoływane przez Repo Managera i nie publikuje własnych wrapperów.
- Operacje systemowe i procesy są jawne, testowalne i wykonywane przez wąskie adaptery.

## 4. Lifecycle repozytorium

Typowa instalacja wygląda tak:

1. `repo_install` klonuje repozytorium i ustala ownera oraz tryb systemowy.
2. Odczytuje `required_repo` i próbuje zainstalować brakujące zależności.
3. Uruchamia opcjonalny `self/install.sh` albo `self/install.py` jako owner.
4. Hook może wygenerować lokalny stan na podstawie wersjonowanych szablonów.
5. Repo Manager zapisuje wpis w rejestrze i historię przez API `repo-manifests`.
6. Zwykłe pliki `host_scripts/*.sh` publikuje jako `/usr/local/bin/*`.

Przy aktualizacji hook `prepare` działa przed pull, a `update` po pull. Przy usuwaniu `uninstall` działa przed usunięciem checkoutu. Brak hooka oznacza pominięcie kroku, nie błąd.

## 5. Dwa rodzaje JSON

### Dane repozytorium

Repozytorium deklaruje własną tożsamość w `manifest.json`, np. nazwę, cel, tryb systemowy, entrypoint i komendy. Dane instalacji, owner, ścieżka, commit, status i historia należą do Repo Managera oraz `repo-manifests`.

### Manifest narzędzia agenta

Narzędzie dostępne dla agenta ma `kind: "tool-manifest"` i opisuje co najmniej:

```json
{
  "schema_version": 1,
  "kind": "tool-manifest",
  "id": "repo-list",
  "command": "repo_list",
  "executable": "/usr/local/bin/repo_list",
  "description": "List managed repositories.",
  "execution": {
    "mode": "read",
    "requires_confirmation": false,
    "requires_sudo": true,
    "interactive": false,
    "supports_dry_run": false,
    "idempotent": true
  },
  "arguments": [],
  "examples": [],
  "outputs": []
}
```

`execution.mode` może być `read`, `write`, `destructive`, `network` albo `mixed`. Agent nie powinien wykonywać operacji destrukcyjnej lub uprzywilejowanej bez spełnienia warunków zapisanych w manifeście.

## 6. Repo Manifests

`repo-manifests` tworzy w repozytorium aplikacji katalog:

```text
available_tools/
├── registry.json       # wygenerowane menu narzędzi
├── tool.schema.json    # schemat manifestu narzędzia
├── title.json          # tożsamość repozytorium
├── config.json         # konfiguracja odkrywania
├── struct.json         # deklaracja układu
└── tools/*.json        # linki lub kopie manifestów źródłowych
```

Źródłowe manifesty leżą zwykle w `internal_scripts/manifests/`, `manifests/`, `tools/manifests/` albo `.agent-tools/manifests/`. `registry.json` jest wynikiem scalania plików z `available_tools/tools/`; nie należy edytować go ręcznie.

Przykładowe polecenie inicjalizacji:

```bash
manifests_init --target /path/to/project --repo-id project --title "Project" \
  --description "Project tools" --tag automation
```

## 7. Agenci i dane runtime

Każdy agent działa jako odrębna tożsamość systemowa albo w kontrolowanym kontekście użytkownika. Jego konfiguracja i historia powinny być przechowywane w dedykowanym katalogu, np.:

```text
/home/user-system/.agents/<agent-id>/
├── runtime.json
├── shell.json
└── shells/
```

Executor agenta musi rozdzielać komendę, argumenty, ownera, uprawnienia, timeout i wynik. Nie wolno traktować opisu narzędzia jako zgody na dowolne wykonanie.

## 8. Dobre praktyki

- Najpierw opisz cel, odbiorców, komendy, zależności i skutki uboczne.
- Nie zgaduj logiki biznesowej na podstawie nazwy repozytorium.
- Trzymaj konfigurację hosta w `.env`, a reguły biznesowe w wersjonowanym modelu.
- Nigdy nie commituj `.env`; commituj `.env.example` z opisem wartości.
- Używaj list argumentów zamiast sklejanych poleceń shellowych.
- Waliduj ścieżki i nie nadpisuj istniejących danych bez jawnej zgody.
- Po każdej zmianie komendy aktualizuj implementację, `manifest.json`, `usage`, README, manifest narzędzia i testy.
- Szablon jest źródłem wejściowym, a wygenerowany rejestr jest artefaktem.
- Rejestr i historię zapisuj przez API `repo-manifests`, nie bezpośrednio.

## 9. Status ujednolicenia szablonów

Obecnie szablony manifestów narzędzi znajdują się w `repo-manifests/templates/`. Docelowo wspólne, stabilne szablony JSON powinny być wersjonowane w `agents-system`, a `repo-manifests` powinno je konsumować lub dystrybuować. Migracja musi zachować wersję schematu, kompatybilność generatora i testy przykładowego repozytorium.

Do czasu zakończenia migracji obowiązuje istniejący schemat `repo-manifests`, a nowe repozytoria mają wzorować się na `repo-template` i niniejszym dokumencie.

## 10. Rezydentne moduły aplikacji

`agents-system` może ładować aplikacje Python zainstalowanych repozytoriów do
jednego procesu runtime. Repozytorium może pozostawić klasyczne wrappery bez
zmian albo wyposażyć swój entrypoint w klienta runtime-first z lokalnym
fallbackiem:

```bash
asystem_app_add \
  --repo-name ai-module \
  --start
asystem_runtime_status
asystem_app_call --name ai-module --payload '{"action":"health"}'
```

Runtime przechowuje rejestr w `/home/user-system/.repos/modules.json`, ładuje
entrypoint leniwie i przeładowuje go po zmianie pliku. Udostępnia go przez Unix
socket. Moduł powinien eksportować `create_service()` zwracające callable albo
funkcję `handle(payload)`. Alternatywnie może udostępnić klasę `Application`
z metodą `handle`.

Runtime pobiera UID/GID klienta z `SO_PEERCRED`, nadpisuje zastrzeżone pole
`_runtime` i przechwytuje tekst wypisany przez starsze handlery. Nowe handlery
powinny zwracać JSON z wynikiem oraz strumieniami bez bezpośredniego drukowania.
Brak rejestracji zwraca `error_code: module_unavailable`, co pozwala klientowi
bezpiecznie uruchomić lokalny fallback przed rozpoczęciem operacji. Pozostałe
błędy nie zezwalają na automatyczne powtórzenie komendy.

Przy pierwszym odczycie po aktualizacji dotychczasowy plik
`/home/user-system/.agents/modules.json` jest automatycznie przenoszony do
nowej lokalizacji. Socket i PID runtime nadal pozostają w katalogu `.agents`.

Operacje: `asystem_app_add`, `asystem_app_list`, `asystem_app_remove`,
`asystem_runtime_start`, `asystem_runtime_stop`, `asystem_runtime_status` oraz
`asystem_app_call`.

Błędy operatorskie, na przykład próba usunięcia niezarejestrowanej nazwy,
zwracają kod `1` i krótki komunikat na `stderr` bez tracebacka Pythona.

## 11. Status i użytkownicy

Raport dla człowieka:

```bash
asystem_status
```

Raport maszynowy:

```bash
asystem_status --json
```

Raport pokazuje zainstalowane repozytoria, wersję, status, ścieżkę, ostatnią
akcję, ostatnie wpisy historii, stan runtime oraz katalogi agentów.

Zarządzanie użytkownikiem systemowym:

```bash
sudo ausers_create --user user-system --yes
ausers_get
ausers_get --home
ausers_list
sudo ausers_set --user user-system --yes
```

`ausers_create` bez `--yes` tylko opisuje plan i nie zmienia systemu.

## 12. Konfiguracja środowiska

Bootstrap i reinstalacja także przechodzą przez klasy Pythona, a wrappery Bash
jedynie przekazują argumenty. Obie operacje wymagają jawnego potwierdzenia:

```bash
sudo asystem_install --user user-system --yes
sudo asystem_reinstall --user user-system --yes
```

Instalacja przygotowuje konto, checkout, publiczne linki i od razu publikuje
domyślną konfigurację. Reinstalacja zachowuje istniejący
`resources/app_env.json` i ponownie tworzy z niego artefakty centralne.

Źródłem struktury jest wersjonowany `resources/app_env.template.json`. Każda
zmienna ma `name`, `value`, `description` i `example`. Wartości mogą korzystać
z placeholderów `${NAZWA}`, dlatego pełne ścieżki nie powtarzają
`/home/user-system`. Placeholdery domenowe w postaci `{{repository_name}}` są
zachowywane do późniejszego uzupełnienia przez aplikację.

Konfigurację inicjalizuje dokładnie jeden z trybów:

```bash
sudo asystem_env_init --default
sudo asystem_env_init --file /ścieżka/do/app_env.json
sudo asystem_env_init --interactive
```

Po walidacji dokument jest atomowo zapisywany jako ignorowany przez Git
`resources/app_env.json`. Następnie powstaje dowiązanie pod ścieżką wyliczoną
pod `APP_ENV_PATH`, plik `environment.sh` oraz — przy
uruchomieniu jako root — bezpieczna, root-owned konfiguracja
`/etc/profile.d/agents-system.sh`. Istniejący zwykły plik centralny nie jest
nadpisywany bez jawnego `--force`.

Aplikacje odczytują konfigurację bez automatycznego eksportowania jej do procesu.
W trybie `dev` z `BASH_SOURCE=true` obowiązuje kolejność: środowisko powłoki,
flaga CLI, `app_env.json`; w pozostałych przypadkach: flaga CLI, `app_env.json`.
Jawne ładowanie do środowiska przez `EnvironmentService` działa wyłącznie poza
trybem `repo`. `asystem_env_init` generuje również integrację powłoki w
`environment.sh` i `/etc/profile.d/agents-system.sh`. Po jej wczytaniu
`asystem_env_export` jest funkcją wykonującą bezpieczne eksporty bezpośrednio w
bieżącej powłoce:

```bash
asystem_env_export
echo "$APP_DATA_DIR"
```

Pierwsza konfiguracja nie może zmienić procesu powłoki, który uruchomił
`asystem_env_init`. Dla już otwartego terminala integrację wczytuje się raz:

```bash
source /etc/profile.d/agents-system.sh
```

Nowa sesja loginowa wczyta ją automatycznie. Wywołanie pliku wykonywalnego z
pominięciem funkcji, np. `/usr/local/bin/asystem_env_export`, nadal wypisuje
czyste instrukcje `export` dla automatyzacji.

`asystem_env_export --local` ładuje lokalny artefakt, a `--file PATH` dowolny
zgodny dokument. `get_var NAME` wypisuje pojedynczą wartość, `get_var` wszystkie
wartości w formacie `NAME=value`, natomiast `get_var --local` zawsze omija
środowisko procesu i czyta `resources/app_env.json`.

Parser wykrywa nieznane placeholdery, cykle, powtórzone nazwy, błędne nazwy
zmiennych i nieobsługiwaną wersję schematu przed pierwszym zapisem.

## 13. Konsola `asystem`

Publiczna konsola jest osobną aplikacją Python w `src/app_api/`. Nie importuje
logiki domenowej Agents Managera. Ładuje główny
`src/app_api/manifests/asystem.app.json`, pobiera wszystkie pliki
`*.module.json` i buduje scalony katalog sekcji wyłącznie w pamięci.

`main.py` jest cienkim composition rootem. `app/application.py` wybiera runtime,
tryb i renderer, natomiast `app/services/` zawiera osobne adaptery manifestów,
control plane, IPC runtime i prezentacji.

```bash
asystem
asystem agents
asystem agents install --help
asystem agents install -n huggin
```

Ostatnia komenda przechodzi przez wewnętrzną komendę `console-dispatch` w
`agents-system`. Dopóki migracja Agents Managera nie zostanie wykonana, zwraca
`Not implemented yet.`.

Tryby prezentacji:

```bash
asystem --human             # domyślny widok terminalowy
asystem --human-raw agents  # czysty tekst
asystem --agent agents      # zwarty JSON dla agenta
asystem --json              # pełny scalony manifest
asystem --interactive       # interaktywna konsola terminalowa
```

`app_api` udostępnia `create_service()` i jest rejestrowany jako wbudowany
moduł przy starcie wspólnego runtime. Gdy runtime nie działa albo moduł nie jest
jeszcze dostępny, CLI może bezpiecznie wykonać lokalny adapter, ponieważ przed
fallbackiem nie zaszła operacja domenowa.
