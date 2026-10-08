# Manifests

Instalowalny pakiet Pythona 3.11+ zawierający aplikację, modele i walidator
manifestów Agents System. Publiczne API:

```python
from manifests import ManifestsApp, ManifestValidator
from lib.manifests_loader import ManifestsLoader
```

Publiczny pakiet eksportuje `ManifestsApp` i `ManifestValidator`.
`ManifestsApp` woła `ManifestsLoader` do odczytu dokumentów. Loader używa
`JsonLoader` i zwraca dane bez walidacji. Metoda `validate_manifest()` wybiera
model przez strategię; `load_modules_manifest()` koordynuje odczyt,
walidację modeli oraz scalenie referencji wyłącznie w pamięci.

## Instalacja i entrypoint

```bash
python3 -m pip install ./src/lib/json_loader ./src/lib/manifests_loader \
  ./src/lib/modules_catalog ./src/lib/unix_socket ./src/agents_system_cli ./src/manifests
PYTHONPATH=src python3 -m manifests src/agents_system/resources/agents_system.module.json
PYTHONPATH=src python3 -m manifests --help
```

Po instalacji dostępna jest też komenda `manifest-validate PATH`.
`__main__.py` odczytuje dokument przez loader i uruchamia model wybrany przez
strategię na podstawie `kind`. Sukces zwraca JSON i kod 0; błąd kod 1.

## Walidacja przez modele

`ManifestValidator.validate(data)` wybiera strategię według `kind` w
`app/helpers/manifests_validator/`. Strategia wyłącznie konstruuje odpowiedni
model przez `from_dict()`. Walidator wywołuje `model.validate()`; model
sprawdza własne pola i modele zagnieżdżone, gromadzi błędy w `errors` oraz
zgłasza jeden `ManifestValidationError`. Parsowanie nie uruchamia walidacji.

| kind | Model |
| --- | --- |
| `agents-system-modules-manifest` | `ModulesManifestModuleManifest` |
| `module-manifest` | `ModuleManifest` |
| `agents-system-environment` | `EnvironmentManifest` |

`EnvironmentManifest` waliduje zagnieżdżone `EnvironmentVariableManifest`,
wymagane zmienne, powiązania ścieżek i wartości konfiguracji. `ModuleManifest`
waliduje opis, użycie oraz zagnieżdżone komendy i flagi. Element listy modułów
z `manifest_path` odczytuje swój manifest podczas własnej walidacji i sprawdza
zgodność tożsamości. Modele można walidować bez użycia strategii.

`app/helpers/manifest_validator.py` zawiera właściwy walidator: wybór
strategii według `kind`, utworzenie modelu i wywołanie jego `validate()`. `ManifestsApp.validate_manifest(data)` deleguje do
niego, a `ManifestsLoader.load_manifest(path)` odczytuje dane JSON.

## Sprawdzenie

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 -m unittest discover -s src/manifests/tests -v
```

Testy sprawdzają składnię, budowanie wheel i import publicznego API. Testy sprawdzają także wybór modelu, jego samodzielną walidację i agregację błędów. Test
pakowania wymaga lokalnie `pip`, `setuptools>=68` i `wheel`, działa bez sieci
oraz buduje kopię źródeł w katalogu tymczasowym.
