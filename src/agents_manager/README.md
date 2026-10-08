# agents_manager

Moduł Pythona zarządzający instalacją, aktualizacją, wykonaniem i stanem agentów.
Publicznym interfejsem jest `agents_system_cli`: przez socket wywołuje Agents
System, a lokalnie ładuje managera przez `get_main_app(configuration)`.
Manager zwraca dane; prezentacja należy do CLI.

Pakiet można zainstalować przez `python3 -m pip install ./src/agents_manager`
z katalogu repozytorium. Nie udostępnia osobnego parsera komend `agent-manager`.
Etapy migracji opisuje [AGENT_MANAGER_MERGE.md](../../AGENT_MANAGER_MERGE.md).

## API aplikacji

`AgentsApplication` ma dwie publiczne metody: `help` i `execute`.
Obie zwracają `dict[str, Any]` serializowalny do JSON.

```python
from agents_manager import AgentsApplication

application = AgentsApplication(configuration, manifests)
module_help = application.help(None, {}, None)
command_help = application.help("install", {}, None)
result = application.execute("list", {"show": True}, None)
```

CLI przekazuje `method_name` i słownik już sparsowanych `flags`. Lokalnie
pomija trzeci argument; runtime może przekazać `module_name=None`.
Argument `module_name` pozostaje w sygnaturze dla zgodności wywołań i jest
ignorowany. Manager nie parsuje flag ani nie formatuje danych na stdout.

`HelpService` zwraca przekazany manifest modułu albo opis jednej komendy.
Pomoc nie tworzy kontekstu operacji i nie odczytuje kont systemowych.
`AgentsService.exec` wybiera metodę przez `getattr`; brak metody zwraca
`{"message": "Method not found"}`, a błędy operacji
`{"message": "opis błędu"}`. Metoda komendy `exec` deleguje do `execute`
serwisu wykonawczego.

| Operacja | Wynik |
| --- | --- |
| `list` | Dokument rejestru z polem `agents`, także gdy jest pusty. |
| `status` | Rekord wybranego agenta wraz ze stanem i zadaniami. |
| `tools` | `agent` oraz polityka `tools`. |
| `install`, `update` | Status operacji, agent, użytkownik, ścieżki i `messages` z diagnostyką. |
| `exec` | Agent, `returncode`, `stdout` i `stderr` procesu, także dla niezerowego kodu. |
| `wakeup` | Agent oraz `stdout` i `stderr`; koperta JSON pochodzi z `flags["envelope"]`. |
| `delete` | Status `not-implemented`; usuwanie pozostaje dotychczasowym placeholderem. |

Flaga `json` pozostaje akceptowana przez manifest dla zgodności wywołań;
wynik managera zawsze jest słownikiem. Tryb prezentacji wybiera CLI.
Operacje gatewaya oznaczone w manifeście jako niezaimplementowane zachowują
swój dotychczasowy status.

## Instalacja z katalogu

Instalacja wymaga `-p` lub `--path` wskazującego katalog definicji agenta:

```bash
asystem agents_manager install -p /path/to/mimir
asystem agents_manager install --path /path/to/mimir --dry-run
```

Katalog może znajdować się poza repozytorium. Instalator czyta z niego
opcjonalny `config.json`, `personality/`, `scripts/` oraz wymagany
`resources/shell.template.json`. Brak ścieżki, nieistniejący katalog lub
zwykły plik powodują błąd przed przygotowaniem plików instalacji.

Nazwa agenta pochodzi z nazwy wskazanego katalogu; `--name` i pole `name`
w `config.json`, jeśli podane, muszą być z nią zgodne. Instalacja nie szuka
agenta oznaczonego `default=true`. Podawaj ścieżkę absolutną, aby lokalne
wywołanie i runtime wskazywały to samo źródło.

Instalator zapisuje źródło jako `definition_path` w konfiguracji stanu.
`update -n NAME` ponownie używa tego katalogu. Starsze instalacje bez tego
pola korzystają z dotychczasowej lokalizacji `agents/NAME` w repozytorium.

Katalog główny stanu przygotowuje instalator systemu. Manager tworzy w nim
katalogi agenta i `shells/` bez `sudo`, z trybem `0777` (odczyt, zapis
i przechodzenie dla wszystkich użytkowników), bez ustawiania bitu SGID.
Tryb jest normalizowany także dla istniejących katalogów i niezależnie od umask. Dedykowany agent spoza grupy aplikacji otrzymuje ACL pozwalające
przejść przez te katalogi i odczytać wskazane pliki konfiguracji oraz powłoki.

## Wstrzykiwanie zależności

Konstruktor `AgentsApplication` buduje `HelpService`, serwisy operacji oraz
`AgentServicesFactory` i przekazuje je przez konstruktory. Aktualizacja
używa tej samej instancji instalatora. Serwisy operacji wywołują bezpośrednio
wstrzyknięte zależności.

Fabryka tworzy zależności związane z konkretnym kontekstem żądania:
runner, rejestr, stan, konfigurację, instalację narzędzi i adapter agenta.
Każde żądanie ma osobny runner i listę komunikatów, więc gateway, tryb verbose
i diagnostyka jednego wywołania nie zmieniają pozostałych. Można wstrzyknąć
własną fabrykę przez `AgentsApplication(..., services_factory=my_factory)`.
Helpery i adaptery zachowują typy potrzebne do wewnętrznych obliczeń;
słownik jest kontraktem publicznych operacji.

## Adapter narzędzia agentów

`open_claw/facade.py` udostępnia `OpenClawFacade`. Kontrakt `AgentToolAbstract`
z `open_claw/abstract.py` obejmuje rejestrację i listowanie agentów, tożsamość,
politykę narzędzi, plugin wykonawczy oraz wywołanie agenta. Szczegóły komend,
JSON i instalacji pluginu znajdują się w `open_claw/backend.py`.

Własny adapter implementujący ten kontrakt można przekazać przez
`AgentsApplication(configuration, manifests, agent_tool=my_adapter)`.
Wszystkie serwisy korzystają z tej samej wstrzykniętej integracji.

OpenClaw jest odnajdywany przez `type -P openclaw` w interaktywnej powłoce
logowania Bash użytkownika gatewaya (`open_claw/shell.py`). Ta sama powłoka
wykonuje komendę, zachowując środowisko Node/NVM i granice argumentów.
Kontekst nie szuka binarki w `PATH` runtime. Użytkownik gatewaya pochodzi
z jawnej flagi, następnie `SUDO_USER`, a domyślnie z konfiguracji `USER_SYSTEM`.
