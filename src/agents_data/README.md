# agents_data

Lokalna aplikacja Pythona obsługująca dane i wiadomości agenta: odbiór,
lokalną skrzynkę, historię oraz synchronizację. Kod CLI i klienta HTTP został przeniesiony z `communication_stack/src/comm`
do warstwy `app/`. Dedykowany broker działa osobno w `../agents_data_runtime/`.

Plan migracji znajduje się w
[COMMUNICATION_STACK_MERGE.md](../../COMMUNICATION_STACK_MERGE.md).
