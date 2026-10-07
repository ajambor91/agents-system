# Architektura Agents System
Status: **docelowy kontrakt architektoniczny i plan konsolidacji**.

Ten dokument powstał z `SYSTEM_REPO_CODING.md` i od teraz jest kanonicznym
opisem kodu aplikacji znajdujących się w repozytorium `agents-system`.
Standard ogólny nadal obowiązuje, ale dla tego repozytorium jawnie przyjmujemy
stałe katalogi aplikacji z myślnikami w nazwach.

Szczegółowe plany najbliższych migracji:

- [AGENT_MANAGER_MERGE.md](AGENT_MANAGER_MERGE.md) — włączenie desktopowej
  aplikacji Agents Manager;
- [COMMUNICATION_STACK_MERGE.md](COMMUNICATION_STACK_MERGE.md) — rozdzielenie
  `communication_stack` na aplikację lokalną, backend danych i wspólny runtime.

## 1. Cel konsolidacji

`agents-system` ma stać się jednym repozytorium kodu dla lokalnego systemu
agentów, bez zlewania wszystkich odpowiedzialności w jeden proces. Repozytorium
zawiera kilka niezależnych aplikacji Pythona, wspólne zasoby i kontrakty, ale
każda aplikacja ma oddzielny entrypoint, cykl życia i granicę danych.

Docelowo repozytorium obejmuje:

1. control plane Agents System;
2. wspólny rezydentny runtime aplikacji systemowych;
3. osobny runtime komunikacji Agents Data;
4. konsolę i API interfejsu `agents_system_cli`;
5. desktopowy Agents Manager;
6. lokalną aplikację Agents Data;
7. backend Agents Data z Redis i MongoDB.

Konsolidacja kodu nie oznacza wspólnego mutable state ani importowania
przypadkowych plików między aplikacjami. Integracje przechodzą przez jawne
interfejsy Pythona, Unix socket albo HTTP.

## 2. Sztywne ścieżki aplikacji

Poniższe ścieżki są stałe i nie są wyprowadzane z nazwy pakietu, konfiguracji
ani nazwy repozytorium:

```text
agents-system/
├── ARCHITECTURE.md
├── AGENT_MANAGER_MERGE.md
├── COMMUNICATION_STACK_MERGE.md
├── host_scripts/
├── resources/
├── internal_scripts/
├── tests/
└── src/
    ├── lib/
    │   ├── json_loader/
    │   ├── manifests_loader/
    │   ├── modules_catalog/
    │   └── unix_socket/
    ├── manifests/
    │   ├── __main__.py
    │   ├── pyproject.toml
    │   └── app/
    │       ├── helpers/manifest_validator.py
    │       └── models/
    ├── agents_system/
    │   ├── __main__.py
    │   └── app/
    ├── _runtime/
    │   ├── __main__.py
    │   └── app/
    ├── agents_system_cli/
    │   ├── __main__.py
    │   ├── app/
    │   │   ├── application.py
    │   │   ├── models/
    │   │   └── services/
    │   │       ├── module_dispatcher.py
    │   │       ├── module_loader.py
    │   │       ├── renderer.py
    │   │       └── runtime.py
    │   └── resources/agents_system_cli.module.json
    ├── agents_manager/
    │   ├── __main__.py
    │   ├── pyproject.toml
    │   └── app/
    ├── agents_data/
    │   ├── __main__.py
    │   └── app/
    ├── agents_data_runtime/
    │   ├── __main__.py
    │   └── service.py
    └── agents_data_backend/
        └── __main__.py
```

Kanoniczne entrypointy to dokładnie:

| Aplikacja | Entrypoint |
| --- | --- |
| Agents System | `src/agents_system/__main__.py` |
| Shared Runtime | `src/_runtime/__main__.py` |
| Console API | `src/agents_system_cli/__main__.py` |
| Agents Manager Desktop | `src/agents_manager/__main__.py` |
| Agent Data | `src/agents_data/__main__.py` |
| Agents Data Runtime | `src/agents_data_runtime/__main__.py` |
| Agent Data Backend | `src/agents_data_backend/__main__.py` |

