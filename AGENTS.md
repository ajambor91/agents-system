# Agents System: kontrakt dla agentów

## Cel

`agents-system` jest źródłem zasad współdzielonych przez repozytoria systemu agentów. Agent zmieniający to repozytorium ma utrzymywać kontrakt między ludźmi, Repo Managerem, Repo Manifests i repozytoriami aplikacji.

## Kolejność rozpoznania

Przed implementacją agent musi ustalić:

1. cel repozytorium i jego użytkowników;
2. czy repozytorium jest systemowe;
3. publiczne komendy i ich argumenty;
4. zależności repozytoryjne oraz runtime;
5. operacje uprzywilejowane, sieciowe i destrukcyjne;
6. wymagany lifecycle instalacji, aktualizacji i usuwania;
7. pliki JSON, które są źródłem, a które są generowanym artefaktem.

Nie wolno wymyślać logiki biznesowej na podstawie samej nazwy projektu.

## Odpowiedzialności

- `agents-system` definiuje zasady i wspólne szablony.
- `repo-template` pokazuje minimalne drzewo nowego repozytorium.
- `repo-manager` wykonuje lifecycle i publikuje wrappery.
- `repo-manifests` zapisuje trwałe dane oraz generuje katalog narzędzi agentów.
- `agents-manager` zarządza procesami i konfiguracją agentów.

Nie przenoś logiki Git do `repo-manifests`. Nie zapisuj rejestru ani historii bezpośrednio z aplikacji repozytorium, jeżeli dostępne jest API `manifests_*`.

## Kontrakt drzewa repozytorium

Obowiązujące nazwy to:

- `src/` — kod aplikacji;
- `host_scripts/` — cienkie, publiczne wrappery Bash;
- `internal_scripts/` — skrypty wyłącznie wewnętrzne;
- `self/` — hooki lifecycle;
- `README.md` — dokumentacja człowieka;
- `AGENTS.md` — instrukcje agenta;
- `manifest.json` — opis repozytorium i komend;
- `required_repo` — zależności repozytoryjne;
- `usage` — human-readable spis komend;
- `.env.example` — przykład konfiguracji hosta;
- `.system` — pusty znacznik repozytorium systemowego;
- `available_tools/` — generowane manifesty narzędzi, jeśli repozytorium udostępnia narzędzia agentom.

Nie twórz katalogu `self-scripts/`. To określenie roli, nie ścieżki.

## Python i wrappery

Dla repozytoriów systemowych kod aplikacji jest w Pythonie. Jeden publiczny wrapper prowadzi do jednego entrypointu, a jedna publiczna komenda ma jedną klasę use-case. Bash nie implementuje walidacji domenowej, zapisu JSON ani operacji Git.

Wrapper powinien:

- używać `set -euo pipefail`;
- wyznaczać absolutną ścieżkę entrypointu względem własnego katalogu;
- przekazywać argumenty bez zmiany ich granic;
- zwracać kod zakończenia aplikacji;
- mieć komentarz opisujący publiczne flagi.

Procesy systemowe przyjmują listę argumentów. Sklejony string shellowy jest niedozwolony poza jawnie kontrolowanym hookiem.

## Manifesty narzędzi

Manifest narzędzia musi być obiektem JSON zgodnym z wersjonowanym schematem i zawierać co najmniej:

- `schema_version`;
- `kind: "tool-manifest"`;
- stabilne `id`;
- `command` i `executable`;
- opis;
- `execution.mode`;
- argumenty, przykłady i oczekiwany wynik, gdy są potrzebne.

Opisuj prawdziwe ryzyko: `requires_sudo`, `requires_confirmation`, `interactive`, `supports_dry_run`, `idempotent` i timeout. `available_tools/registry.json` jest generowanym menu i nie może być ręcznie poprawiany.

Po zmianie publicznej komendy zaktualizuj razem: kod, wrapper, `manifest.json`, `usage`, README, źródłowy manifest narzędzia i testy.

## Lifecycle

`repo_install` wykonuje hook instalacyjny przed wpisem do rejestru. Hooki nie powinny wywoływać ponownie `repo_install` ani publikować `/usr/local/bin`. Brak hooka jest poprawnym przypadkiem.

Po instalacji:

1. repozytorium ma gotową konfigurację hosta;
2. `manifest.json` jest zgodny z implementacją;
3. manifesty narzędzi są zainicjalizowane, jeśli repozytorium je udostępnia;
4. wpis i historia są zapisane przez `repo-manifests`;
5. dopiero potem publikowane są hostowe wrappery.

## JSON: źródło kontra artefakt

Nie mieszaj tych dokumentów:

- `manifest.json` — kontrakt repozytorium;
- `available_tools/title.json`, `config.json`, `struct.json` — lokalne metadane zestawu narzędzi;
- `available_tools/tools/*.json` — manifesty pojedynczych narzędzi;
- `available_tools/registry.json` — wygenerowane menu;
- centralne `data.json` i historia JSONL — trwałość Repo Managera;
- globalny rejestr — skrócona lista zarządzanych repozytoriów.

Wspólne szablony JSON mają docelowo należeć do `agents-system`; do czasu migracji nie zmieniaj schematu `repo-manifests` bez aktualizacji generatora i testów.

