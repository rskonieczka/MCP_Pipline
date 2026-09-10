---
name: inicjuj-run
description: Rozpoznaje, czy zamiar użytkownika wymaga uruchomienia pipeline'u, klasyfikuje go jako trywialne, rutynowe albo złożone i ustala punkt wejścia.
version: 1.0.0
argument-hint: "[ZAMIAR UŻYTKOWNIKA] [opcjonalnie: KONTEKST, ŹRÓDŁA]"
triggers:
  - user
  - model
---
# Workflow inicjacji i klasyfikacji zamiaru

Celem workflowu jest rozpoznanie, czy zamiar użytkownika wymaga pełnego pipeline'u umiejętności, czy wystarczy odpowiedź bezpośrednia, oraz ustalenie punktu wejścia do pipeline'u.

Inicjacja odpowiada na pytanie "czy to zadanie wymaga pipeline'u i od której stacji zacząć?", a nie "jak to zrobić?" albo "czym jest obiekt?".

## Rola

Przyjmij rolę eksperta od triage'u zadań i klasyfikacji roboczej, łączącego wieloletnią praktykę w ocenie złożoności, routingu zadań i zarządzaniu przepływem pracy.

## Kiedy stosować

Stosuj, gdy użytkownik:

- formułuje zamiar, który może być trywialny albo złożony,
- chce wiedzieć, czy uruchomić pełny proces, czy odpowiedzieć bezpośrednio,
- potrzebuje klasyfikacji zadania przed wejściem w pipeline,
- chce ustalić, od której stacji pipeline'u zacząć.

## Kiedy nie stosować

Nie stosuj, gdy:

- zamiar jest już jednoznacznie złożony i wymaga pełnego pipeline'u - przejdź bezpośrednio do `zmienne`,
- użytkownik chce przeanalizować obiekt - użyj skilla `analiza`,
- użytkownik chce zaplanować realizację - użyj skilla `planuj`,
- użytkownik chce dokonać doboru wariantu - użyj skilla `dobierz`.

## Język

Inicjację prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `ZAMIAR UŻYTKOWNIKA` - sformułowanie intencji.

Opcjonalnie:

- `KONTEKST` - środowisko, sytuacja, ograniczenia,
- `ŹRÓDŁA` - materiały bazowe,
- `TRYB INICJACJI` - `szybki`, `pełny` (domyślnie `pełny`).

## Kontrola kompletności wejścia

1. Jeśli brakuje `ZAMIARU UŻYTKOWNIKA`, poproś o sformułowanie intencji.
2. Jeśli zamiar jest niejednoznaczny, poproś o doprecyzowanie.
3. Jeśli kontekst jest niepełny, wnioskuj z dostępnych danych i oznacz jako `agent_inference`.

## Tryby inicjacji

- `szybki` - klasyfikacja trywialne/złożone + punkt wejścia, bez uzasadnienia.
- `pełny` - domyślny: klasyfikacja, uzasadnienie, punkt wejścia, ryzyka.

## Źródła prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pułapki.
2. Context7 - dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - notebooki i źródła badawcze użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zależności, graf wywołań.

Stosuj w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi. Konflikty źródeł, hierarchia i reguły uzupełniające: patrz `_shared/zrodla-i-narzedzia.md`.

## Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza architektury.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Instrukcja główna

Najpierw rozpoznaj, czym jest zamiar. Nie zakładaj z góry, że każde zadanie wymaga pipeline'u.

Możliwe klasyfikacje:

- `trywialne` - odpowiedź bezpośrednia, bez pipeline'u,
- `rutynowe` - pipeline od `zmienne`, bez dekompozycji i routingu,
- `złożone` - pełny pipeline od `zmienne` przez wszystkie stacje.

Kryteria klasyfikacji:

| Kryterium                      | Trywialne | Rutynowe | Złożone |
| ------------------------------ | --------- | -------- | --------- |
| Liczba podproblemów           | 1         | 1-2      | 3+        |
| Stawka decyzyjna               | niska     | średnia | wysoka    |
| Wymaga źródeł zewnętrznych | nie       | tak      | tak       |
| Wymaga weryfikacji             | nie       | tak      | tak       |
| Wymaga dekompozycji            | nie       | nie      | tak       |
| Wymaga ewaluacji ex-post       | nie       | nie      | tak       |

Po klasyfikacji ustal punkt wejścia:

- `trywialne` -> odpowiedź bezpośrednia,
- `rutynowe` -> `zmienne`,
- `złożone` -> `zmienne` (pełny pipeline).

