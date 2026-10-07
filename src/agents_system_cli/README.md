# Agents System CLI

Instalowalny moduł Pythona udostępniający konsolę i API `agents_system_cli` wraz z
zależnością od lokalnej biblioteki `unix-socket-client`.

## Instalacja z repozytorium

Lokalne projekty należy przekazać do jednego wywołania `pip`. Dzięki temu
resolver użyje lokalnego źródła biblioteki i nie będzie szukał jej w indeksie:

```bash
python -m pip install \
  ./agents-system/src/lib/json_loader \
  ./agents-system/src/lib/manifests_loader \
  ./agents-system/src/lib/modules_catalog \
  ./agents-system/src/manifests \
  ./agents-system/src/lib/unix_socket \
  ./agents-system/src/agents_system_cli
```

W trybie developerskim:

```bash
python -m pip install --editable ./agents-system/src/lib/json_loader --editable ./agents-system/src/lib/manifests_loader --editable ./agents-system/src/lib/modules_catalog --editable ./agents-system/src/manifests --editable ./agents-system/src/lib/unix_socket
python -m pip install --editable ./agents-system/src/agents_system_cli
```

## Import

```python
from agents_system_cli import AgentsSystemCLI
from agents_system_cli.__main__ import execute
from shared import get_config
from lib.unix_socket.socket_client_builder import SocketClientBuilder

application = AgentsSystemCLI(get_config())
result = execute(["--agent"], application=application)
```

`AgentsSystemCLI` przyjmuje wyłącznie zainicjalizowany obiekt `Configuration`.
Entrypoint `python -m agents_system_cli` deleguje start do `app/console.py`. Konsola tworzy
`Configuration` z aktywnego `app_env.json` przed wyborem runtime lub wykonania
lokalnego. `RuntimeDispatcher` korzysta z tej samej konfiguracji i klienta
`shared.socket_client.RuntimeSocketGateway`. Adapter aplikacyjny definiuje
konfigurację i protokół runtime, a klienta tworzy przez
`SocketClientBuilder.configure(codec=RuntimeMessageCodec).create(configuration).get()`.

`AgentsSystemCLI` udostępnia `run()`, `run_dict()` i status `runtime_available`.
Menu i komendy pochodzą z aktywnego manifestu modułów. Ogólna pomoc
(`asystem`, `asystem --help`) jest renderowana lokalnie. Wywołania przez socket
przechodzą przez moduł `agents_system`:

- komenda z flagami: `execute(module_name, method_name, flags)`;
- sama sekcja, komenda bez flag lub `--help`: `help(module_name, method_name, flags)`.

Dla samej sekcji `method_name` jest nazwą sekcji; dla komendy jest to
`method` z manifestu lub jej `name`. `flags` jest słownikiem `{nazwa_flagi: wartość}` bez metadanych.
Flagi bez wartości mają wartości boolowskie, np.
`{"installed": true, "running": false}`. Parser zachowuje typy i wartości
domyślne z manifestu.
Brak flag komendy kieruje do `help`, także gdy manifest definiuje flagi
wymagane lub domyślne. Flagi trybu wyjścia, np. `--json`, nie uruchamiają `execute`.

Runtime otrzymuje te argumenty w polu `kwargs` koperty socketu,
a metoda docelowa przyjmuje je przez `**kwargs`. Przy braku runtime lokalny
loader ładuje wybrany moduł z manifestu i wywołuje jego
`execute(method_name, flags)` albo `help(method_name, flags)`, bez argumentu
`module_name`, przez `**kwargs`. W obu trybach `flags` ma taki sam format
słownika; przez socket jest serializowany do JSON.
Błąd po wysłaniu żądania nie powoduje ponownego wykonania lokalnego.
Moduł `agents_system` musi udostępniać metody `execute` oraz `help`.
