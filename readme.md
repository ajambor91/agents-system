Jest to system, który w oparciu o gitops, openclaw dostarcza rozwiązanie oparte o agentach AI,ktorzy mają dedykowane katalogi użytkownika, narzędzia oraz zadania. Co jest możliwe jest oskryptowane, żeby agent mógł posłużyć  się skryptem, zamiast zastanawiać się nad kolejnymi krokami.
System składa się z kilku elementów
1. Agents System - to repozytorium, przechowuje ogólne założenia systemu, skills, architekturę, standardy, tworzy użytkownika, przechowuje jego katalog domowy, nazwę
2. Repo Manager - menadżer repozytoriow, odpowiada za instalacje oraz monitorowanie repozytoriów, można wyświetlic historie, albo wygodnie zainstlować repozytorium
3. Agents Manager - tu można dodać agentów, uruchomić ich, monitorować ich pracę
4. Repo Manifests - repoytorium odpowiada za porządek wszystkich innych repozytoriow pod względem standaryzacji jsonów dla agentów AI
5. Repo Template - puste repozytorium, które narzuca strukturę wszystkich repozytoriów
6. AI Module - dodanie AI oparte o Ollama i inne narzędzia

Struktura repozytorium
host_scripts - katalog dla skryptow sh,która Repo Manager podczas instalacji linkuje do katalogu /usr/local/bin
repo.json - plik z podsta

Zasady ogólne
1. Główny katalog projektu to warstwa nadrzędna, będą tutaj katalogi dla skyptów, aplikacji, konfiguracja
2. Jeśli repozytorium jest systemowe to ma być tworzony plik .system on będzie pusty
3. Aplikacja zawsze będzie w src, nie ważne czy to aplikacja systemowa, czy repozytorium projektowe
4. Jeśli repozytorium jest systemowe, to aplikacja będzie napisana w python
5. jedna komenda = jedna klasa python
6. Aplikacja python będzie miała jeden plik startowy np. app.py
7. Api aplikacji to skrypty bash, one odpytują Pythona
8. Katalog internal-scripts to skrypty,które odnoszą się tylko i wyłacznie do tego repozytorium
9. Katalog self-scripts oraz skrypty z nim związane to są hooki to wywyołania przez instalator
10. W głównym katalogu projektu jest dopuszczalny plik .env - on odpowiada tylko za konfigurację systemową, nie biznesową repozytorium
11.Ma zawierać ogólne instrukcje dla agentów AI oraz człowieka
12. Ma zawierać listę zależności - plik 'needed_repos' 
13. Ma zawierać instrukcje dla agenta tworzącego repozytorium - ma się dopytać czym ma być repozytorium i na podstawie tego dopiero zbudować instrukcje
14. W głównym katalogu projektu ma się też znajdować plik usage - tam mają być spisane komendy,które udostępnia skrypt
ma być human read
15. .env ma być wpisany do gitignore, ale do repo ma iść .env.example

Czym jest to repozytorium
1. Jest to puste repozytorium na podstawie którego będą tworzyć sie inne repozytoria
2. Chcę, żeby na github poszło już gotowe repozytorium, ale przy tworzeniu nowego repozytorium można było sobie wszystko skonfigurować przez flagi, np -s --system znaczy systemowe, -n --name nazwa, -r --repo - link do github, 



UPDATE
1. Każde repozytorium musi mieć .env albo .env.example. Ma działać to tak, że każde repozytorium musi mieć konfigurowalne:
- ścieżka instalacji
- użytkownik, który będzie właścicilem repozyotirum
- nazwę
- czy jest systemowe
2. W każdym repozytorium ma być na początku plik repo.json w nim mają być informacje,plik idzie do github, w nim ma być tylko 
{ 
    repo_name: 'nazwa',
    system: true | false,
    path: absolute_path
    owner: uzytkownik owner
    version: commit_tag albo puste,
    techs: [
        {
            "tech" : "python"
            "deps": ["scikit-learn", "requests", "pydantic"]
        },
        {
            "tech" : "ollama",
            "install_command" : "url -fsSL https://ollama.com/install.sh | sh"
        }
    ]
    
}
jeśli użytkownik wykona komendę inicjalizującą repo XXX to w komendzie mają być flagi -p --path sciezka, -u --user nazwa_usera, -n --name nazwa_repozytorium -s --system 
jeśli w repo.json repozytorium jest nazwa oraz we fladze jest nazwa, to zostaną podmienione w repo.json, jeśli flag nie ma - lecą wartości domyślne tj. name: z repo json, tak jak system,  jeśli w repo.json jest wpisane system na true, to zawsze będzie to system, tego nie da się nadpisać, da się tylko jeśli system jest false - wtedy można tak nadpisać
projekt ma mieć skrypt self/init_repo.sh w tym skrypcie będzie generowany prawdziwy json, ten, który podeslałem ma być generowany, tj ma być plik json w resources/repo.json ale z placeholderami, skrypt w self/init_repo.sh będzie wołany gdy repo_install będzie instalować repozytorium - to ma być flow przy każdym repozytorium, jeśłi nie znajdzie pliku self/init_repo.sh to po prostu pomija tak czy siak, ma być to robione przed wpisaniem do registry, regstrsy ma zresztą bazować na repo.json w głównym katalogu


