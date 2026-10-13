# Kroki instalacji, uruchamiania i aktualizacji agenta

Opis aktualnej implementacji `agents_manager`, na podstawie kodu z 7 października
2026. Plik znajduje się przy runtime komunikacji na życzenie użytkownika;
opisane operacje implementuje przede wszystkim `agents_manager`.

## Oznaczenia uprawnień

- **SUDO** — kod wywołuje `run_privileged()`: zwykły użytkownik uruchamia
  `sudo <komenda>`, root wykonuje komendę bezpośrednio.
- **USER** — kod wywołuje `run_as_user()`: ten sam użytkownik wykonuje komendę
  bez sudo; root używa `runuser`; inny użytkownik używa `sudo -u USER -H -- …`.
- **PLIKI** — bez automatycznego sudo. Proces musi mieć prawa do odczytu,
  zapisu, zmiany trybu lub grupy wskazanych plików.
- **BRAK** — walidacja lub operacja w pamięci, bez podnoszenia uprawnień.

To opis rzeczywistych wywołań kodu. Niektóre kroki oznaczone SUDO można byłoby
wykonać jako właściciel plików, ale obecna implementacja zawsze używa tam
`run_privileged()`.

## 1. Instalacja agenta — kolejność

Komenda przechodzi przez konsolę, control plane i `AgentsService.install()` do
`AgentsInstallatorService.execute()`. W trybie runtime proces wykonujący te
kroki jest procesem usługi Agents System.

| Krok | Co wykonujemy | Uprawnienia |
| --- | --- | --- |
| 1 | Ustalamy i walidujemy katalog definicji z `--path`. Nazwa agenta pochodzi z nazwy katalogu. | PLIKI: odczyt definicji |
| 2 | Budujemy kontekst i serwisy, wczytujemy konfigurację definicji. Uzupełniamy `name`, `user` i `model`; sprawdzamy obecność `resources/shell.template.json`. | PLIKI |
| 3 | Przygotowujemy `APP_DATA_DIR/<agent>/` oraz `shells/`. Tworzymy lub normalizujemy katalogi do `0777`. Katalog nadrzędny musi już istnieć. | PLIKI: zapis; zmiana grupy/trybu może wymagać właściciela lub roota, bez automatycznego sudo |
| 4 | Wybieramy użytkownika wykonawczego. Gdy definicja lub flaga wskazuje `user`, używamy dedykowanego konta; w przeciwnym razie konta gateway. Istniejące konto tylko odczytujemy, brakujące tworzymy przez `adduser`. | SUDO tylko przy tworzeniu konta |
| 5a | Dla dedykowanego konta przygotowujemy home: `bin`, `scripts`, `tools`, `tmp`, `.config`, `.cache`, `.local/bin`, `.local/share`, z właścicielem agenta i trybem `0700`. | SUDO: `install -d -o … -g …` |
| 5b | Dla dedykowanego konta przygotowujemy `<home>/workspace`, dajemy gateway ACL do przejścia przez home oraz pracy w workspace, także domyślne ACL dla nowych plików. | SUDO: `install`, `setfacl` |
| 5c | Bez dedykowanego konta tworzymy `<gateway_home>/.openclaw/<agent>_workspace`. Kroki 5a–5b są pomijane. | PLIKI |
| 6 | Kopiujemy `personality/` do workspace. Przy `force` zastępujemy kolidujące pliki/katalogi. | PLIKI: kod używa bezpośrednio operacji Pythona, także w dedykowanym workspace |
| 7 | Kopiujemy skrypty definicji do `<home>/scripts` dla dedykowanego konta albo `<workspace>/scripts` dla konta gateway. | SUDO dla dedykowanego konta: `install`, `cp`, `chown`, przy zastępowaniu także `rm`; inaczej PLIKI |
| 8 | Wdrażamy wspólne narzędzia z `agents/shared/scripts` do `<tools_root>/bin`, przygotowujemy bootstrap i obsługujemy zastępowanie istniejących plików. | SUDO dla dedykowanego konta; inaczej PLIKI |
| 9 | Budujemy zmienne `AGENT_*` i generujemy konfigurację powłoki, m.in. `.agentrc` i `.bashrc`, w katalogu stanu. | PLIKI |
| 10 | Budujemy opis runtime i przygotowujemy katalogi historii oraz początkowy wpis historii w home agenta. | USER: użytkownik agenta |
| 11 | Zapisujemy `runtime.json` oraz efektywne `config.json`, w tym `definition_path` używane przy aktualizacji. | PLIKI: zapis atomowy i ustawienie uprawnień/grupy |
| 12 | Nadajemy gateway odczyt runtime i konfiguracji; przy dedykowanym koncie także odczyt konfiguracji agentowi. | SUDO: `setfacl`, chyba że odbiorca jest właścicielem stanu — wtedy krok jest pomijany |
| 13 | Wywołujemy `host_scripts/agents-gateway-start.sh` przez Bash. | SUDO — w każdej rzeczywistej instalacji |
| 14 | Tworzymy link `<workspace>/config.json` do konfiguracji w katalogu stanu. | SUDO: `ln`, `chown -h`, przy zastępowaniu `rm`; poprawny istniejący link jest pomijany |
| 15 | Dla dedykowanego konta nadajemy odczyt plików powłoki i tworzymy linki `.bashrc` oraz `.agentrc` w home. | SUDO: `setfacl`, `ln`, `chown -h`, opcjonalnie `rm` |
| 16 | Dla dedykowanego konta instalujemy politykę `/etc/sudoers.d/agent-manager-<agent>`, pozwalającą gateway uruchamiać powłokę jako agent bez hasła. Gdy użytkownicy są identyczni, nic nie zapisujemy. | SUDO: `visudo -cf`, `install` jako root |
| 17 | Rejestrujemy agenta w OpenClaw. Jeśli istnieje, bez `force` przerywamy; z `force` aktualizujemy rejestrację. Następnie stosujemy identity z workspace. | USER: użytkownik gateway |
| 18 | Tylko dla backendu `agent-executor`: synchronizujemy snapshot pluginu do `APP_DATA_DIR/openclaw_plugins/agent-executor`, instalujemy i włączamy plugin w OpenClaw. | Snapshot: PLIKI, kod dopuszcza root lub gateway; CLI OpenClaw: USER gateway |
| 19 | Jeśli definicja zawiera politykę narzędzi, ustawiamy ją w OpenClaw. | USER gateway |
| 20 | Jeśli skonfigurowano bootstrap, uruchamiamy go z przygotowanymi zmiennymi środowiska. | USER: właściciel narzędzi, czyli użytkownik agenta |
| 21 | Synchronizujemy `APP_DATA_DIR/agents.json`: wcześniejsze wpisy, pliki runtime, historia zadań i dane OpenClaw. | PLIKI dla stanu; USER gateway dla odczytu OpenClaw |
| 22 | Zwracamy wynik `installed` oraz ścieżki, użytkowników i komunikaty. | BRAK |