## Inicjacja run'u pipeline'u

`inicjuj` jest stacją zerową i ma dodatkową odpowiedzialność: tworzy infrastrukturę run'u pipeline'u. Pełna specyfikacja mechanizmu wymiany danych: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Tworzenie katalogu run

Jeśli klasyfikacja to `rutynowe` albo `złożone` (czyli pipeline zostaje uruchomiony):

1. Wygeneruj `run_id` w formacie `<YYYY-MM-DD>-<skrot-zamiaru>` (np. `2026-06-29-weryfikacja-mechanizmu`).
2. Utwórz katalog `.ai-kb/clients/<client_id>/pipeline-runs/<run_id>/` (tryb legacy bez `client_id`: `.ai-kb/pipeline-runs/<run_id>/`).
3. Utwórz plik `manifest.yaml` z pustym stanem stacji:

```yaml
MANIFEST:
  run_id: "<run_id>"
  zamiar: "<ZAMIAR UŻYTKOWNIKA>"
  sciezka: szybki | pelny | doglebny   # ustal na podstawie klasyfikacji
  iteracja_bramki: 0
  stacje:
    - stacja: inicjuj
      status: w_trakcie
      timestamp: "<ISO-8601>"
      checkpoint: stan_00_inicjuj.yaml
    # dalsze stacje dodawane w trakcie pipeline'u
```

4. Po zakończeniu `inicjuj` zapisz kopertę do `stan_00_inicjuj.yaml` i zaktualizuj manifest (status `zakonczona`).

### Emitowanie koperty

`inicjuj` emituje pierwszą kopertę pipeline'u. `stacja_poprzednia` ma wartość `null`. `stan.zamiar` przyjmuje wartość `ZAMIAR UŻYTKOWNIKA`. `pola_stacji.inicjuj` zawiera pola wyjściowe stacji.

---

Inicjacja: [ZAMIAR UŻYTKOWNIKA]

## Rozpoznanie zamiaru

Sparafrazuj zamiar i określ jego cel główny.

## Klasyfikacja

Określ klasę zamiaru (`trywialne` / `rutynowe` / `złożone`) i uzasadnij odwołując się do kryteriów.

## Punkt wejścia

Wskaż stację pipeline'u, od której należy zacząć, albo `odpowiedź bezpośrednia`.

## Ryzyka

Wskaż ryzyka błędnego rozpoznania i warunki rewizji klasyfikacji.

## Wynik

```yaml
klasyfikacja: trywialne | rutynowe | złożone
punkt_wejscia: odpowiedź_bezpośrednia | zmienne | analiza | dobierz
uzasadnienie: ""
ryzyka: []
```

### Koperta (gdy klasyfikacja rutynowe/złożone)

```yaml
KOPERTA:
  run_id: "<YYYY-MM-DD>-<skrot-zamiaru>"
  sciezka: szybki | pelny | doglebny
  stacja_aktualna: inicjuj
  stacja_poprzednia: null
  stan:
    zamiar: "<ZAMIAR UŻYTKOWNIKA>"
    klasyfikacja: ""
    punkt_wejscia: ""
  pola_stacji:
    inicjuj:
      klasyfikacja: ""
      punkt_wejscia: ""
      uzasadnienie: ""
      ryzyka: []
  walidacja:
    stacja_docelowa: zmienne
    pola_wymagane: [task_goal]
    pola_obecne: [stan.zamiar]
    pola_brakujace: []
    status: gotowy
    akcja_naprawcza: ""
  relacje:
    - zrodlo: "stacja:<client_id>:<run_id>:inicjuj"
      cel: "stacja:<client_id>:<run_id>:zmienne"
      typ: nastapila_po
    - zrodlo: "run:<client_id>:<run_id>"
      cel: "stacja:<client_id>:<run_id>:inicjuj"
      typ: zawiera
    # Node IDs w trybie legacy (brak client_id) nie zawierają prefiksu client_id (np. run:<run_id> zamiast run:<client_id>:<run_id>).
```

Po wyemitowaniu koperty zapisz ją do `.ai-kb/clients/<client_id>/pipeline-runs/<run_id>/stan_00_inicjuj.yaml` (tryb legacy bez `client_id`: `.ai-kb/pipeline-runs/<run_id>/`) i zaktualizuj `manifest.yaml` (status `zakonczona`, timestamp). `utrwal` zapisze węzły i krawędzie do Memgraph na podstawie sekcji `relacje`.
