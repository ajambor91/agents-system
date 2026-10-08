# agents_data_runtime

Osobny runtime transportu danych agentów. Utrzymuje połączenia odbiorców,
subskrybuje strumienie wiadomości i dostarcza zdarzenia do lokalnych aplikacji
`agents_data`. `__main__.py` jest wyłącznie composition rootem, a implementacja
brokera znajduje się w `service.py`.

