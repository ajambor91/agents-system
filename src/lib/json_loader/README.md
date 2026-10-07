# json_loader

Wspólny odczyt JSON bez walidacji domenowej. Pliki są czytane jako UTF-8.
`load()` i `loads()` przyjmują dowolny korzeń JSON, również `null`.
`getJsonFileContent()` zachowuje dotychczasowe API i odrzuca `null`.

```python
from lib.json_loader import JsonLoader

document = JsonLoader.load('/path/to/document.json')
document = JsonLoader.loads('{"name": "example"}')
```

Instalacja: `python3 -m pip install ./src/lib/json_loader`.
Pakiet udostępnia też przestrzeń nazw `json_loader`.
