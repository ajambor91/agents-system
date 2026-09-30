# Runtime

Wspólny rezydentny runtime systemu agentów. Odpowiada za socket Unix,
uwierzytelnienie klienta przez `SO_PEERCRED`, rejestr modułów, leniwe ładowanie
i przeładowywanie handlerów oraz izolowanie odpowiedzi JSON od stdout/stderr.

`service.py` jest silnikiem używanym przez aplikację `src/agents-system/`.
`main.py` jest bezpośrednim entrypointem procesu runtime.