Konfiguracja środowiska ma osobny kontrakt:

- `resources/app_env.template.json` jest wersjonowanym źródłem i musi zawierać
  opisy, przykłady oraz placeholdery `${NAME}` zamiast powtarzanych ścieżek;
- `resources/app_env.json` jest lokalnym, ignorowanym przez Git artefaktem;
- `APP_ENV_PATH` wskazuje aktywny dokument trybu systemowego; w trybie `dev`
  aktywny jest lokalny `resources/app_env.json`;
- aplikacje nie eksportują konfiguracji automatycznie do procesu;
  `EnvironmentService.load_into_environment()` pozostaje wyłącznie jawnym API
  i jest nieaktywne w trybie `dev`;
- gdy `INSTALL_MODE=dev` i JSON zawiera `BASH_SOURCE=true`, kolejność to
  środowisko powłoki, jawna flaga CLI, a następnie `app_env.json`; poza tym
  aplikacje ignorują środowisko i stosują kolejność flaga CLI, `app_env.json`;
- eksporty powłoki generuje wyłącznie `EnvironmentService`; `BASH_SOURCE` nie
  jest eksportowane, ponieważ jest specjalną tablicą Basha;
- domyślny `get_var` czyta aktywną konfigurację, a `--local` jawnie wybiera
  artefakt w repozytorium.

## Bezpieczeństwo i testy

Przed zapisem waliduj ścieżkę, nie nadpisuj zwykłych plików bez zgody i zapisuj atomowo. `.env` musi być ignorowany przez Git, a `.env.example` nie może zawierać sekretów. Uprawnienia root, sieć i operacje destrukcyjne wymagają jawnego kontraktu.

Minimalne testy zmiany obejmują parser flag, zachowanie klasy use-case, wrapper, tryb systemowy, konfigurację środowiska, ścieżki oraz zgodność JSON z implementacją. Operacje usuwania testuj wyłącznie w katalogu tymczasowym.

## Stałe aplikacje i runtime

Ścieżki aplikacji są częścią kontraktu repozytorium i nie są wyliczane z
nazwy paczki. Control plane znajduje się zawsze w
`src/agents-system/__main__.py`. Wariant `src/agents_system/` z podkreśleniem jest
niedozwolony.

Wspólny, rezydentny runtime ma osobny entrypoint `src/_runtime/main.py`, a jego
silnik znajduje się w `src/_runtime/app/`. Control plane może nim
zarządzać, ale logika utrzymywania procesu należy do katalogu `runtime`.

Pozostałe stałe katalogi aplikacji to:

- `src/app_api/` — manifest-driven konsola i API interfejsu `asystem`,
- `src/agents-manager/` — wyłącznie desktopowa aplikacja Pythona,
- `src/agents-data/` — lokalny klient danych i wiadomości agenta,
- `src/agents-data-runtime/` — osobny runtime komunikacji i dostarczania wiadomości,
- `src/agents-data-backend/` — backend trwałych danych, cache i streamów.

`app_api` jest zaimplementowanym adapterem interfejsu i nigdy nie wykonuje
logiki domenowej bezpośrednio. Ładuje `asystem.app.json` oraz pliki
`*.module.json`, scala ich widok wyłącznie w pamięci i przekazuje typowaną
kopertę do komendy `console-dispatch` w control plane. Każda sekcja menu ma
osobny manifest JSON. Publiczny wrapper `host_scripts/asystem.sh` prowadzi
wyłącznie do `src/app_api/__main__.py`.

W `app_api` plik `main.py` nie wybiera runtime ani renderera. Te decyzje należą
do `app/application.py`. Adaptery manifestów, renderowania, control plane i IPC
runtime muszą pozostać w `app/services/`; nie dodawaj ponownie płaskich modułów
`application.py`, `manifests.py`, `renderer.py` lub `control_plane.py` obok
`main.py`.

Pozostałe trzy aplikacje są obecnie szkieletami migracji. Nie przenoś do nich
kodu produkcyjnego bez zachowania etapów i testów opisanych w
`AGENT_MANAGER_MERGE.md` i `COMMUNICATION_STACK_MERGE.md`.

Moduły dodaje się do rejestru przez `asystem_app_add`; nie importuj
repozytoriów przez stałe, ręcznie wpisane ścieżki w kodzie Agents System.

Kontrakt załadowanej aplikacji to jedno z poniższych:

- `create_service()` zwraca obiekt wywoływalny przyjmujący jeden obiekt JSON;
- moduł eksportuje `handle(payload)`;
- moduł eksportuje `Application` z metodą `handle(payload)`.

Runtime ładuje moduł leniwie i trzyma handler w pamięci do zmiany entrypointu.
Do payloadu wstawia własne `_runtime` z poświadczeniami `SO_PEERCRED`; wartość
klienta nie może być zaufana. Handler zwraca wartość serializowalną do JSON.
Runtime zachowuje także przechwycone `stdout` i `stderr` dla starszych
adapterów.

Wrapper może działać runtime-first, ale fallback do lokalnego CLI jest
dozwolony wyłącznie przy braku socketu/modułu albo jawnej odpowiedzi
`handled: false` sprzed wykonania. Po wysłaniu żądania błąd transportu nie może
powodować ponownego wykonania operacji mutującej.