architektura aplikacji Python i skryptów
1. API to zawsze są skrypty w host_scripts, ktore są linkowane przez Repo Manager
2. aplikacja Python jest w src/{nazwa_repo}/main.py
3. w katalogu src/{repo_name}/services są klasyczne serwisy, src/{repo_name}/commands są odwzorowane dokładne komendy ze host_scripts

agents-system czyli ten projekt ma mieć możliwość dołączania "aplikacji" pythona z innych repo, tj. chcę mieć mechanizm, ktory pozwoli mi zrobić asystem_app_add -r --repo_name np. asystem_app_add -r ai_module wtedy chcę miec możliwość jakoś dowiązać paczkę pythona z ai_module, chodzi o to, że ta aplikacja w agents-system ma mieć możliwość być ciągle gotowa do działania w RAM, nie będzie musiała nic ladowaći interpretować przy każdym wywołaniu - aplikacje osobno z modułów działają standardowo czyli bash -> odpalanie pythona -> akcja 

Agenci - ogólnie agenci dostają swojego nowego uzytkownika i mają nakładkę executora na wykonywanie komend, więc jak mam agenta Huggin to on będzie dzialał jako Huggin. Agenci zapisują swoje dzialania i konfiguracje, np. tak:
adam@adam-GF63-Thin-11UC:~/projects$ sudo ls -la /home/user-system/.agents/huggin
razem 20
drwx--s--x  3 user-system user-system 4096 wrz 27 19:08 .
drwx--s--x  3 user-system user-system 4096 wrz 27 18:18 ..
-rw-r-----+ 1 user-system user-system  248 wrz 27 19:08 runtime.json
-rw-r-----  1 user-system user-system 3559 wrz 27 19:08 shell.json
drwx--s--x  2 user-system user-system 4096 wrz 27 19:08 shells
adam@adam-GF63-Thin-11UC:~/projects$ 


user-system to użytkownik systemowy wskazany w systemie, jest też historia repozytorium:
dam@adam-GF63-Thin-11UC:~/projects$ sudo repo_show -n agents-manager
Nazwa: agents-manager
ID: agents-manager
Repozytorium: git@github.com:ajambor91/agents-manager
Ścieżka: /home/user-system/repositories/agents-manager
Owner: user-system:user-system
System: tak
Status: installed
Usunięcie: -
Purge: -
Branch: main
Branche: main, origin, origin/main
Instalacja: 2026-09-27T15:35:54Z
Aktualizacja: 2026-09-27T17:08:37Z

Autorzy:
  Adam Jambor <adam.jambor@correctcontext.com>

Commity zarządzane:
  20a32cc0a6c48c343005d9b5c3f06d61b002d972 | main | repo-register | 2026-09-27T15:35:54Z
  20a32cc0a6c48c343005d9b5c3f06d61b002d972 | main | repo-register | 2026-09-27T15:36:29Z
  20a32cc0a6c48c343005d9b5c3f06d61b002d972 | main | repo-register | 2026-09-27T15:37:05Z
  20a32cc0a6c48c343005d9b5c3f06d61b002d972 | main | repo-register | 2026-09-27T15:46:12Z
  20a32cc0a6c48c343005d9b5c3f06d61b002d972 | main | repo-register | 2026-09-27T16:26:50Z
  20a32cc0a6c48c343005d9b5c3f06d61b002d972 | main | repo-update | 2026-09-27T16:38:54Z
  d7104025898c3da0708c38bf69951c15759451ab | main | repo-update | 2026-09-27T16:53:56Z
  306262cc2b2eeee4e36270b9c2065446bae66e2b | main | repo-update | 2026-09-27T17:08:37Z

Ścieżki:
  global_registry: /home/user-system/.repos/repos
  metadata_directory: /home/user-system/.repos/repositories/agents-manager
  data: /home/user-system/.repos/repositories/agents-manager/data.json
  history_directory: /home/user-system/.repos/repositories/agents-manager/history
  readme: -

Historia akcji:
  [2026-09-27T10:00:00Z] - | - | -
    komenda: 
