---
name: monitoruj
description: Śledzi postęp, blokady, zależności i odchylenia od planu w zadaniach wieloetapowych, raportuje checkpointy i warunki przejścia.
version: 1.0.0
argument-hint: "[ZADANIE LUB PLAN] [opcjonalnie: CHECKPOINTY, METRYKI, TRYB]"
triggers:
  - user
  - model
---

# Workflow monitorowania postępu

Celem workflowu jest śledzenie postępu wieloetapowego zadania albo projektu, sygnalizowanie checkpointów, blokad, zależności i odchyleń od planu, oraz informowanie o warunkach przejścia do kolejnych etapów.

Monitorowanie odpowiada na pytanie "gdzie jesteśmy względem planu i co blokuje przejście dalej?", a nie "jak zaplanować?" (to `planuj`) ani "jak ocenić ex-post?" (to `ewaluacja`).

## Rola

Przyjmij rolę eksperta od monitorowania projektów i zadań wieloetapowych, łączącego myślenie systemowe, sekwencyjne i krytyczne.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- śledzić postęp wieloetapowego zadania,
- sprawdzić, czy checkpointy zostały osiągnięte,
- zidentyfikować blokady i zależności,
- zgłosić odchylenia od planu,
- ustalić, czego brakuje do przejścia do kolejnego etapu,
- raportować status projektu.

## Kiedy nie stosować

Nie stosuj, gdy:

- zadanie jest jednorazowe i nie wymaga monitorowania,
- użytkownik chce zaplanować zadanie - użyj skilla `planuj`,
- użytkownik chce ocenić rozwiązanie ex-post - użyj skilla `ewaluacja`,
- użytkownik chce utrwalić wnioski - użyj skilla `utrwal`.

## Język

Monitorowanie prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `ZADANIE LUB PLAN` - co jest monitorowane.

Opcjonalnie:

- `CHECKPOINTY` - punkty kontrolne do sprawdzenia,
- `METRYKI` - wskaźniki postępu,
- `ŹRÓDŁA` - dane o postępie,
- `TRYB MONITOROWANIA` - `szybki`, `pełny` (domyślnie `pełny`).

## Kontrola kompletności wejścia

1. Jeśli brakuje `ZADANIE LUB PLAN`, poproś o wskazanie.
2. Jeśli brakuje checkpointów, wnioskuj z planu i oznacz jako `agent_inference`.
3. Jeśli brakuje danych o postępie, ustaw status `ograniczony`.

## Tryby monitorowania

- `szybki` - status głównych checkpointów + blokady.
- `pełny` - domyślny: wszystkie checkpointy, blokady, zależności, odchylenia, warunki przejścia.

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

Najpierw rozpoznaj, co jest monitorowane. Nie zakładaj z góry, że każde monitorowanie ma tę samą strukturę.

Możliwe typy monitorowania:

- `checkpointowy` - sprawdzanie punktów kontrolnych,
- `metryczny` - śledzenie wskaźników postępu,
- `blokad` - identyfikacja blokad i zależności,
- `odchyleń` - porównanie stanu faktycznego z planem.

Po rozpoznaniu typu dostosuj zakres.

Zasady:

- Raportuj jawnie: osiągnięte / nieosiągnięte / zablokowane / w toku.
- Wskaż, czego brakuje do przejścia do kolejnego etapu.
- Sygnalizuj odchylenia od planu z oceną wpływu.
- Nie maskuj blokad.

## Restart pipeline'u z manifestu

`monitoruj` ma dodatkową rolę w pipeline'u: odczyt manifestu, walidacja integralności checkpointów, weryfikacja grafu i raportowanie statusu restartu. Ta funkcja jest aktywowana, gdy użytkownik chce wznowić przerwany pipeline.

### Procedura restartu

1. Odczytaj `manifest.yaml` z `.ai-kb/pipeline-runs/<run_id>/`.
2. Zidentyfikuj ostatnią stację ze statusem `zakonczona`.
3. Odczytaj jej checkpoint (`stan_<NN>_<stacja>.yaml`).
4. Zweryfikuj integralność checkpointu (patrz "Walidacja integralności checkpointu" niżej).
5. Zweryfikuj spójność grafu w Memgraph (patrz "Weryfikacja grafu przez Cypher" niżej).
6. Odtwórz kopertę z checkpointu.
7. Raportuj:
   - które stacje są `zakonczona`,
   - która stacja jest `w_trakcie` albo `zablokowana`,
   - jaka jest `iteracja_bramki`,
   - od której stacji kontynuować,
   - czy checkpointy są spójne,
   - czy graf jest spójny,
   - jakie anomalie wykryto.
