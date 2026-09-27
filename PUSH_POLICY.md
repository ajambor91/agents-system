# Polityka pushowania

- Aktualna wersja repozytorium jest w `VERSION`.
- Pierwsza wersja to `0.0.1`.
- Push wykonuj wyłącznie przez `internal_scripts/push.sh --tag X.Y.Z`.
- Skrypt wymaga czystego drzewa, tworzy annotowany tag i wysyła commit oraz tag.
- Repo Manager zapisuje wersję do registry, `data.json` i history jako `version`.
