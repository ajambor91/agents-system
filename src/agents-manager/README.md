# agents-manager

Desktopowa aplikacja Pythona do zarządzania agentami. Kod aplikacji został
przeniesiony z repozytorium `agents-manager` do warstwy `app/`; `main.py` jest
cienkim composition rootem. Dalszy podział odpowiedzialności opisuje
[AGENT_MANAGER_MERGE.md](../../AGENT_MANAGER_MERGE.md). Aplikacja nie
jest runtime'em, nie utrzymuje procesu rezydentnego i nie powinna wykonywać
operacji roota bez warstwy kontrolnej `agents-system`.