`dry_run` pomija mutacje instalacyjne i zgłasza plan, ale nie oznacza całkowitego
braku odczytów ani procesów: np. adapter OpenClaw sprawdza istniejącą rejestrację
przed gałęzią dry-run.

## 2. Uruchamianie komendy jako agent — `exec`

To wykonanie konkretnej komendy, a nie start stałego procesu modelu.

| Krok | Co wykonujemy | Uprawnienia |
| --- | --- | --- |
| 1 | Budujemy serwisy i wczytujemy runtime wskazanego agenta. | PLIKI |
| 2 | Wczytujemy timeout z `config.json`: domyślnie 300 sekund, poprawny zakres 1–3600. | PLIKI |
| 3 | Sprawdzamy, czy komenda nie jest pusta; ustalamy `requested_by`. | BRAK |
| 4 | Przygotowujemy historię, jeśli jeszcze jej nie ma. | USER agenta |
| 5 | Dopisujemy `command_started` z identyfikatorem wykonania. | USER agenta |
| 6 | Uruchamiamy Bash jako użytkownik agenta: wczytanie `.agentrc`, wejście do workspace, ustawienie `AGENT_REQUESTED_BY`, wykonanie przekazanej komendy przez kontrolowany hook `eval`. | USER agenta; dodatkowe wymagania samej komendy zależą od jej treści |
| 7 | Przechwytujemy stdout, stderr i kod zakończenia; egzekwujemy timeout. | BRAK dodatkowego podnoszenia uprawnień |
| 8 | Dopisujemy `command_completed` z kodem zakończenia. | USER agenta |
| 9 | Zwracamy `agent`, `returncode`, `stdout`, `stderr`. | BRAK |

Przy błędzie uruchomienia procesu krok 8 może nie zostać osiągnięty.

## 3. Uruchamianie agenta do obsługi wiadomości — `wakeup`

