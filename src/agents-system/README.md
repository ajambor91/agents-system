# Agents System module

Moduł Pythona z publicznym API `Application(configuration).modules()`.
Katalog źródłowy pozostaje `src/agents-system`; zainstalowany pakiet ma nazwę
importu `agents_system`. Nie powstaje katalog `src/agents_system`.

```bash
python3 -m pip install ./src/lib/unix_socket ./src/app_api ./src/agents-system
python3 -m agents_system modules --installed
python3 -m agents_system --json modules --running
```

Entrypoint modułu to `src/agents-system/__main__.py`, który przekazuje
wykonanie do `app/console.py`. W repozytorium można uruchomić go przez
`PYTHONPATH=src python3 -m agents-system`.
`Console` inicjalizuje `Configuration` przed utworzeniem `Application`.

```python
from agents_system import Application
from shared import get_config

application = Application(get_config())
result = application.modules(installed=True)
```

`Application` przyjmuje tylko `Configuration` i udostępnia wyłącznie metodę
`modules(installed=False, running=False)`. Wymagana jest dokładnie jedna opcja.
`--installed` czyta tablice `modules` z plików JSON w `INSTALLED_MODULES_DIR`.
`--running` wywołuje `instance-manager.get_running_modules` przez Unix socket.
Niedostępny runtime kończy komendę błędem z czerwonym komunikatem w terminalu.

Struktura aplikacji:

- `app/application.py` — publiczne API;
- `app/console.py` — start, obsługa błędów i emisja wyniku;
- `app/services/` — adapter CLI, przypadek użycia modules, JSON i runtime;
- `app/models/` — jeden model w pliku;
- `app/exceptions/` — jeden wyjątek w pliku.

CLI wykorzystuje parser i renderer `app_api`. Definicja komendy pochodzi
wyłącznie z sekcji systemowej aktywnego manifestu, renderowanego z
`resources/agents-system.module.template.json`. Nie ma osobnego rejestru klas
komend ani katalogu `specs`. Metody rozwiązywane są dynamicznie według manifestu,
a argumenty trafiają do nich pod nazwami z pól `name`.

Dotychczasowe komendy użytkowników, konfiguracji, zarządzania aplikacjami,
instalacji i sterowania runtime oraz ich wrappery zostały usunięte.
Instalator systemu jest osobną aplikacją opisaną w `install/README.md`.
