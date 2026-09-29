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
pozostałych modułów. Nowo zarejestrowany moduł jest ładowany leniwie bez restartu,
a zmiana czasu modyfikacji entrypointu powoduje przeładowanie przy następnym
wywołaniu.

## IPC i lifecycle

Domyślny socket to `/home/user-system/.agents/runtime.sock`, a rejestr to
`/home/user-system/.repos/modules.json`. Przy pierwszym odczycie starszy
`/home/user-system/.agents/modules.json` jest automatycznie migrowany do nowej
lokalizacji. Klient wysyła jeden wiersz JSON:

```json
{"module":"ai-module","payload":{"action":"health"}}
```

Odpowiedź rozdziela wynik handlera od przechwyconych strumieni:

```json
{"ok":true,"result":{"status":"ready"},"stdout":"","stderr":""}
```

Brak modułu jest jedynym błędem runtime, który wprost zezwala klientowi na
lokalny fallback:

```json
{"ok":false,"error_code":"module_unavailable","error":"..."}
```

1. Repo Manager instaluje repozytorium dziecka jak dotychczas.
2. `asystem_app_add` zapisuje jego ścieżkę i entrypoint.
3. `asystem_runtime_start` ładuje wpisy dostępne podczas startu.
4. Nowe wpisy są ładowane leniwie przy pierwszym wywołaniu.
5. `asystem_app_call` komunikuje się z procesem przez Unix socket.
6. `asystem_app_remove` usuwa wpis; następne wywołanie zwalnia cache modułu.

Próba usunięcia niezarejestrowanej nazwy kończy się kodem `1` i czytelnym
komunikatem na `stderr`, bez tracebacka Pythona.

Aktualny runtime jest pojedynczym procesem i nie zapewnia jeszcze izolacji,
limitów czasu ani automatycznego restartu. Nie ładuj do niego niezaufanego kodu.
Rozłączenie klienta przed odebraniem wyniku jest ignorowane przez pętlę serwera
i nie może zakończyć całego runtime'u.