| Krok | Co wykonujemy | Uprawnienia |
| --- | --- | --- |
| 1 | Walidujemy kopertę i jej rozmiar, ustalamy użytkownika wywołującego. | BRAK |
| 2 | Wczytujemy `runtime.json` i sprawdzamy uprawnienia: proces musi być użytkownikiem gateway, wywołujący gateway lub użytkownikiem tego agenta. | PLIKI i kontrola tożsamości |
| 3 | Walidujemy nadawcę; wiadomość agenta do samego siebie jest pomijana. | BRAK |
| 4 | Budujemy prompt i zapisujemy tymczasowy plik z trybem `0600`. | PLIKI |
| 5 | Wywołujemy OpenClaw dla agenta, z kluczem sesji zależnym od agenta i nadawcy oraz timeoutem. | USER gateway — nie bezpośrednio konto systemowe agenta |
| 6 | Zwracamy stdout/stderr i usuwamy tymczasowy plik także przy błędzie. | PLIKI |

Gateway może też przyjmować żądania wakeup przez Unix socket i ustalać
użytkownika klienta przez `SO_PEERCRED`. Komenda `AgentsWakeupService` wywołuje
serwis wakeup bezpośrednio; nie należy utożsamiać obu wejść z jednym połączeniem
przez socket.

## 4. Aktualizacja agenta — `update`

1. Kopiujemy flagi żądania i ustawiamy `force=True`, `operation="update"`,
   `user=None`, `model=None` oraz gateway z kontekstu. **BRAK**.
2. Ponownie wywołujemy ten sam `AgentsInstallatorService.execute()`.
3. Jeśli nie podano ścieżki, odczytujemy `definition_path` z istniejącego
   `config.json`; dla starszych instalacji fallbackiem jest `agents/<name>`
   w repozytorium. **PLIKI**.
4. Wczytujemy definicję ponownie, także użytkownika i model — `None` w kroku 1
   nie wymusza konta współdzielonego, tylko pozwala pobrać wartości z definicji.
5. Wykonujemy kroki instalacji 3–21 z zastępowaniem istniejących zasobów.
   Istniejącego konta nie tworzymy ponownie; przygotowanie home, ACL, linków,
   sudoers, gateway i bootstrapu nadal może być wykonywane.
6. Zwracamy `updated` zamiast `installed`.

**Uprawnienia są takie same jak przy instalacji.** Update nie wykonuje pull Git
definicji i nie jest osobnym mechanizmem aktualizacji działającego procesu.

## 5. Obecne ograniczenia implementacji

- `NoNewPrivileges=true` w usłudze blokuje podnoszenie uprawnień przez sudo.
  Dotyczy zarówno SUDO, jak i USER wymagającego przełączenia z nieuprzywilejowanego
  konta na inne konto. `NOPASSWD` nie usuwa tej blokady.
- `ProtectHome=read-only` oraz `ProtectSystem=strict` ograniczają zapis;
  szablon dopuszcza zapis do `APP_DATA_DIR` i `APP_RUNTIME_DIR`. Samo umożliwienie
  sudo nie rozwiązuje wszystkich ograniczeń pracy w `/home` i `/etc`.
- W obecnym checkoutcie brakuje `host_scripts/agents-gateway-start.sh`, mimo że
  instalator agenta próbuje go uruchomić w kroku 13.
- `0777` dotyczy katalogów agenta i `shells/`, nie wszystkich plików, katalogu
  nadrzędnego ani home innych użytkowników. Nie zastępuje uprawnień do zmiany
  właściciela, ACL i przełączania użytkownika.
- Operacje instalacji wykonują się kolejno; ta ścieżka nie ma wspólnego rollbacku
  całej instalacji agenta. Błąd może pozostawić wykonane wcześniejsze kroki.
- `AgentsService` zamienia wyjątek na słownik z `message`. Dispatcher może potem
  zapisać `operation completed … status=returned`, mimo że instalacja się nie udała.

## Źródła kolejności

- [Instalacja](../agents_manager/app/services/agents_installator_service.py)
- [Update](../agents_manager/app/services/agents_update_service.py)
- [Exec — adapter](../agents_manager/app/services/agents_executor_service.py)
- [Exec — proces i historia](../agents_manager/app/services/agent_executor.py)
- [Wakeup](../agents_manager/app/services/wakeup.py)
- [Użytkownicy i workspace](../agents_manager/app/services/linux_user.py)
- [Stan i ACL](../agents_manager/app/services/state.py)
- [Linki](../agents_manager/app/services/symlink.py)
- [Sudoers](../agents_manager/app/services/sudo_policy.py)
- [Procesy i przełączanie użytkownika](../agents_manager/app/services/process.py)
- [OpenClaw](../agents_manager/open_claw/backend.py)
- [Szablon systemd](../../resources/system.template.service)
