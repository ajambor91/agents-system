# compose_loader

Biblioteka odczytu Compose. Publiczny interfejs to klasa `ComposeLoader`
z jedną statyczną metodą `loadYaml(path: Path | str) -> ComposeData`.
Wszystkie modele są eksportowane bezpośrednio z `compose_loader` (w repozytorium:
`lib.compose_loader`) oraz z podpakietu `models`. Wymaga Pythona 3.11+ i PyYAML 6.

```python
from pathlib import Path
from lib.compose_loader import ComposeLoader, ComposeData, Service, Port

compose: ComposeData = ComposeLoader.loadYaml(Path("docker-compose.yml"))
service: Service = compose.services["app-data"]
context = service.build.context if service.build else None
port: Port = service.ports[0]
print(context, port.published, port.target)
print(service.environment["REDIS_CACHE_URL"].value)
```

`Services`, `Networks`, `ServiceNetworks`, `VolumeDefinitions`, `Environment`,
`DependsOn` i `Resources` są słownikami typowanych modeli.
`Ports`, `Volumes` i `ResourceReferences` są listami typowanych modeli.
Definicje wolumenów na poziomie dokumentu (`VolumeDefinition`) są odrębne od
montowań w usłudze (`Volume`). `Build.context` jest niezmienionym stringiem YAML.

Obsługiwane są krótkie i rozszerzone formy `build`, `ports`, `volumes`,
`environment`, `depends_on`, `networks`, `secrets` i `configs`.
Porty liczbowe w krótkiej składni stają się `int`; zakresy i placeholdery
pozostają stringami. Obsługiwane są adresy IPv6 w nawiasach kwadratowych.
Krótkie ścieżki wolumenów używają składni POSIX `source:target[:mode]`.
Opcje bez dedykowanego pola oraz rozszerzenia `x-*` pozostają w `extra`
odpowiedniego modelu; nie są odrzucane.

Każdy model i każda kolekcja udostępnia `to_mapping()`. Modele i słowniki
zwracają nowy `dict`, a kolekcje listowe (np. `Ports`) nową listę słowników.
Konwersja jest rekurencyjna, spłaszcza `extra` i pomija pola o wartości `None`.
Zachowuje wartości `False`, `0` i puste kolekcje. `Environment.to_mapping()`
zwraca mapę nazw na wartości, zachowując również nierozwiązane wartości `None`.
Modyfikacja wyniku nie modyfikuje modelu.

```python
mapping = compose.to_mapping()
ports = service.ports.to_mapping()
environment = service.environment.to_mapping()
```

To reprezentacja modeli, nie pełny serializer Compose ani uniwersalne argumenty
Docker SDK. Przykładowo `Service.name` i `Volume.mode` pozostają w wyniku.

Dla tworzenia nazwanych wolumenów `VolumeDefinition.to_docker_kwargs(key)`
zwraca wyłącznie `name`, `driver`, `driver_opts` i `labels`, zgodne z
[`client.volumes.create`](https://docker-py.readthedocs.io/en/stable/volumes.html).
Używa jawnego `name` albo klucza Compose; nie dodaje prefiksu projektu.
Etykiety w składni listowej zamienia na słownik. Wolumeny `external` odrzuca
przez `ValueError`, ponieważ należy pobrać istniejący wolumen:

```python
for key, volume in compose.volumes.items():
    if volume.external:
        client.volumes.get(volume.name or key)
    else:
        client.volumes.create(**volume.to_docker_kwargs(key))
```

Iterowanie po `compose.volumes` zwraca klucze. `.items()` zwraca pary
klucz–model, a `.values()` same modele. Biblioteka nie importuje Docker SDK
i nie wykonuje operacji na daemonie.

Loader używa `yaml.safe_load`, nie eksportuje środowiska, nie uruchamia
procesów, nie rozwija `${VARIABLE}`, nie rozwiązuje ścieżek względnych ani
referencji `include`/`extends` i nie scala wielu plików. Nie jest pełnym
walidatorem specyfikacji Compose. Złe kształty modelowanych sekcji zgłaszają
`ValueError`; błędy plików i YAML propagują się do wywołującego.

Testy: `PYTHONPATH=src python3 -m unittest discover -s src/lib/compose_loader/tests -v`.

Referencje: [Compose services](https://docs.docker.com/reference/compose-file/services/),
[PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation).