Nazwy katalogów aplikacji są nazwami importowalnych pakietów Pythona
z podkreśleniami. Wrappery i manifesty wskazują jawne entrypointy podane
w tabeli. `agents_manager` ma `pyproject.toml`, `__init__.py` i
`__main__.py`; konsola `agents_system_cli` eksportuje klasę `AgentsSystemCLI`.

## 3. Odpowiedzialności aplikacji

### `src/agents_system/`

Control plane i publiczne CLI całego repozytorium. Odpowiada za:

- wersjonowane kontrakty komend JSON;
- konfigurację środowiska i `get_var`;
- użytkownika systemowego i instalację hostową;
- rejestr aplikacji ładowanych przez runtime;
- status systemu i orkiestrację usług;
- publikację cienkich wrapperów z `host_scripts/`.

Nie implementuje pętli Redis Streams, UI desktopowego ani dostępu do MongoDB.

### `src/runtime/`

Wspólny proces rezydentny dla aplikacji systemowych. Odpowiada za:

- Unix socket i lifecycle procesu;
- tożsamość klienta z `SO_PEERCRED`;
- leniwe ładowanie i przeładowywanie modułów;
- routing zweryfikowanych żądań;
- przechwytywanie stdout/stderr starszych adapterów.

Nie obsługuje transportu wiadomości agentów. Ta odpowiedzialność należy do
osobnego `src/agents_data_runtime/`.

### `src/agents_data_runtime/`

Osobny proces rezydentny transportu Agents Data. Odpowiada za:

- Unix socket dla aplikacji odbiorców;
- połączenie z Redis Streams;
- rejestrację odbiorców i ich tematów;
- dostarczenie wiadomości oraz ACK po zapisie po stronie odbiorcy;
- utrzymanie tylko jednego aktywnego brokera dla danego socketu.

Kod brokera jest w `service.py`, a `__main__.py` pozostaje cienkim composition
rootem zgodnym z układem `src/runtime/`.

### `src/agents_system_cli/`

Jedyny publiczny interfejs hierarchicznej konsoli `asystem`. Odpowiada za:

- odczyt i walidację głównego manifestu `asystem.app.json`;
- odkrywanie osobnych manifestów sekcji `*.module.json`;
- scalenie menu wyłącznie w pamięci procesu;
- widoki `human`, `human-raw`, `agent`, `json` i `interactive`;
- walidację ścieżki sekcja → komenda → flagi;
- przekazanie typowanej koperty do `agents_system/console-dispatch`.

`agents_system_cli` nie instaluje agentów ani nie zapisuje ich stanu. Udostępnia
`create_service()` i jest wbudowanym modułem wspólnego runtime. Lokalny fallback
jest dozwolony jedynie wtedy, gdy runtime nie działa albo nie zna jeszcze
modułu, czyli zanim wykonano operację domenową.

`src/agents_system_cli/__main__.py` jest wyłącznie composition rootem: buduje `AgentsSystemCLI`,
przekazuje argumenty i emituje gotowy `ApiResult`. Decyzja o użyciu runtime,
wyborze renderera, trybie interaktywnym i fallbacku należy do
`app/application.py`. Odczyt manifestów, IPC runtime, wywołanie control plane i
renderowanie są osobnymi serwisami pod `app/services/`.

### `src/agents_manager/`

Wyłącznie aplikacja Pythona działająca na desktopie. Odpowiada za interakcję
operatora z agentami: instalację, aktualizację, listę, status, narzędzia i
diagnostykę. Nie staje się drugim daemonem i nie przejmuje wspólnego runtime.

Operacje uprzywilejowane wykonuje przez wąski interfejs control plane lub
zweryfikowany executor. Integracja OpenClaw, ACL, sudoers i definicje agentów
zostaną przeniesione według `AGENT_MANAGER_MERGE.md`.

### `src/agents_data/`

Lokalna aplikacja Pythona dla agentów i użytkowników. Odpowiada za:

- wysyłanie i odbieranie wiadomości;
- lokalną historię i inbox;
- klienta nasłuchującego `agents_data_runtime`;
- jawne potwierdzenia dostarczenia;
- lokalny sync plików i bazy przez przyszłe API synchronizacji.

Nie posiada MongoDB, Redis ani publicznego backendu HTTP.

### `src/agents_data_backend/`

