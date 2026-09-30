# agents-data-runtime

Osobny runtime transportu danych agentów. Utrzymuje połączenia odbiorców,
subskrybuje strumienie wiadomości i dostarcza zdarzenia do lokalnych aplikacji
`agents-data`. `main.py` jest wyłącznie composition rootem, a implementacja
brokera znajduje się w `service.py`.

