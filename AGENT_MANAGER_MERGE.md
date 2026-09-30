# Plan scalenia Agents Manager

## Cel

Przenieść działającą aplikację Pythona z repozytorium `agents-manager` do
`src/agents-manager/` jako aplikację desktopową. Nie przenosić do niej wspólnego
runtime ani nie tworzyć drugiego daemona.

## Stan źródłowy

Przed migracją kod produkcyjny znajdował się w `src/agents_manager/` i ma już podział
na `application.py`, klasy w `commands/` i serwisy. Obsługiwane są `install`,
`update`, `exec`, `list`, `status`, `tools`, `wakeup` oraz gateway. `delete`
pozostaje placeholderem. Starszy `src/agents/agents.py` nie jest używany przez
aktualne wrappery.

Istotne zasoby po migracji:

- `agents/<name>/config.json`, personality i skrypty;
- `agents/shared/scripts/` kopiowane jako snapshot narzędzi;
- plugin `provider_plugins/openclaw/agent-executor`;
- `/home/user-system/.agents/agents.json` i per-agent `runtime.json`;
- wrappery `agents_*` i testy regresyjne.

## Docelowa granica

```text
src/agents-manager/
|-- main.py
`-- app/
    |-- application.py
    |-- commands/
    `-- services/

agents/
|-- <agent>/
`-- shared/scripts/

provider_plugins/openclaw/
`-- agent-executor/
```

Desktop odpowiada za interakcję operatora i budowę typowanego żądania.
Uprzywilejowane zmiany użytkowników, ACL, sudoers i procesów wykonuje control
plane przez jawny interfejs. Gateway/daemon przechodzi do `src/runtime/` albo
zostaje adapterem OpenClaw zarządzanym przez runtime.

## Mapa przeniesienia

| Źródło `agents-manager` | Cel | Decyzja |
| --- | --- | --- |
| `src/agents_manager/application.py` | `src/agents-manager/app/application.py` | przeniesiono |
| `src/agents_manager/commands/` | `src/agents-manager/app/commands/` | przeniesiono klasy use-case |
| `services/agent_config.py`, `agent_catalog.py` | `app/services/` | przeniesiono |
| `services/agent_registry.py`, `state.py` | `app/services/` | przeniesiono; pozniejszy podzial |
| `services/linux_user.py`, `sudo_policy.py`, `symlink.py` | `app/services/` | przeniesiono; do dalszego wydzielenia |
| `services/openclaw.py` | `app/services/openclaw.py` | przeniesiono adapter CLI |
| `services/agent_executor.py`, `process.py` | `app/services/` | przeniesiono; wymaga audytu polityk |
| `gateway.py`, `services/wakeup.py` | `app/` i `app/services/` | przeniesiono jako adapter przejsciowy |
| `src/agents/<name>/` | `agents/<name>/` | przeniesiono jako wersjonowane źródło |
| `src/shared/scripts/` | `agents/shared/scripts/` | przeniesiono; instalacja zachowuje snapshot |
| `openclaw_plugins/agent-executor` | `provider_plugins/openclaw/agent-executor` | przeniesiono z manifestem |
| `src/agents/agents.py` | brak | nie przenosić; tylko test porównawczy jeśli potrzebny |

## Etapy

### 1. Zamrożenie kontraktu

- Spisać wszystkie flagi i kody wyjścia obecnych wrapperów.
- Oznaczyć `delete` nadal jako niewdrożone.
- Zrobić fixture `agents.json`, configów agentów i odpowiedzi OpenClaw.
- Zapisać testy `--dry-run`, `--force`, gateway user i identity.

### 2. Interfejs control plane

- Zdefiniować żądania: `agent.install`, `agent.update`, `agent.exec`,
  `agent.list`, `agent.status`, `agent.tools`, `agent.wakeup`.
- Oddzielić dane operatora od uwierzytelnionej tożsamości runtime.
- Określić, które operacje wymagają root i które są tylko odczytem.
- Nie przekazywać polecenia jako string; executor przyjmuje executable i argv.

### 3. Przeniesienie aplikacji desktopowej

- Przenieść composition root, komendy i czyste serwisy.
- Zastąpić parser argparse definicjami JSON.
- Pozostawić desktop bez pętli serwera i bez własnego PID/socketu.
- Dodać klienta control plane/runtime z timeoutem i stabilnymi błędami.

### 4. Definicje i narzędzia agentów

- Przenieść configi Huggin, Mimir i Sindri bez zmiany schematu.
- Zachować kopiowanie personality jako snapshot, nie symlink.
- Zachować dereferencjonowanie współdzielonych skryptów.
- Ujednolicić `bootstrap.sh`, `get_var` i eksportowane środowisko.
- Zweryfikować plugin AgentExecutor i jego manifest przed instalacją.

### 5. Gateway i wakeup

- Usunąć potrójny łańcuch narzędzi tam, gdzie wystarcza jedno wywołanie
  wspólnego executora.
- Przenieść lifecycle gatewaya do `src/runtime/`.
- Zachować `agents_wakeup` jako operację domenową, nie dodatkowy daemon.
- Sprawdzić, czy OpenClaw CLI nadal musi działać jako gateway user.

### 6. Kompatybilność i cutover

- Stare wrappery w repo źródłowym kierują do nowych entrypointów i emitują
  ostrzeżenie deprecacyjne.
- Przez jeden cykl wersji porównywać JSON wynikowy i stan plików.
- Przełączyć `repo-manifests` i katalog narzędzi na nowe źródło.
- Dopiero potem wyrejestrować stare repo i zarchiwizować checkout.

## Kryteria akceptacji

- Wszystkie dotychczasowe testy Agents Manager przechodzą z nowej ścieżki.
- Nie ginie workspace, historia, bindings ani `agents.json`.
- `--force` nie usuwa całego workspace.
- `--dry-run` nie modyfikuje hosta.
- Awaria OpenClaw daje `unavailable`, nie fałszywe `deleted`.
- Desktop nie ma własnego runtime/gateway daemona.
- Każda operacja uprzywilejowana ma uwierzytelnionego aktora i audyt.

## Rollback

Przed cutover wykonać kopię rejestru i konfiguracji agentów. Wrappery można
przełączyć z powrotem na stare repo bez migracji wstecz danych, dopóki oba
warianty korzystają z tego samego wersjonowanego schematu `agents.json`.
