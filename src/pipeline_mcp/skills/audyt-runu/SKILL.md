---
name: audyt-runu
description: "Weryfikuje ex-post spójność całego run'u pipeline'u przez graf Memgraph: integralność checkpointów, spójność grafu, osierocone węzły, brakujące krawędzie, anomalie relacyjne."
version: 1.0.0
argument-hint: "[RUN_ID] [opcjonalnie: TRYB AUDYTU, ZAKRES]"
triggers:
  - user
  - model
---
# Workflow audytu relacyjnego run'u pipeline'u

Celem workflowu jest weryfikacja ex-post spójności całego run'u pipeline'u przez graf powiązań w Memgraph i pliki checkpointów. Audyt wykrywa anomalie relacyjne, osierocone węzły, brakujące krawędzie, niespójności między checkpointami a grafem oraz naruszenia reguł integralności.

Audyt run'u odpowiada na pytanie "czy run jest spójny relacyjnie i które anomalie wystąpiły?", a nie "czy artefakt jest zgodny z pytaniem?" (to `sprawdzenie`) ani "gdzie jesteśmy względem planu?" (to `monitoruj`).

## Rola

Przyjmij rolę eksperta od audytu relacyjnego baz danych grafowych i weryfikacji integralności danych, łączącego myślenie systemowe, krytyczne i abdukcyjne.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- zweryfikować ex-post spójność całego run'u pipeline'u,
- wykryć osierocone węzły w grafie run'u,
- sprawdzić brakujące krawędzie między stacjami,
- wykryć anomalie relacyjne (stacje bez poprzednika, zmienne bez źródła, decyzje bez uzasadnienia),
- porównać spójność między checkpointami plikowymi a grafem Memgraph,
- zweryfikować reguły integralności grafu,
- przeprowadzić audyt przed archiwizacją albo ponownym uruchomieniem run'u,
- sprawdzić relacje między runami (kontynuacja, naprawa, ponowne uruchomienie).

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce monitorować postęp bieżącego run'u - użyj skilla `monitoruj`,
- użytkownik chce audytować zgodność artefaktu z pytaniem - użyj skilla `sprawdzenie`,
- użytkownik chce ocenić wartość ex-post rozwiązania - użyj skilla `ewaluacja`,
- użytkownik chce zapisać wnioski z run'u - użyj skilla `utrwal`,
- brak `run_id` albo run nie istnieje w `.ai-kb/pipeline-runs/`.

## Język

Audyt prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `RUN_ID` - identyfikator run'u do audytu.

Opcjonalnie:

- `TRYB AUDYTU` - `szybki`, `pełny` (domyślnie `pełny`), `dogłębny`,
- `ZAKRES` - które wymiary audytu sprawdzić (wszystkie domyślnie),
- `ŹRÓDŁA` - dodatkowe materiały.

## Kontrola kompletności wejścia

1. Jeśli brakuje `RUN_ID`, poproś o wskazanie.
2. Jeśli katalog `.ai-kb/pipeline-runs/<run_id>/` nie istnieje, zgłoś błąd i zakończ.
3. Jeśli `manifest.yaml` nie istnieje albo jest uszkodzony, zgłoś błąd i zakończ.
4. Jeśli Memgraph jest niedostępny, wykonaj audyt tylko na podstawie checkpointów plikowych i oznacz ograniczenie.

## Tryby audytu

- `szybki` - sprawdzenie spójności grafu + liczba anomalii, bez szczegółów.
- `pełny` - domyślny: wszystkie wymiary audytu, lista anomalii z uzasadnieniem.
- `dogłębny` - pełna analiza z zapytaniami Cypher per reguła integralności, porównanie checkpointów z grafem, analiza przyczyn anomalii.

## Źródła prawdy

1. `.ai-kb/pipeline-runs/<run_id>/` - manifest i checkpointy plikowe.
2. Memgraph MCP - graf powiązań run'u.
3. `kontrakty_pipelines.md` - kontrakty I/O stacji (do weryfikacji pól wymaganych).
4. `_shared/graf-pipeline.md` - schemat grafu, reguły integralności, zapytania wzorcowe.