Backend trwałych danych i transportu. Odpowiada za:

- walidację i zapis wiadomości;
- MongoDB jako trwałe źródło danych;
- Redis Cache jako odtwarzalny cache;
- Redis Streams jako transport zdarzeń;
- API odczytu danych i endpointy health;
- publikację zdarzenia dopiero po trwałym zapisie.

Redis Cache i Redis Streams pozostają dwiema osobnymi instancjami o różnych
politykach utraty danych. Cache może zostać odbudowany, stream nie może usuwać
nieobsłużonych zdarzeń przez politykę LRU.

## 4. Dozwolone zależności

```text
operator/agent -> agents_system_cli ------┐
agents_manager (desktop) -------+
                                v
                         agents-system (control plane)
                                |
                                v
                           shared runtime

agents_data (local receiver) <-> agents_data_runtime
        |                              |
        v                              v
agents_data_backend ------------> Redis Streams
        |                         Redis Cache
        +-----------------------> MongoDB
```

Reguły:

- `agents_system_cli` nie wykonuje logiki domenowej i nie importuje prywatnych serwisów
  control plane;
- `agents_manager` nie importuje prywatnych serwisów runtime;
- `agents_data` nie czyta MongoDB ani Redis bezpośrednio;
- backend nie zapisuje plików w katalogach domowych agentów;
- runtime nie staje się właścicielem danych domenowych;
- aplikacje wymieniają typowane obiekty JSON, nigdy polecenia shellowe;
- integracja z repozytorium zewnętrznym jest adapterem przejściowym, nie stałym
  importem przez absolutną ścieżkę.

## 5. Przepływ wiadomości

Docelowy przepływ:

```text
agents_data/message_send
  -> HTTP agents_data_backend
  -> walidacja
  -> zapis MongoDB
  -> zapis/odświeżenie Redis Cache
  -> publikacja do stream:<receiver>
  -> agents_data_runtime konsumuje zdarzenie
  -> pobiera pełny dokument przez backend API
  -> dostarcza do zarejestrowanego receivera agents_data
  -> receiver zapisuje lokalny JSONL/inbox
  -> receiver odsyła ACK
  -> agents_data_runtime wykonuje XACK
```

Zdarzenie w streamie zawiera identyfikator wiadomości, a nie pełny mutable
dokument. Publikacja nie może nastąpić przed trwałym zapisem. Brak ACK oznacza
ponowienie, a nie utratę wiadomości.

## 6. Przepływ komendy

Każda publiczna komenda zachowuje wspólny kontrakt:

```text
/usr/local/bin/asystem
  -> host_scripts/asystem.sh
  -> src/agents_system_cli/__main__.py
  -> manifest aplikacji + manifest sekcji
  -> agents_system/console-dispatch
  -> wersjonowany JSON komendy
  -> Command
  -> CommandRequest
  -> Application.execute()
  -> jedna klasa use-case
  -> wąski Service
  -> CommandResult
  -> renderer CLI
```

Wrapper Bash używa `set -euo pipefail`, wyznacza repo względem własnego pliku,
przekazuje `"$@"` bez zmiany granic i nie zawiera walidacji domenowej.

Definicja JSON jest warunkiem wykonania. Nieznana wersja, brak implementacji,
kolizja flag albo niepoprawny target kończą działanie przed skutkiem ubocznym.
`--help` również powstaje z kontraktu JSON.

## 7. Konfiguracja i dane

Wersjonowane źródła:

- `resources/app_env.template.json` — model wspólnego środowiska;
- `src/agents_system/app/specs/*.json` — kontrakty komend control plane;
- `internal_scripts/manifests/*.json` — źródłowe manifesty narzędzi;
- przyszłe schematy komunikacji w katalogach właściwych aplikacji.

Generowane artefakty:

- `resources/app_env.json` — lokalna konfiguracja, ignorowana przez Git;
- `APP_ENV_PATH` — aktywny dokument konfiguracji trybu systemowego; w trybie `dev` używany jest `resources/app_env.json`;
- `APP_DATA_DIR/modules.json` — rejestr modułów runtime;
- `APP_DATA_DIR` — trwały stan aplikacji, a `APP_RUNTIME_DIR` — PID-y i sockety;
- `available_tools/registry.json` — wygenerowany indeks narzędzi.

