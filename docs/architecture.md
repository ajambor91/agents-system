# Architektura systemu agentów

## Przepływ odpowiedzialności

```text
agents-system (standard i szablony)
        |
        v
repo-template (szkielet repozytorium)
        |
        v
repo-manager (clone, lifecycle, wrappery)
        |
        +--> repo-manifests (rejestr, dane, historia, manifesty narzędzi)
        |
        +--> repozytorium aplikacji (src, hooki i komendy)
        |
        v
agents-manager (agenci i executor)
```

## Trzy kontrakty danych

### Kontrakt repozytorium

Wersjonowany w repozytorium jako `manifest.json`. Opisuje cel, aplikację,
układ katalogów i publiczne komendy. Jest czytany przez ludzi, agenty i narzędzia
budujące repozytorium.

### Kontrakt instalacji

Zarządzany przez Repo Managera i `repo-manifests`. Obejmuje ścieżkę checkoutu,
ownera, tryb systemowy, branch, commit, status, autorów i akcje lifecycle.

### Kontrakt narzędzia

Wersjonowany jako `kind: "tool-manifest"`. Opisuje komendę dostępną agentowi,
jej argumenty, wynik i ryzyko wykonania. `registry.json` jest tylko indeksem
wygenerowanym z tych manifestów.

## Zasada źródła prawdy

Plik źródłowy jest edytowany przez człowieka lub generator. Plik wygenerowany
jest odtwarzalny i nie powinien być ręcznie modyfikowany. W szczególności:

- źródło manifestu narzędzia pozostaje w katalogu manifestów repozytorium;
- `available_tools/tools/*.json` jest linkiem albo kopią według konfiguracji;
- `available_tools/registry.json` powstaje podczas scalania;
- centralne `data.json` i historia powstają przez API `manifests_*`;
- `repo_data/` udostępnia linki do centralnych danych.

## Plan migracji szablonów JSON

1. Ustalić wersjonowany katalog szablonów w `agents-system`.
2. Zachować identyczne `schema_version`, `kind` i nazwy pól z obecnym schematem.
3. Dodać test renderowania każdego szablonu i walidacji przykładowego JSON.
4. Zmienić `repo-manifests` tak, aby korzystało z wersji zainstalowanej razem z `agents-system` albo z jawnie wskazanego katalogu.
5. Dopiero po zgodności testów usunąć duplikację szablonów z `repo-manifests`.

Migracja nie powinna zmieniać znaczenia istniejących dokumentów ani mieszać
manifestu repozytorium z manifestem narzędzia.
