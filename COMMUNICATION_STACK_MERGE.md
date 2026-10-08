# Plan scalenia Communication Stack

## Cel

Rozdzielić obecne `communication_stack` pomiędzy:

- `src/agents_data/` — lokalną aplikację Pythona dla nadawcy i odbiorcy;
- `src/agents_data_backend/` — trwały backend danych i streamów;
- `src/agents_data_runtime/` — osobny broker dostarczający zdarzenia do receiverów.

Po migracji żadna zwykła aplikacja nie łączy się ze starym runtime. Adapter
zgodności może należeć tylko do `src/agents_data_runtime/` i działa wyłącznie
do cutover.

## Stan źródłowy

Repozytorium zawiera obecnie:

- `src/comm/` — Python CLI `messege_send` i placeholdery sync/memory;
- `agents_scripts/shared/` — `message.py`, `message_listening.py`,
  `message_receive.py`;
- `src/runtime/__main__.py` — broker Unix socket ↔ Redis Streams z ACK;
- `src/stack/app-comm` — TypeScript HTTP ingress, zapis przed publikacją;
- `src/stack/app-data` — TypeScript MongoDB + Redis Cache;
- `src/stack/app-sync` — szkielet przyszłego sync;
- dwie instancje Redis i MongoDB w Docker Compose.

## Docelowa mapa

| Źródło | Cel | Decyzja |
| --- | --- | --- |
| `src/comm/__main__.py`, `commands/message.py` | `src/agents_data/app/` | przenieść do JSON-driven CLI |
| `src/comm/services/app_comm.py` | klient backendu Agent Data | zachować timeouty i błędy |
| `agents_scripts/shared/message*.py` | `src/agents_data/app/receiver/` | scalić w jeden klient/listener |
| `src/runtime/__main__.py` | `src/agents_data_runtime/service.py` | przenieść broker i ACK |
| `stack/app-comm` | `src/agents_data_backend/` | przepisać zachowanie do Pythona |
| `stack/app-data` | `src/agents_data_backend/` | przepisać Mongo/cache do Pythona |
| `stack/app-sync` | `src/agents_data/app/sync/` + API backendu | rozdzielić lokalne pliki od backendu |
| Docker Compose | `deploy/agents_data/` | zachować Redis×2 i Mongo, usunąć node_modules/dist |

## Docelowe API

Minimalne endpointy backendu:

- `GET /health`;
- `POST /api/messages` — walidacja, trwały zapis, publikacja;
- `GET /api/messages/{id}` — cache-first, Mongo fallback;
- `POST /api/messages/{id}/seen`;
- `POST /api/sync/plan` i `POST /api/sync/apply` dopiero po zdefiniowaniu
  konfliktów i idempotencji.

Kontrakt wiadomości zachowuje: `id`, `seenBy`, `archived`, `createdAt` i
`content`, gdzie `content` ma `sender`, `date`, `receivers` oraz tablicę
wiadomości `type/content`.

## Etapy

### 1. Schematy i testy zgodności

- Zapisać JSON Schema requestu, dokumentu przechowywanego i eventu streamu.
- Zamrozić kody HTTP i błędy obecnych usług.
- Utworzyć golden fixtures oraz test: persist → publish → fetch → deliver → ACK.
- Zachować historyczny alias `messege_send` tylko jako warstwę deprecacji;
  docelowa nazwa to `message_send`.

### 2. Agent Data Python

- Przenieść wysyłanie, `--admin`, content-file i lokalną historię.
- Połączyć listening/receive w jeden trwały receiver z reconnect/backoff.
- Zachować JSONL inbox i atomowy zapis.
- Receiver rejestruje nazwę i topics, zapisuje envelope, a dopiero potem ACK.
- Bootstrap agenta uruchamia receiver w tle przez wspólny kontrakt narzędzia.

### 3. Backend Python

- Zaimplementować walidację zgodną z obecnym Zod.
- Zachować idempotentny upsert po `message.id`.
- Zapis Mongo musi zakończyć się przed `XADD`.
- Redis Cache dostaje TTL; cache miss czyta Mongo i odbudowuje cache.
- Uwierzytelnienie nadawcy nie może ufać samemu polu `sender`.

### 4. Dedykowany Agents Data Runtime

- Przenieść lock, socket, register/ping/ack i consumer groups.
- Nazwa konsumenta zawiera identyfikator instancji, jeśli dopuścimy HA.
- Zapewnić tylko jednego aktywnego konsumenta w czasie migracji.
- Adapter starego protokołu jest izolowany i usuwalny.
- Runtime nie zapisuje domenowego dokumentu wiadomości poza diagnostyką.

### 5. Sync danych i plików

- Najpierw zdefiniować indeks, wersję, hash, tombstone i regułę konfliktu.
- Lokalny Agent Data skanuje pliki i buduje plan.
- Backend utrwala metadane oraz dokumenty; nie otrzymuje dowolnej ścieżki hosta.
- Operacja apply jest idempotentna i ma dry-run.
- Placeholdery `memory_*` pozostają niewdrożone do czasu osobnego kontraktu.

### 6. Deployment i cutover

- Nowy compose uruchamia backend, Redis Cache, Redis Streams i MongoDB.
- Nie kopiować `node_modules`, `dist` ani haseł z obecnego compose.
- Sekrety trafiają do lokalnej konfiguracji/secrets, nie do Git.
- Uruchomić nowy backend równolegle bez drugiego konsumenta streamu.
- Przełączyć producenta, następnie receiverów, na końcu konsumenta runtime.
- Opróżnić pending entries i dopiero zatrzymać stary runtime.

## Migracja danych

MongoDB może pozostać tą samą instancją, jeśli nowy model czyta istniejący
schemat bez migracji destrukcyjnej. Redis Cache można wyczyścić i odbudować.
Redis Streams wymaga zachowania grup, pending entries i identyfikatorów; nie
wolno traktować go jak cache.

Lokalne `/home/<user>/.inbox/messages.jsonl` pozostają na miejscu. Nowa
aplikacja może je czytać, ale nie przepisuje całej historii bez backupu.

## Kryteria akceptacji

- Wiadomość jest widoczna w Mongo przed eventem streamu.
- Cache miss poprawnie odbudowuje Redis Cache.
- Receiver po restarcie odbiera pending message i wysyła ACK po zapisie.
- Brak receivera nie powoduje XACK ani utraty eventu.
- `--admin` zapisuje historię u faktycznego aktora.
- Agent odpowiada przez ten sam publiczny interfejs wiadomości.
- Stary i nowy runtime nigdy nie konsumują jednocześnie tej samej grupy.
- Testy failure injection obejmują brak Mongo, Redis, backendu i zerwane
  połączenie Unix socket.

## Rollback

Producent można przełączyć z powrotem tylko wtedy, gdy schemat wiadomości jest
zgodny. Przed zmianą konsumenta należy zatrzymać nowy runtime i zweryfikować
pending entries. Mongo pozostaje źródłem prawdy; Redis Cache jest odbudowywany,
a streamów nie usuwa się podczas rollbacku.
