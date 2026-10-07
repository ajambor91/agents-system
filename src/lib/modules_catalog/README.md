# Modules Catalog

Biblioteka Pythona tworzy katalog modułów i komend ze słownika, dokumentu JSON
lub pliku JSON. Nie uruchamia komend, nie importuje aplikacji i nie zapisuje
manifestów. Wymaga Pythona 3.11+; nie ma zewnętrznych zależności runtime.

## Instalacja

Z katalogu głównego repozytorium:

```bash
python3 -m pip install ./src/lib/modules_catalog
```

Publiczne API zawiera dokładnie:

```python
__all__ = ["Flag", "Module", "Command", "ModulesCatalog", "ExclusiveGroup", "CommandInput", "ModulesFactory"]
```

Biblioteka obsługuje importy `lib.modules_catalog` oraz `modules_catalog`.
W jednej aplikacji używaj konsekwentnie jednej przestrzeni nazw. Modele są
klasami danych z `slots`; fabryka udostępnia metody statyczne i nie jest
przeznaczona do tworzenia instancji.

## Użycie

```python
from lib.modules_catalog import ModulesFactory

catalog = ModulesFactory.create_modules_from_dict({
    "schema_version": 1,
    "version": "0.1.0",
    "kind": "modules-catalog",
    "app_name": "example",
    "absolute_path": "/opt/example",
    "menu_name": "Example",
    "description": "Example command catalog",
    "sections": {
        "system": {
            "absolute_path": "/opt/example",
            "module_name": "system",
            "absolute_module_path": "/opt/example/system",
            "menu_name": "System",
            "description": "System commands",
            "commands": [{
                "name": "status",
                "method": "status",
                "description": "Show status",
                "usage": "status",
                "implementation_status": "implemented",
            }],
        },
    },
})

command = catalog.commands["system.status"]
assert command.module is catalog.modules[0]
```

Pozostałe wejścia:

```python
catalog = ModulesFactory.create_modules_from_json(json_text_or_bytes)
catalog = ModulesFactory.create_modules_from_json_file("modules.json")
```

Pliki są odczytywane jako UTF-8. `section_name` domyślnie pochodzi z klucza
w `sections`. Indeks komend używa kluczy `section_name.command_name`.
Komendy zachowują referencję do swojego modułu. Powtórzony klucz komendy
zgłasza `ValueError`.

`flags`, `exclusive_groups` i `commands` są opcjonalnymi listami.
`method` może być pominięte; wtedy ma wartość `None`. `input`, jeśli podane,
zawiera `source`, `type` i `maximum_bytes`. Każda grupa wykluczająca zawiera
`members`, `minimum` i `maximum`.

Flaga wymaga `name`, `description`, `usage`, `takes_value`, `type` i `required`;
`short`, `long`, `aliases` i `default` są opcjonalne.
Fabryka odtwarza dane i powiązania, bez pełnej walidacji schematu czy zgodności
argumentów komendy. Brak wymaganych pól zgłasza `KeyError`, niepoprawny JSON
`json.JSONDecodeError`, a błędy odczytu pliku odpowiednie wyjątki systemowe.

## Testy

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:src/lib \
  python3 -m unittest discover -s src/lib/modules_catalog/tests -v
```

Testy obejmują publiczne eksporty, wejścia JSON/słownik/plik, powiązania modeli,
wartości domyślne, duplikaty, błędy oraz niezależność tworzonych katalogów.
Test pakowania buduje wheel w katalogu tymczasowym bez sieci i sprawdza oba
importy poza repozytorium. Wymaga dostępnych lokalnie `pip`, `setuptools>=68`
i `wheel`; same testy korzystają z `unittest`.

## External module help

For a `children` catalog, each entry may provide an absolute `manifest_path`
instead of inline help. Its `module-manifest` document defines the matching
`module_name`, `schema_version: 1`, positive integer `version`, `menu_name`,
`description`, `usage` and `commands`. All public factory methods resolve these
references through the same loader and merge a private copy in memory. Missing
files, invalid paths, conflicting inline help and duplicate identities fail
loading. `Module.usage` exposes the module-level help usage.

`ModulesFactory` korzysta z `ManifestsApp`: aplikacja woła bierny loader,
waliduje dokument przez model wybrany według `kind` i rozwiązuje referencje.
Fabryka katalogu tworzy następnie typowane modele komend.