MongoDB jest źródłem trwałych danych Agent Data. Redis Cache i pliki lokalne są
odtwarzalne. JSONL inbox/historia jest lokalnym widokiem odbiorcy, nie globalną
bazą prawdy.

## 8. Bezpieczeństwo

- Uwierzytelnienie lokalnego klienta opiera się na `SO_PEERCRED`, nie na polu
  UID przesłanym w JSON.
- Proces runtime nadpisuje zastrzeżone `_runtime` własnymi danymi.
- Operacje root mają jawny kontrakt, walidację i test trybu bez skutków.
- Polecenia procesów są listą argumentów; shell string jest zabroniony poza
  kontrolowanym hookiem.
- Plik sudoers przechodzi `visudo -cf` i jest instalowany atomowo jako `0440`.
- Sekrety nie trafiają do manifestów, verbose, historii ani pełnych dumpów
  środowiska.
- Backend nie ufa nazwie nadawcy bez warstwy autoryzacji; tryb `--admin`
  wyprowadza aktora z tożsamości procesu.
- Ścieżki zapisu muszą pozostać pod zatwierdzonym rootem aplikacji.

## 9. Lifecycle i kompatybilność

Każda migracja przebiega w kolejności:

1. zinwentaryzowanie zachowania i testów źródłowego repozytorium;
2. zapisanie kontraktu wejścia, wyjścia i danych;
3. przeniesienie kodu bez zmiany zachowania;
4. testy równoważności na obu implementacjach;
5. przełączenie wrapperów i manifestów na nową ścieżkę;
6. okres zgodności z ostrzeżeniem deprecacyjnym;
7. zatrzymanie starego runtime i wyłączenie zapisu w starym repo;
8. usunięcie duplikacji dopiero po potwierdzonym cutover.

W jednej chwili istnieje tylko jeden aktywny konsument danej grupy Redis
Streams i tylko jeden właściciel mutacji danego rejestru.

### Usługa systemowa runtime

Wersjonowany `resources/agents_manager.template.service` jest źródłem jednostki
systemd. Po wyrenderowaniu placeholderów jednostka uruchamia wyłącznie
`src/_runtime/__main__.py` jako `USER_SYSTEM`. Nie uruchamia osobnych usług dla
`agents_system_cli`, `agents-system` ani `agents_manager`.

Systemd pilnuje dostępności procesu wspólnego runtime. Runtime będzie docelowo
czytał manifest aplikacji wskazany przez `AGENTS_SYSTEM_APPS_PATH` i odpowiadał
za uruchamianie oraz stan pozostałych aplikacji. Renderowanie, instalacja i
odczyt tego JSON-a pozostają osobnym etapem implementacji.

## 10. Testy i definicja ukończenia

Minimalna walidacja każdej zmiany:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
git diff --check
repo_audit --target /home/user-system/repositories/agents-system
```

Zmiana publicznej komendy aktualizuje razem: kontrakt JSON, use-case, serwis,
wrapper, `manifest.json`, `usage`, README, manifest narzędzia i testy.

Konsolidacja jest ukończona dopiero, gdy:

- wszystkie entrypointy używają siedmiu stałych ścieżek;
- nie istnieje `src/agents_system/`;
- wspólny runtime obsługuje aplikacje systemowe, a `agents_data_runtime` wyłącznie transport wiadomości;
- desktop Agents Manager nie działa jako daemon;
- Agent Data nie łączy się bezpośrednio z Redis/Mongo;
- backend zapisuje przed publikacją;
- migracje zachowują dane, historie, workspace i kompatybilne wrappery;
- stare repozytoria są read-only lub zarchiwizowane dopiero po testach cutover.

`ManifestsApp` woła `lib.manifests_loader.ManifestsLoader`, który odczytuje
dokumenty przez `lib.json_loader.JsonLoader`. Loader zwraca dane bez
walidacji. Aplikacja koordynuje rozwiązywanie referencji i walidację modeli
wybranych przez `ManifestValidator` według `kind`. `ManifestCatalog` w
`manifests.app` buduje menu w pamięci; adapter control plane sprawdza rekordy
instalacji po odczycie przez aplikację manifestów.
