# Polityka pushowania

- Aktualna wersja repozytorium jest w `VERSION`.
- Pierwsza wersja to `0.0.1`.
- Push wykonuj wyłącznie przez `sudo repo_push --target . --tag X.Y.Z`.
- `repo_push` jest publikowane przez Repo Manager jako `/usr/local/bin/repo_push`.
- Komenda wymaga czystego drzewa, tworzy annotowany tag i wysyła commit oraz tag.
- Repo Manager zapisuje wersję do registry, `data.json` i history jako `version`.
