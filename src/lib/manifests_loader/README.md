# manifests_loader

`ManifestsLoader` wyłącznie odczytuje dokumenty przez `JsonLoader`.
Nie sprawdza schematu, `kind`, typu korzenia ani pól; nie wywołuje modeli
ani walidatora. Zwraca dane dokładnie tak, jak odczytał je czytnik JSON.
Zgłasza jedynie błędy odczytu i dekodowania JSON, zachowując ich przyczynę.

```python
from lib.manifests_loader import ManifestsLoader

document = ManifestsLoader.load_manifest('/path/to/manifest.json')
document = ManifestsLoader.parse_manifest('{"kind": "example"}')
metadata = ManifestsLoader.load_module_metadata('/path/to/module')
documents = ManifestsLoader.load_directory('/path/to/manifests')
```

`ManifestsApp` woła loader i koordynuje walidację oraz rozwiązywanie referencji.
Strategia wybiera model według `kind`; modele walidują własne pola.
Loader można zainstalować i używać bez aplikacji `manifests`.

```bash
python3 -m pip install ./src/lib/json_loader ./src/lib/manifests_loader
```

Pakiet udostępnia przestrzenie nazw `lib.manifests_loader` i `manifests_loader`.
W jednej aplikacji używaj konsekwentnie jednej przestrzeni nazw.
