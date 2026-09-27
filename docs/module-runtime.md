# Runtime modułów Agents System

## Cel

Runtime pozwala dołączyć aplikację Python z innego, już zainstalowanego
repozytorium i załadować ją raz do pamięci procesu. Kolejne wywołania nie muszą
ponownie startować interpretera ani importować aplikacji.

## Rejestracja

```bash
asystem_app_add \
    --repo-name ai-module \
  --entrypoint src/ai-module/main.py \
  --start
```

Domyślna ścieżka repozytorium to
`/home/user-system/repositories/<repo-name>`. Można ją nadpisać przez
`--repository-path`. `--entrypoint` jest opcjonalny, gdy repozytorium ma
`manifest.json` z `application.entrypoint`. W przeciwnym razie runtime
zaakceptuje dokładnie jeden plik `src/**/main.py`.

## Kontrakt aplikacji

Najprostszy moduł:

```python
def handle(payload: dict) -> dict:
    return {"received": payload}
```

Dla inicjalizacji zależności:

```python
class Service:
    def handle(self, payload: dict) -> dict:
        return {"ok": True}


def create_service() -> Service:
    return Service()
```

Runtime preferuje `create_service()`, następnie `handle()`, a na końcu
`Application()`. Błąd ładowania oznacza status `error` modułu i nie zatrzymuje
pozostałych modułów.

## IPC i lifecycle

Domyślny socket to `/home/user-system/.agents/runtime.sock`, a rejestr to
`/home/user-system/.agents/modules.json`. Klient wysyła jeden wiersz JSON:

```json
{"module":"ai-module","payload":{"action":"health"}}
```

1. Repo Manager instaluje repozytorium dziecka jak dotychczas.
2. `asystem_app_add` zapisuje jego ścieżkę i entrypoint.
3. `asystem_runtime_start` ładuje wszystkie zarejestrowane moduły.
4. `asystem_app_call` komunikuje się z procesem przez Unix socket.
5. `asystem_app_remove` usuwa wpis; restart runtime zwalnia moduł z pamięci.

Aktualny runtime jest pojedynczym procesem i nie zapewnia jeszcze izolacji,
limitów czasu ani automatycznego restartu. Nie ładuj do niego niezaufanego kodu.