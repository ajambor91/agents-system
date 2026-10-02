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
| agents-system | `src/agents-system/__main__.py` | zaimplementowana |
| runtime | `src/_runtime/main.py` | zaimplementowana |
| agents-data-runtime | `src/agents-data-runtime/main.py` | przeniesiony broker komunikacji |
| app_api | `src/app_api/__main__.py` | zaimplementowana konsola/API |
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

## 10. Moduł Agents System

`src/agents-system/` jest modułem Pythona o układzie zgodnym z `app_api`:
`app/application.py`, `app/console.py`, `app/services/`, `app/models/`
i `app/exceptions/`. Instrukcja instalacji pakietu oraz publiczne API znajdują
się w [src/agents-system/README.md](src/agents-system/README.md).

`Application` przyjmuje wyłącznie `Configuration` i udostępnia `modules()`.
Dotychczasowy parser, rejestr komend, `run()`, `execute()`, katalog `specs`
i wrappery dawnych komend zostały usunięte. Instalacja systemu pozostaje
odrębną aplikacją w `install/`.

## 11. Konsola `asystem`

Publiczna konsola jest osobną aplikacją Python w `src/app_api/`. Ładuje
aktywny manifest modułów wygenerowany z
`resources/agents-system.module.template.json` i buduje menu z `children`
wyłącznie w pamięci. `src/app_api/__main__.py` deleguje start do klasy `Console`.

Komendy są publicznymi metodami aplikacji wskazanych przez manifest i `meta.json`.
Konsola przekazuje do runtime nazwę modułu, metodę i argumenty nazwane według
pól `name` z manifestu. Bez połączenia z socketem ładuje tę samą klasę lokalnie.
Pozostałe aplikacje będą dostosowywane etapami; brak metody zwraca błąd.

```bash
asystem
asystem system modules --help
asystem system modules --installed
asystem system modules --running
asystem --json system modules --installed
```

`system modules` wymaga dokładnie jednej flagi. `--installed` czyta pliki
`*.json` bezpośrednio w `INSTALLED_MODULES_DIR` i łączy ich tablice `modules`,
zachowując metadane rekordów. Brak katalogu daje pustą listę. Błędny JSON lub
sprzeczne wpisy tego samego modułu zatrzymują odczyt; identyczne wpisy są scalane.
Plik `resources/agents-system.json` pokazuje format dokumentu instalacji.

`--running` wywołuje `instance-manager.get_running_modules` przez socket runtime.
Zwraca aktualne publiczne instancje zarządzane przez runtime, w tym jego usługi;
instancje z końcówką `_block` są pomijane. Nie korzysta z list instalacyjnych.
Niedostępny runtime kończy komendę błędem z czerwonym komunikatem w terminalu.
`--human-raw`, `NO_COLOR` i tryby JSON nie zawierają kolorów ANSI.

Tryby prezentacji:

```bash
asystem --human             # domyślny widok terminalowy
asystem --human-raw agents  # czysty tekst
asystem --agent agents      # zwarty JSON dla agenta
asystem --json              # pełny scalony manifest
asystem --interactive       # interaktywna konsola terminalowa
```

`Application` w `app_api` udostępnia `run()` i serializowalne `run_dict()`.
Błąd transportu po wysłaniu komendy nie powoduje jej ponownego wykonania lokalnie.
