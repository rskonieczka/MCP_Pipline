---
name: utrwal
description: Zapisuje wnioski, decyzje, wzorce i pułapki do bazy wiedzy projektu i pamięci Serena po zakończeniu zadania.
version: 1.0.0
argument-hint: "[WNIOSKI LUB DECYZJE DO ZAPISANIA] [opcjonalnie: TYP WIEDZY, CEL, ŹRÓDŁA]"
triggers:
  - user
  - model
---

# Workflow utrwalania wiedzy projektu

Celem workflowu jest zapisanie wniosków, decyzji, wzorców i pułapek do bazy wiedzy projektu (`.ai-kb`) i pamięci Serena po zakończeniu zadania, aby uniknąć powtarzania kontekstu w przyszłych sesjach.

Utrwalanie odpowiada na pytanie "co zapisać, gdzie i w jakiej formie?", a nie "jak ocenić rozwiązanie?" (to `ewaluacja`) ani "jak monitorować?" (to `monitoruj`).

## Rola

Przyjmij rolę eksperta od zarządzania wiedzą projektu, łączącego myślenie systemowe, sekwencyjne i krytyczne.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- zapisać decyzję architektoniczną z uzasadnieniem,
- utrwalić preferencję techniczną albo konwencję,
- zapisać znany błąd albo obejście,
- zapisać kamień milowy projektu,
- zaktualizować bazę wiedzy po zakończeniu zadania,
- zapisać wzorzec albo antywzorzec.

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce ocenić rozwiązanie - użyj skilla `ewaluacja`,
- użytkownik chce monitorować postęp - użyj skilla `monitoruj`,
- brak wniosków do zapisania,
- wiedza jest tymczasowa albo nie ma wartości dla przyszłych sesji.

## Język

Utrwalanie prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `WNIOSKI LUB DECYZJE DO ZAPISANIA` - co ma zostać utrwalone.

Opcjonalnie:

- `TYP WIEDZY` - `decyzja`, `preferencja`, `błąd`, `wzorzec`, `kamień_milowy`, `pułapka`, `zależność`,
- `CEL` - dlaczego ta wiedza jest ważna,
- `ŹRÓDŁA` - materiały bazowe,
- `TRYB UTRWALANIA` - `szybki`, `pełny` (domyślnie `pełny`).

## Kontrola kompletności wejścia

1. Jeśli brakuje `WNIOSKI LUB DECYZJE DO ZAPISANIA`, poproś o wskazanie.
2. Jeśli `TYP WIEDZY` nie jest wskazany, wnioskuj z treści.
3. Jeśli wiedza jest niepełna, uzupełnij z kontekstu i oznacz jako `agent_inference`.

## Tryby utrwalania

- `szybki` - zapis do `.ai-kb` z minimalnym uzasadnieniem.
- `pełny` - domyślny: zapis z uzasadnieniem, źródłami, powiązaniami.

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

Najpierw rozpoznaj typ wiedzy. Nie zakładaj z góry, że każda wiedza zapisuje się tak samo.

Typy wiedzy do utrwalania:

- `decyzja` - dlaczego wybrano X zamiast Y,
- `preferencja` - styl kodowania, narzędzia, konwencje,
- `błąd` - znany błąd i obejście,
- `wzorzec` - wzorzec projektowy albo procesowy,
- `kamień_milowy` - kluczowy etap projektu,
- `pułapka` - pułapka oceny albo użycia,
- `zależność` - zależność technologiczna albo organizacyjna.

Miejsca zapisu:

- `.ai-kb/` - dokumentacja projektu,
- pamięć Serena - `write_memory` / `edit_memory`,
- Memgraph - graf powiązań pipeline'u (obowiązkowo w trybie `pełny`/`dogłębny` w kontekście pipeline'u).

Zasady:

