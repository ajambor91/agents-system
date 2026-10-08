# Unix socket client

Biblioteka udostępnia działający transport Unix (`AF_UNIX`, `SOCK_STREAM`),
kodek JSON UTF-8 z separatorem nowej linii, klienta oraz fasadę `SocketClient`.
Nie zawiera protokołu ani konfiguracji runtime aplikacji.

## Użycie

Konfigurację definiuje i tworzy aplikacja importująca bibliotekę. Dziedziczy
ona po `AbstractSocketConfiguration` i udostępnia `socket_path` (`Path`),
`connect_timeout`, `request_timeout` (sekundy lub `None`) oraz
`maximum_response_bytes` (dodatni limit rozmiaru ramki).

```python
from lib.unix_socket.socket_client_builder import SocketClientBuilder
from lib.unix_socket.models import Request

# configuration: instancja konfiguracji zdefiniowanej w aplikacji
client = SocketClientBuilder.create(configuration).get()
try:
    client.connect()
    response = client.message(Request("echo", {"text": "hello"}))
finally:
    client.close()
```

`create(configuration)` wymaga jawnej konfiguracji i zwraca builder. `get()`
zwraca jego `SocketClient`. `configure()` również zwraca builder, bez tworzenia
klienta i bez otwierania połączenia. Nie ma globalnego rejestru ani singletona.
Każdy builder ma własne komponenty i wynik; `get()` przed `create()` zgłasza
`ClientNotConfiguredException`. Przed ponownym `create()` zamknij połączenie.

## Własne implementacje

`SocketClient.socket_exists()` sprawdza, czy skonfigurowana ścieżka wskazuje
socket, bez otwierania połączenia. Fasada deleguje przez klienta do
`UnixSocketTransport.socket_exists(configuration)`. Istnienie socketu nie
potwierdza działania serwera; błędy `connect()` nadal wymagają obsługi.
Własne implementacje klienta i transportu muszą udostępniać te metody.

Import abstrakcji klienta, kodeka i transportu jest potrzebny tylko przy
zastępowaniu implementacji domyślnych:

```python
from lib.unix_socket.socket_client_builder import SocketClientBuilder
from lib.unix_socket.abstract import AbstractUnixSocketTransport

class MyTransport(AbstractUnixSocketTransport):
    # __init__(), is_connected, connect(configuration), exchange(frame, timeout=...), close()
    ...

client = SocketClientBuilder.configure(transport=MyTransport).create(configuration).get()
```

`configure(client=..., codec=..., transport=...)` przyjmuje klasy dziedziczące
po odpowiadających im abstrakcjach. Klient otrzymuje w konstruktorze
`(configuration, codec, transport)`; kodek i transport mają konstruktor bez
argumentów. `create()` tworzy nowe instancje wszystkich trzech komponentów.

Fasada udostępnia `connect()`, `message()`/`request()`, `close()`,
`is_connected`, a także `transport`, `client`, `codec`, `connect_transport()`,
`exchange()`, `close_transport()`, `is_transport_connected`, `encode_request()`
i `decode_response()`.

Domyślny request zawiera `request_id`, `operation`, `payload` i `metadata`.
Response zawiera `request_id`, `successful`, `result` oraz `error` (obiekt przy
niepowodzeniu). Inny protokół implementuje własny `AbstractMessageCodec` i
modele `AbstractRequest`/`AbstractResponse`. Modele przechowują dane; nie ma
wspólnej klasy modelu wymagającej metod walidacji.

Transport nie ponawia żądań. Błąd po wysłaniu danych może oznaczać wykonanie
operacji po stronie serwera. Aplikacja nie może wtedy automatycznie wykonać
tej samej mutacji ponownie.

## Instalacja i testy

```bash
python3 -m pip install ./src/lib/unix_socket
PYTHONPATH=src:src/lib python3 -m unittest discover -s src/lib/unix_socket/tests -q
```

Dystrybucja udostępnia importy `lib.unix_socket` i `unix_socket`; w jednej
aplikacji używaj konsekwentnie jednej przestrzeni nazw. Nie wymaga zależności
runtime poza standardową biblioteką Pythona.