Stosuj w podanej kolejności. Konflikty źródeł, hierarchia i reguły uzupełniające: patrz `_shared/zrodla-i-narzedzia.md`.

## Narzędzia lokalne

- `desktop-commander` (pełne) - odczyt manifestu i checkpointów, weryfikacja YAML.
- `Memgraph MCP` (warstwa grafowa) - zapytania Cypher weryfikujące spójność grafu.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Wymiary audytu

### 1. Integralność checkpointów

Sprawdź dla każdego checkpointu w run'ie:

- czy plik istnieje i jest poprawnym YAML,
- czy `run_id` w checkpoincie zgadza się z `run_id` w manifeście,
- czy `pola_stacji.<stacja>` zawiera wszystkie pola z kontraktu wyjścia stacji,
- czy `stacja_poprzednia` w checkpoincie odpowiada stacji poprzedzającej w manifeście,
- czy sekcja `relacje` w kopercie jest niepusta (dla stacji merytorycznych poza `inicjuj`).

### 2. Spójność grafu stacji

Sprawdź przez Cypher:

- czy każda stacja (poza `inicjuj`) ma relację `NASTAPILA_PO` do stacji poprzedniej,
- czy liczba relacji `NASTAPILA_PO` = liczba stacji - 1,
- czy nie ma stacji bez `ZAWIERA` od `Run`,
- czy nie ma stacji `zakonczona` bez `ZAPISANA_W` do `Checkpoint`.

### 3. Osierocone węzły

Sprawdź przez Cypher:

- czy nie ma węzłów (poza `Run`) bez `WYPRODUKOWALA` od `Stacja`,
- czy nie ma węzłów bez `ZAWIERA` od `Run`,
- czy nie ma `Werdykt` bez `DOTYCZY` do `Twierdzenie`,
- czy nie ma `KrokPlanu` bez `ROZWIĄZUJE` do `Podproblem` (w ścieżce `dogłębny`),
- czy nie ma `Zmiana` bez `REALIZUJE` do `KrokPlanu`.

### 4. Spójność między checkpointami a grafem

Sprawdź:

- czy liczba stacji w manifeście = liczba węzłów `Stacja` w grafie,
- czy każda stacja `zakonczona` w manifeście ma odpowiadający węzeł `Stacja` w grafie,
- czy `checkpoint_file` w manifeście = `checkpoint_file` w węźle `Checkpoint` w grafie,
- czy encje w `pola_stacji` w checkpointach mają odpowiadające węzły w grafie.

### 5. Reguły integralności grafu

Sprawdź wszystkie 10 reguł integralności z `_shared/graf-pipeline.md`:

1. Każdy `Run` ma co najmniej jedną stację (`ZAWIERA`).
2. Każda `Stacja` (poza `inicjuj`) ma `NASTAPILA_PO`.
3. Każda `Stacja` ma `ZAPISANA_W` do `Checkpoint` (poza `pominieta`).
4. Każda encja ma `WYPRODUKOWALA` od `Stacja`.
5. Każdy `Werdykt` ma `DOTYCZY` do `Twierdzenie`.
6. Każdy `KrokPlanu` ma `ROZWIĄZUJE` do `Podproblem` (w `dogłębny`).
7. Każda `Zmiana` ma `REALIZUJE` do `KrokPlanu`.
8. Brak osieroconych węzłów.
9. Ciągłość `NASTAPILA_PO` (liczba relacji = liczba stacji - 1).
10. `run_id` spójny we wszystkich węzłach.

### 6. Relacje między runami

Sprawdź:

- czy run ma relacje `KONTYNUACJA` / `NAPRAWIA` / `PONOWNE_URUCHOMIENIE` do innych run'ów, jeśli zgłoszono to w manifeście,
- czy runy powiązane istnieją w `.ai-kb/pipeline-runs/`,
- czy relacje między runami są symetryczne (jeśli A `KONTYNUACJA` B, to B nie powinno `KONTYNUACJA` A).

### 7. Wykrywanie anomalii automatyczne