- Najpierw sprawdź, czy wiedza już istnieje (`list_memories`, odczyt `.ai-kb`).
- Preferuj `edit before duplicate`.
- Nie zapisuj sekretów, kluczy ani danych wrażliwych.
- Każdy wpis musi mieć datę, źródło i uzasadnienie.
- W kontekście pipeline'u (gdy istnieje `run_id` w kopercie) zapis do Memgraph jest obowiązkowy, nie opcjonalny.

## Graf powiązań w Memgraph

`utrwal` ma dodatkową rolę w pipeline'u: zapis grafu powiązań do Memgraph po każdej stacji. Pełny schemat węzłów, krawędzi, mapowanie koperty na graf i wzorcowe zapytania Cypher: patrz `_shared/graf-pipeline.md`.

### Zapis po stacji

Po zapisie checkpointu (patrz sekcja "Checkpoint po stacji" niżej), `utrwal` zapisuje węzły i krawędzie do Memgraph na podstawie koperty:

1. **Węzeł `Stacja`** - dla stacji bieżącej, z `run_id`, `nazwa`, `status`, `timestamp`, `checkpoint_file`.
2. **Krawędź `ZAWIERA`** - od `Run` do `Stacja` (jeśli `Run` jeszcze nie istnieje, utwórz go z `run_id`, `zamiar`, `sciezka`, `timestamp_start`).
3. **Krawędź `NASTAPILA_PO`** - od `Stacja` bieżącej do `Stacja` poprzedniej (z `stacja_poprzednia` w kopercie).
4. **Krawędź `ZAPISANA_W`** - od `Stacja` do `Checkpoint` (z `checkpoint_file`, `yaml_poprawny`, `timestamp`).
5. **Węzły encji** - dla każdej encji wyprodukowanej przez stację (zgodnie z mapowaniem w `_shared/graf-pipeline.md`):
   - `zmienne` -> węzły `Zmienna` (per zmienna z `pola_stacji.zmienne.variables[]`),
   - `dekompozycja` -> węzły `Podproblem` (per podproblem),
   - `dobierz` -> węzeł `Decyzja` (rekomendacja),
   - `planuj` -> węzły `KrokPlanu` (per krok planu),
   - `realizuj` -> węzły `Zmiana` (per zmiana),
   - `weryfikacja` -> węzły `Twierdzenie` + `Werdykt` (per twierdzenie i werdykt),
   - `sprawdzenie` -> węzły `WymiarAudytu` (per wymiar),
   - `ewaluacja` -> węzły `Wniosek` (per wniosek).
6. **Krawędź `WYPRODUKOWALA`** - od `Stacja` do każdej encji.
7. **Krawędzie relacyjne** - na podstawie sekcji `relacje` w kopercie (`ZALEZY_OD`, `OPARTA_NA`, `DOTYCZY`, `ROZWIĄZUJE`, `REALIZUJE`, `WERYFIKUJE`, `WYPROWADZONY_Z`).

### Walidacja po checkpoincie