8. Jeśli istnieje stacja `zablokowana`, wskaż powód blokady z poprzedniego przebiegu.

### Walidacja integralności checkpointu

Dla każdego checkpointu odczytanego przy restarcie sprawdź:

```yaml
WALIDACJA_CHECKPOINTU:
  plik: stan_02_analiza.yaml
  yaml_poprawny: true              # czy plik jest poprawnym YAML
  run_id_zgodny: true              # czy run_id w checkpoincie = run_id w manifeście
  pola_wymagane_obecne: true       # czy pola_stacji.<stacja> ma wszystkie pola kontraktu
  stan_ciagly: true                # czy stacja_poprzednia = ostatnia zakonczona w manifeście
  relacje_obecne: true             # czy sekcja relacje w kopercie jest niepusta
  status: spójny | niespójny
  bledy: []                        # lista błędów, jeśli status niespójny
```

Kroki walidacji:

1. **YAML poprawny** - odczytaj plik checkpointu i sprawdź czy jest poprawnym YAML.
2. **run_id zgodny** - porównaj `run_id` w checkpoincie z `run_id` w manifeście.
3. **Pola wymagane obecne** - sprawdź czy `pola_stacji.<stacja>` zawiera wszystkie pola z kontraktu wyjścia stacji (patrz `kontrakty_pipelines.md`).
4. **Stan ciągły** - sprawdź czy `stacja_poprzednia` w checkpoincie odpowiada ostatniej stacji `zakonczona` w manifeście przed stacją bieżącą.
5. **Relacje obecne** - sprawdź czy sekcja `relacje` w kopercie jest niepusta (dla stacji merytorycznych poza `inicjuj`).

### Weryfikacja grafu przez Cypher

Po walidacji checkpointów wykonaj zapytania Cypher w Memgraph weryfikujące spójność grafu run'u:

**Ciągłość stacji:**

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja)
OPTIONAL MATCH (s)-[:NASTAPILA_PO]->(s_prev:Stacja)
WHERE s.nazwa <> 'inicjuj' AND s_prev IS NULL
RETURN s.nazwa AS stacja_bez_poprzednika
```

**Osierocone węzły:**

```cypher
MATCH (n) WHERE n.run_id = $run_id
AND NOT ()-[:WYPRODUKOWALA]->(n)
AND NOT ()-[:ZAWIERA]->(n)
AND labels(n) <> ['Run']
RETURN labels(n) AS typ_wezla, n
```

**Spójność grafu:**

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja)
WITH r, count(s) AS liczba_stacji
MATCH (r)-[:ZAWIERA]->(s2:Stacja)-[:NASTAPILA_PO]->(s3:Stacja)
WITH r, liczba_stacji, count(s2) AS liczba_relacji
RETURN r.run_id, liczba_stacji, liczba_relacji,
       CASE WHEN liczba_relacji = liczba_stacji - 1 THEN 'spójny' ELSE 'niespójny' END AS status
```

Pełny zestaw zapytań wzorcowych: patrz `_shared/graf-pipeline.md`.

### Raport restartu

```yaml
restart:
  run_id: ""
  ostatnia_zakonczona: <stacja>
  stacja_w_trakcie: <stacja> | null
  stacja_zablokowana: <stacja> | null
  iteracja_bramki: 0
  kontynuuj_od: <stacja_nastepna>
  powod_blokady: ""
  walidacja_checkpointow: spójny | niespójny
  walidacja_grafu: spójny | niespójny
  anomalie: []                    # lista anomalii wykrytych przez walidację
```

---

Monitorowanie: [ZADANIE LUB PLAN]

## Rozpoznanie typu monitorowania

Określ typ i uzasadnij.

## Status checkpointów

| Checkpoint | Status | Uwagi |
| --- | --- | --- |
| ... | osiągnięty / nieosiągnięty / zablokowany / w toku | ... |

## Blokady i zależności

Wskaż blokady i zależności blokujące przejście.

## Odchylenia od planu

| Plan | Stan faktyczny | Odchylenie | Wpływ |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## Warunki przejścia

Wskaż, czego brakuje do przejścia do kolejnego etapu.

## Wynik

```yaml
checkpointy: {}
blokady: []
odchylenia: []
warunki_przejscia: []
status: w_toku | zablokowany | zakonczony | odchylony
restart:                              # tylko przy restarcie z manifestu
  ostatnia_zakonczona: ""
  kontynuuj_od: ""
  iteracja_bramki: 0
  walidacja_checkpointow: spójny | niespójny
  walidacja_grafu: spójny | niespójny
  anomalie: []
```