Wykryj i zgłoś:

- stacje bez poprzednika (poza `inicjuj`),
- zmienne oznaczone jako `hypothesis` użyte w `Decyzja` bez `OPARTA_NA`,
- twierdzenia `potwierdzony` oparte na `Zmienna` z `source_type: hypothesis`,
- decyzje bez `uzasadnienie`,
- werdykty `niezweryfikowany` bez wskazania braku źródeł,
- wnioski `ewaluacja` bez `WYPROWADZONY_Z` do `Stacja`,
- zmiany `zablokowane` bez wskazania powodu blokady.

## Instrukcja główna

Najpierw odczytaj manifest i zidentyfikuj wszystkie stacje w run'ie. Następnie wykonaj wymiary audytu sekwencyjnie.

W trybie `dogłębny` wykonaj dodatkowo:

- porównanie per-pole między checkpointami a węzłami grafu,
- analizę przyczyn każdej anomalii (czy to błąd zapisu, błąd modelu, błąd infrastruktury),
- rekomendacje naprawcze dla każdej anomalii.

---

Audyt run'u: [RUN_ID]

## Odczyt manifestu

Odczytaj `manifest.yaml` i wypisz wszystkie stacje z statusami.

## Audyt integralności checkpointów

Dla każdego checkpointu wykonaj walidację i wypisz wynik w tabeli:

| Checkpoint           | YAML poprawny | run_id zgodny | Pola wymagane | Stan ciągły | Relacje obecne | Status             |
| -------------------- | ------------- | ------------- | ------------- | ------------- | -------------- | ------------------ |
| stan_00_inicjuj.yaml | tak/nie       | tak/nie       | tak/nie       | tak/nie       | n/d            | spójny/niespójny |
| ...                  | ...           | ...           | ...           | ...           | ...            | ...                |

## Audyt spójności grafu

Wykonaj zapytania Cypher z `_shared/graf-pipeline.md` i wypisz wyniki:

- liczba stacji w grafie vs manifeście,
- liczba relacji `NASTAPILA_PO`,
- status spójności grafu.

## Audyt osieroconych węzłów

Wypisz wszystkie osierocone węzły wykryte przez Cypher.

## Audyt spójności checkpointy vs graf

Wypisz rozbieżności między checkpointami plikowymi a grafem Memgraph.

## Audyt reguł integralności

Wypisz naruszenia każdej z 10 reguł integralności.

## Audyt relacji między runami

Wypisz relacje między runami i sprawdź ich spójność.

## Wykryte anomalie

Wypisz wszystkie anomalie w tabeli:

| ID anomalii | Typ                | Węzeł/stacja | Opis                      | Wpływ | Rekomendacja naprawcza                     |
| ----------- | ------------------ | -------------- | ------------------------- | ------ | ------------------------------------------ |
| A1          | osierocony_węzeł | zmienna:V005   | Zmienna bez WYPRODUKOWALA | niska  | sprawdź czy stacja zmienne zapisała graf |

## Wynik

```yaml
run_id: ""
tryb_audytu: szybki | pełny | dogłębny
wymiary_audytu:
  integralnosc_checkpointow: spójny | niespójny
  spojnosc_grafu: spójny | niespójny
  osierocone_wezly: []           # lista osieroconych węzłów
  spojnosc_checkpointy_graf: spójny | niespójny
  reguly_integralnosci:          # naruszenia per reguła
    - regula: 1
      naruszona: false
      opis: ""
  relacje_miedzy_runami: spójny | niespójny
  anomalie: []                   # lista anomalii
ocena_calkowita: spójny | niespójny | ograniczony
liczba_anomalii: 0
status: zakonczony | ograniczony | niemozliwy
rekomendacje: []
```

### Statusy audytu

- `spójny` - brak anomalii, wszystkie reguły integralności spełnione.
- `niespójny` - wykryto anomalie albo naruszono reguły integralności.
- `ograniczony` - Memgraph niedostępny, audyt wykonany tylko na checkpointach plikowych.
- `niemozliwy` - manifest uszkodzony albo run nie istnieje.