Po zapisie checkpointu i zapisie do Memgraph, `utrwal` wykonuje zapytanie weryfikujące ciągłość grafu:

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja {nazwa: $stacja})
MATCH (s)-[:NASTAPILA_PO]->(s_prev:Stacja)
RETURN s_prev.nazwa AS poprzednia, s.nazwa AS aktualna, s_prev.status AS status_poprzedniej
```

Jeśli `s_prev.status` != `zakonczona`, zgłoś anomalię: stacja bieżąca nastąpiła po stacji niezakończonej. Jeśli `s_prev` nie istnieje (poza `inicjuj`), zgłoś anomalię: stacja bez poprzednika.

### Zapis końcowy run'u

Po zakończeniu run'u:

1. Zapisz wnioski z całego pipeline'u do `.ai-kb/` i pamięci Serena (zgodnie z instrukcją główną).
2. Zapisz kopertę końcową do `stan_<NN>_utrwal.yaml`.
3. Zaktualizuj `manifest.yaml` - wszystkie stacje `zakonczona`, `iteracja_bramki` ostateczna.
4. Zaktualizuj węzeł `Run` w Memgraph - `timestamp_end`, `status: zakonczony`.
5. Jeśli run jest kontynuacją, naprawą albo ponownym uruchomieniem innego run'u, zapisz relację `KONTYNUACJA` / `NAPRAWIA` / `PONOWNE_URUCHOMIENIE` do Memgraph.

### Kompresja kontekstu

W ścieżce `dogłębny`, po zapisie checkpointu i zapisie do Memgraph dla stacji starszych niż 3 wstecz, usuń ich sekcje `pola_stacji` z koperty w kontekście konwersacji. Pozostaw tylko `stan` i sekcje 3 ostatnich stacji. Pełne dane pozostają w plikach checkpointów i w grafie Memgraph.

## Dodatkowa odpowiedzialność: checkpointowanie i graf stacji

`utrwal` ma dodatkową rolę w pipeline'u: zapis checkpointu i grafu powiązań po każdej stacji merytorycznej (nie tylko na końcu pipeline'u). Ta funkcja jest aktywowana tylko w kontekście pipeline'u (gdy istnieje aktywny `run_id` w kopercie).

### Checkpoint po stacji

Po zakończeniu dowolnej stacji merytorycznej (nie `utrwal` samej w sobie), jeśli pipeline jest aktywny:

1. Odczytaj `run_id` z koperty.
2. Zapisz kopertę do `.ai-kb/pipeline-runs/<run_id>/stan_<NN>_<stacja>.yaml`, gdzie `<NN>` to numer stacji z manifestu.
3. Zaktualizuj `manifest.yaml`:
   - ustaw status stacji na `zakonczona`,
   - wpisz timestamp zakończenia,
   - wpisz nazwę pliku checkpointu.
4. Zapisz węzły i krawędzie do Memgraph (patrz sekcja "Graf powiązań w Memgraph" powyżej).
5. Wykonaj walidację ciągłości grafu (patrz "Walidacja po checkpoincie" powyżej).

### Zapis końcowy pipeline'u

Po zakończeniu pipeline'u (ostatnia stacja przed `utrwal` albo sama stacja `utrwal`):

1. Zapisz wnioski z całego pipeline'u do `.ai-kb/` i pamięci Serena (zgodnie z instrukcją główną).
2. Zapisz kopertę końcową do `stan_<NN>_utrwal.yaml`.
3. Zaktualizuj `manifest.yaml` - wszystkie stacje `zakonczona`, `iteracja_bramki` ostateczna.
4. Zaktualizuj węzeł `Run` w Memgraph i zapisz relacje między runami (patrz "Zapis końcowy run'u" w sekcji "Graf powiązań w Memgraph").

Kompresja kontekstu: patrz sekcja "Kompresja kontekstu" w "Graf powiązań w Memgraph" powyżej.

---

Utrwalanie: [WNIOSKI LUB DECYZJE DO ZAPISANIA]

## Rozpoznanie typu wiedzy

Określ typ wiedzy i uzasadnij.

## Sprawdzenie istniejącej wiedzy

Sprawdź, czy podobna wiedza już istnieje w `.ai-kb` albo pamięci Serena.

## Zapis

Wskaż miejsce zapisu, treść i uzasadnienie.

| Wiedza | Miejsce | Akcja | Uzasadnienie |
| --- | --- | --- | --- |
| ... | .ai-kb/decyzje.md | dodaj / edytuj | ... |

## Wynik

```yaml
typ_wiedzy: decyzja | preferencja | blad | wzorzec | kamien_milowy | pulapka | zaleznosc
miejsca_zapisu: []
akcje: []
status: zapisany | zaktualizowany | pominiety
checkpoint_zapisany: true | false
manifest_zaktualizowany: true | false
graf_zapisany: true | false         # czy węzły i krawędzie zapisane do Memgraph
walidacja_grafu: spójny | niespójny  # wynik walidacji ciągłości grafu po checkpoincie
anomalie: []                        # lista anomalii wykrytych przez walidację
```
