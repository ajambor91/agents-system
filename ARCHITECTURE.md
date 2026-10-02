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
4. konsolę i API interfejsu `app_api`;
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
    ├── agents-system/
    │   ├── main.py
    │   └── app/
    │       ├── application.py
    │       ├── command.py
    │       ├── commands/
    │       ├── services/
    │       └── specs/
    ├── runtime/
    │   ├── main.py
    │   └── service.py
    ├── app_api/
    │   ├── main.py
    │   ├── app/
    │   │   ├── application.py
    │   │   ├── models.py
    │   │   └── services/
    │   │       ├── control_plane.py
    │   │       ├── manifests.py
    │   │       ├── renderer.py
    │   │       └── runtime.py
    │   └── manifests/
    │       ├── asystem.app.json
    │       └── agents.module.json
    ├── agents-manager/
    │   ├── main.py
    │   └── README.md
    ├── agents-data/
    │   ├── main.py
    │   ├── app/
    │   └── README.md
    ├── agents-data-runtime/
    │   ├── main.py
    │   ├── service.py
    │   └── README.md
    └── agents-data-backend/
        ├── main.py
        └── README.md
```

Kanoniczne entrypointy to dokładnie:

| Aplikacja | Entrypoint |
| --- | --- |
| Agents System | `src/agents-system/__main__.py` |
| Shared Runtime | `src/_runtime/main.py` |
| Console API | `src/app_api/__main__.py` |
| Agents Manager Desktop | `src/agents-manager/main.py` |
| Agent Data | `src/agents-data/main.py` |
| Agents Data Runtime | `src/agents-data-runtime/main.py` |
| Agent Data Backend | `src/agents-data-backend/main.py` |

Katalog z myślnikiem nie jest nazwą importowalnego pakietu Python. Kod
wewnętrzny może leżeć w poprawnie nazwanym podpakiecie, np. `app/`, ale wrapper,
manifest i narzędzia wskazują zawsze powyższą, sztywną ścieżkę `main.py`.
Nie tworzymy równoległego `src/agents_system/`.

## 3. Odpowiedzialności aplikacji

### `src/agents-system/`

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
osobnego `src/agents-data-runtime/`.

### `src/agents-data-runtime/`

Osobny proces rezydentny transportu Agents Data. Odpowiada za:

- Unix socket dla aplikacji odbiorców;
- połączenie z Redis Streams;
- rejestrację odbiorców i ich tematów;
- dostarczenie wiadomości oraz ACK po zapisie po stronie odbiorcy;
- utrzymanie tylko jednego aktywnego brokera dla danego socketu.

Kod brokera jest w `service.py`, a `main.py` pozostaje cienkim composition
rootem zgodnym z układem `src/runtime/`.

### `src/app_api/`

Jedyny publiczny interfejs hierarchicznej konsoli `asystem`. Odpowiada za:

- odczyt i walidację głównego manifestu `asystem.app.json`;
- odkrywanie osobnych manifestów sekcji `*.module.json`;
- scalenie menu wyłącznie w pamięci procesu;
- widoki `human`, `human-raw`, `agent`, `json` i `interactive`;
- walidację ścieżki sekcja → komenda → flagi;
- przekazanie typowanej koperty do `agents-system/console-dispatch`.

`app_api` nie instaluje agentów ani nie zapisuje ich stanu. Udostępnia
`create_service()` i jest wbudowanym modułem wspólnego runtime. Lokalny fallback
jest dozwolony jedynie wtedy, gdy runtime nie działa albo nie zna jeszcze
modułu, czyli zanim wykonano operację domenową.

`src/app_api/__main__.py` jest wyłącznie composition rootem: buduje `Application`,
przekazuje argumenty i emituje gotowy `ApiResult`. Decyzja o użyciu runtime,
wyborze renderera, trybie interaktywnym i fallbacku należy do
`app/application.py`. Odczyt manifestów, IPC runtime, wywołanie control plane i
renderowanie są osobnymi serwisami pod `app/services/`.

### `src/agents-manager/`

Wyłącznie aplikacja Pythona działająca na desktopie. Odpowiada za interakcję
operatora z agentami: instalację, aktualizację, listę, status, narzędzia i
diagnostykę. Nie staje się drugim daemonem i nie przejmuje wspólnego runtime.

Operacje uprzywilejowane wykonuje przez wąski interfejs control plane lub
zweryfikowany executor. Integracja OpenClaw, ACL, sudoers i definicje agentów
zostaną przeniesione według `AGENT_MANAGER_MERGE.md`.

### `src/agents-data/`

Lokalna aplikacja Pythona dla agentów i użytkowników. Odpowiada za:

- wysyłanie i odbieranie wiadomości;
- lokalną historię i inbox;
- klienta nasłuchującego `agents-data-runtime`;
- jawne potwierdzenia dostarczenia;
- lokalny sync plików i bazy przez przyszłe API synchronizacji.

Nie posiada MongoDB, Redis ani publicznego backendu HTTP.

### `src/agents-data-backend/`

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
operator/agent -> app_api ------┐
agents-manager (desktop) -------+
                                v
                         agents-system (control plane)
                                |
                                v
                           shared runtime

agents-data (local receiver) <-> agents-data-runtime
        |                              |
        v                              v
agents-data-backend ------------> Redis Streams
        |                         Redis Cache
        +-----------------------> MongoDB
```

