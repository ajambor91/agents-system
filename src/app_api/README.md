# Agents System App API

Instalowalny moduł Pythona udostępniający konsolę i API `app_api` wraz z
zależnością od lokalnej biblioteki `unix-socket-client`.

## Instalacja z repozytorium

Oba lokalne projekty należy przekazać do jednego wywołania `pip`. Dzięki temu
resolver użyje lokalnego źródła biblioteki i nie będzie szukał jej w indeksie:

```bash
python -m pip install \
  ./agents-system/src/lib/unix_socket \
  ./agents-system/src/app_api
```

W trybie developerskim:

```bash
python -m pip install --editable ./agents-system/src/lib/unix_socket
python -m pip install --editable ./agents-system/src/app_api
```

## Import

```python
from app_api import Application
from app_api.__main__ import execute
from shared import get_config
from lib.unix_socket.socket_client_builder import SocketClientBuilder

application = Application(get_config())
result = execute(["--agent"], application=application)
```

`Application` przyjmuje wyłącznie zainicjalizowany obiekt `Configuration`.
Entrypoint `python -m app_api` deleguje start do `app/console.py`. Konsola tworzy
`Configuration` z aktywnego `app_env.json` przed wyborem runtime lub wykonania
lokalnego. `RuntimeDispatcher` korzysta z tej samej konfiguracji i klienta
`shared.socket_client.RuntimeSocketGateway`. Adapter aplikacyjny definiuje
konfigurację i protokół runtime, a klienta tworzy przez
`SocketClientBuilder.configure(codec=RuntimeMessageCodec).create(configuration).get()`.

`Application` udostępnia `run()`, `run_dict()` i status `runtime_available`.
Menu i komendy pochodzą z `children` aktywnego manifestu modułów. Każda
komenda wywołuje publiczną metodę aplikacji modułu: `method` z manifestu,
a gdy pole nie występuje — `name` z zamianą myślników na podkreślenia.
Np. `gateway-start` wywołuje `gateway_start()`.

`ModuleDispatcher` wysyła do runtime `service=module_name`, `method`
i `kwargs` z argumentami sparsowanymi według manifestu. Nie wysyła całego
CLI do `app_api.run_dict` ani do `console-dispatch`. Brak połączenia przed
wysłaniem komendy oznacza lokalny fallback: `ModuleLoader` ładuje klasę
wskazaną przez `meta.json` z `absolute_module_path`, tworzy ją z tą samą
`Configuration` i wywołuje tę samą metodę z tymi samymi argumentami.
Ścieżki `${NAME}` są rozwiązywane z konfiguracji, bez stałej listy modułów.

Parametry flag są przekazywane pod ich `name`; typy `integer`, `number`
i `boolean` są konwertowane. Argumenty pozycyjne pochodzą z `positionals`.
Metody mogą zwracać dowolne dane JSON. Błąd po wysłaniu żądania runtime
nie powoduje ponownego wykonania lokalnego.

Pozostałe aplikacje będą dostosowywane osobno. Brak wymaganej metody lub
niezgodny konstruktor daje jawny błąd modułu; konsola nie tłumaczy wywołania
na dawne CLI i nie symuluje powodzenia.

Parsowanie flag oraz sesja
interaktywna należą do klas w `app/services/`. Modele znajdują się w
`app/models/`, a wyjątki w `app/exceptions/`, po jednej klasie w pliku.

Dystrybucja zawiera pakiety `app_api` oraz `lib.configuration`.
Biblioteka `unix_socket` pozostaje osobną dystrybucją i jest deklarowana jako
zależność `unix-socket-client==0.1.0`.


Menu pokazuje status wykonania: czerwone `Application runtime does not working`
i poniżej `Running in local mode` przy fallbacku; zielone
`Application runtime and socket are OK` po odpowiedzi runtime. Kolory obowiązują
w terminalu w trybie human; `--human-raw` i `NO_COLOR` wyłączają kolory.
Tryby `--json` i `--agent` zachowują dotychczasowy format.

Nazwy parametrów metody pochodzą wyłącznie z `name` w definicjach flag lub
argumentów pozycyjnych. `short`, `long` oraz `aliases` określają tylko zapis CLI.
Np. `{"name": "name", "long": "--display-title", "takes_value": true}`
przekazuje `name="..."`, a nie `display_title="..."`. Ten sam słownik argumentów
trafia lokalnie do `method(**arguments)` oraz przez socket do `kwargs`.

Po wybraniu sekcji i komendy deklarowane flagi modułu mają pierwszeństwo przed
opcjami konsoli. Globalny tryb wyjścia można podać przed sekcją, np.
`asystem --json plugin command --json`, gdzie ostatnie `--json` jest flagą
pluginu, jeśli definiuje ją manifest. Wartości flag pozostają danymi nawet,
jeśli wyglądają jak opcje konsoli. Separator `--` rozpoczyna argumenty pozycyjne.
Nie ma stałej listy nazw parametrów poszczególnych aplikacji czy pluginów.
