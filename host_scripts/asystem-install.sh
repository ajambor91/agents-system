skrypt ma instalować sam siebie
- ma stworzyć pełnego uzytkownika (możesz skorzystać z ausers-add.sh) katalog, usera itd, brak możliwości logowania
- ma skopiować repozytorium do /home/{user}/repositories/{nazwa}
- ma zrobić dowiązania do wszystkich plików w host_scripts do /user/local/bin/asystem_install jak widzisz - są zamienione na _ oraz brak rozszerzenia .sh
- ma wyświetlić użytkownikowi w jakiś ładny sposób listę repo do pobrania, lista będzie w repo/resource/repos.json
- ma zapisać do zmiennych środowiskowych nazwę usera, jego katalog domowy czyli jak zrobię gdzieś echo $USER_SYSTEM_HOME to pokaże mi /home/user-system - albo inne jeśli podano