Reguły:

- `app_api` nie wykonuje logiki domenowej i nie importuje prywatnych serwisów
  control plane;
- `agents-manager` nie importuje prywatnych serwisów runtime;
- `agents-data` nie czyta MongoDB ani Redis bezpośrednio;
- backend nie zapisuje plików w katalogach domowych agentów;
- runtime nie staje się właścicielem danych domenowych;
- aplikacje wymieniają typowane obiekty JSON, nigdy polecenia shellowe;
- integracja z repozytorium zewnętrznym jest adapterem przejściowym, nie stałym
  importem przez absolutną ścieżkę.

## 5. Przepływ wiadomości

Docelowy przepływ:

```text
agents-data/message_send
  -> HTTP agents-data-backend
  -> walidacja
  -> zapis MongoDB
  -> zapis/odświeżenie Redis Cache
  -> publikacja do stream:<receiver>
  -> agents-data-runtime konsumuje zdarzenie
  -> pobiera pełny dokument przez backend API
  -> dostarcza do zarejestrowanego receivera agents-data
  -> receiver zapisuje lokalny JSONL/inbox
  -> receiver odsyła ACK
  -> agents-data-runtime wykonuje XACK
```

Zdarzenie w streamie zawiera identyfikator wiadomości, a nie pełny mutable
dokument. Publikacja nie może nastąpić przed trwałym zapisem. Brak ACK oznacza
ponowienie, a nie utratę wiadomości.

## 6. Przepływ komendy

Każda publiczna komenda zachowuje wspólny kontrakt:

```text
/usr/local/bin/asystem
  -> host_scripts/asystem.sh
  -> src/app_api/__main__.py
  -> manifest aplikacji + manifest sekcji
  -> agents-system/console-dispatch
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
- `src/agents-system/app/specs/*.json` — kontrakty komend control plane;
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
`src/_runtime/main.py` jako `USER_SYSTEM`. Nie uruchamia osobnych usług dla
`app_api`, `agents-system` ani `agents-manager`.

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
- wspólny runtime obsługuje aplikacje systemowe, a `agents-data-runtime` wyłącznie transport wiadomości;
- desktop Agents Manager nie działa jako daemon;
- Agent Data nie łączy się bezpośrednio z Redis/Mongo;
- backend zapisuje przed publikacją;
- migracje zachowują dane, historie, workspace i kompatybilne wrappery;
- stare repozytoria są read-only lub zarchiwizowane dopiero po testach cutover.
