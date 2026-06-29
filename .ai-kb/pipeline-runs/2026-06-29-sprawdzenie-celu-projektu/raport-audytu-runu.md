# Raport audytu run'u pipeline'u

**Run ID:** `2026-06-29-sprawdzenie-celu-projektu`
**Audytowana ścieżka:** doglebny (13 stacji)
**Data audytu:** 2026-06-29 20:08:00
**Tryb audytu:** pełny
**Status audytu:** zakonczony_z_anomaliami

---

## Werdykt

**Ocena całkowita: 65/100**

Run zakończony sukcesem merytorycznym (cel audytu osiągnięty, 13/13 stacji wykonanych, bramka jakości zgodna), ale wykryto **7 anomalii** w warstwie persystencji grafowej i kompresji koperty. Anomalie nie podważają wyniku merytorycznego run'u, ale wskazują na defekty implementacyjne serwera w integracji z Memgraph.

---

## 1. Odczyt manifestu

| Pole | Wartość |
| --- | --- |
| run_id | `2026-06-29-sprawdzenie-celu-projektu` |
| zamiar | Sprawdzenie celu projektu Pipeline MCP Server, którym jest orkiestracja agentów AI w pętli pipeline |
| sciezka | doglebny |
| iteracja_bramki | 0 |
| status_runu | zakonczony |
| timestamp_start | 2026-06-29T19:54:55 |
| timestamp_end | 2026-06-29T20:04:10 |
| liczba stacji | 13 |
| wszystkie stacje zakonczona | TAK |

---

## 2. Integralność checkpointów

| Checkpoint | YAML poprawny | run_id zgodny | Pola wymagane | Stan ciągły | Relacje obecne | Status |
| --- | --- | --- | --- | --- | --- | --- |
| stan_inicjuj.yaml | TAK | TAK | TAK | TAK | TAK | SPOJNY |
| stan_zmienne.yaml | TAK | TAK | TAK | TAK | TAK | SPOJNY |
| stan_analiza.yaml | TAK | TAK | TAK | TAK | TAK | SPOJNY |
| stan_dekompozycja.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_dobierz.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_routing.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_planuj.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_realizuj.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_weryfikacja.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_sprawdzenie.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_ewaluacja.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_utrwal.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |
| stan_monitoruj.yaml | TAK | TAK | TAK | **NIE** | TAK | NIESPOJNY |

**Wynik:** 3/13 spojne, 10/13 niespojne (anomalia A5 - `stacja_poprzednia` we wszystkich checkpointach poza inicjuj/analiza wynosi `'zmienne'` zamiast faktycznej stacji poprzedzającej).

**Liczba checkpointów:** 13 (zgodne z manifestem)
**envelope_final.yaml:** obecny

---

## 3. Spójność grafu Memgraph

### 3.1. Węzły w grafie dla run'u

| Typ węzła (oczekiwany) | Liczba w grafie | Status |
| --- | --- | --- |
| `:Run` z run_id | **0** | BRAK (A1) |
| `:Stacja` z run_id | **0** | BRAK (A1) |
| Generyczne węzły z polem `id` | 14 (1 run + 13 stacji) | BEZ LABELI (A2) |

### 3.2. Relacje w grafie dla run'u

| Typ relacji (oczekiwany) | Liczba w grafie | Status |
| --- | --- | --- |
| `ZAWIERA` (Run -> Stacja) | 36 (z duplikatami) | DUPLIKACJA (A3) |
| `NASTAPILA_PO` (Stacja -> Stacja) | **0** | BRAK (A4) |
| `ZAPISANA_W` (Stacja -> Checkpoint) | 0 | BRAK |
| `WYPRODUKOWALA` (Stacja -> encja) | 0 | BRAK |
| `DOTYCZY` (Werdykt -> Twierdzenie) | 0 | BRAK |
| `ROZWIĄZUJE` (KrokPlanu -> Podproblem) | 0 | BRAK |
| `REALIZUJE` (Zmiana -> KrokPlanu) | 0 | BRAK |

**Wynik:** Graf NIESPOJNY. Brak strukturalnych węzłów `:Run` i `:Stacja`. Brak relacji `NASTAPILA_PO`. Duplikacja relacji `ZAWIERA`.

### 3.3. Przyczyna anomalii grafowych

Analiza kodu `src/pipeline_mcp/server.py` i `src/pipeline_mcp/memgraph.py`:

- `write_run_node()` (memgraph.py:58) - **NIE WYWOŁYWANE** w server.py
- `write_station_node()` (memgraph.py:77) - **NIE WYWOŁYWANE** w server.py
- `write_relations_from_envelope()` (memgraph.py:121) - wywoływane w server.py:438
- `close_run_node()` (memgraph.py:135) - wywoływane w server.py:348, ale `MATCH (r:Run {run_id: $run_id})` nie znajduje węzła (bo `write_run_node` nie został wywołany)

`write_relations_from_envelope` używa `write_relation` które wykonuje `MERGE (a {id: $source})` - tworzy generyczne węzły z polem `id` **bez labeli**. To jest jedyna funkcja zapisu faktycznie wywoływana, stąd brak węzłów `:Run`/`:Stacja` z labelami.

---

## 4. Spójność checkpointy vs graf

| Aspekt | Manifest/checkpointy | Graf Memgraph | Zgodność |
| --- | --- | --- | --- |
| Liczba stacji | 13 | 0 węzłów `:Stacja` (13 generycznych bez labeli) | NIE |
| Węzeł Run | status: zakonczony | brak węzła `:Run` | NIE |
| Relacje NASTAPILA_PO | 12 (implikowane przez manifest) | 0 | NIE |
| Checkpointy | 13 plików YAML | brak węzłów `:Checkpoint` | NIE |

**Wynik:** NIESPOJNY. Graf nie odzwierciedla struktury run'u zapisanej w checkpointach.

---

## 5. Reguły integralności grafu

| Reguła | Naruszona | Opis |
| --- | --- | --- |
| 1. Każdy Run ma ZAWIERA do Stacja | TAK | Brak węzła `:Run` |
| 2. Każda Stacja (poza inicjuj) ma NASTAPILA_PO | TAK | Brak relacji NASTAPILA_PO |
| 3. Każda Stacja ma ZAPISANA_W do Checkpoint | TAK | Brak węzłów `:Stacja` i `:Checkpoint` |
| 4. Każda encja ma WYPRODUKOWALA od Stacja | TAK | Brak węzłów encji |
| 5. Każdy Werdykt ma DOTYCZY do Twierdzenie | TAK | Brak węzłów `:Werdykt` i `:Twierdzenie` |
| 6. Każdy KrokPlanu ma ROZWIĄZUJE do Podproblem | TAK | Brak węzłów `:KrokPlanu` i `:Podproblem` |
| 7. Każda Zmiana ma REALIZUJE do KrokPlanu | TAK | Brak węzłów `:Zmiana` z relacją |
| 8. Brak osieroconych węzłów | TAK | 14 generycznych węzłów bez labeli |
| 9. Ciągłość NASTAPILA_PO (liczba = stacje - 1) | TAK | 0 relacji (oczekiwane 12) |
| 10. run_id spójny we wszystkich węzłach | NIE | run_id obecny w generycznych węzłach |

**Wynik:** 9/10 reguł naruszonych. Tylko reguła 10 (spójność run_id) zachowana.

---

## 6. Relacje między runami

Brak relacji między runami (`KONTYNUACJA` / `NAPRAWIA` / `PONOWNE_URUCHOMIENIE`). Run samodzielny.

---

## 7. Wykryte anomalie

| ID | Typ | Węzeł/stacja | Opis | Wpływ |
| --- | --- | --- | --- | --- |
| A1 | brak_strukturalny | graf Memgraph | `write_run_node` i `write_station_node` zdefiniowane w memgraph.py ale NIE wywoływane w server.py. Tylko `write_relations_from_envelope` zapisuje generyczne węzły z polem `id` bez labeli. | krytyczny |
| A2 | brak_labeli | wszystkie węzły run'u | Wszystkie węzły w grafie dla tego run'u nie mają labeli (`labels: []`). Zamiast `:Run` i `:Stacja` są generycznymi węzłami z polem `id`. | wysoki |
| A3 | duplikacja_relacji | relacje ZAWIERA | 36 relacji ZAWIERA z duplikatami (stacja:inicjuj x12, stacja:zmienne x12). Wynika z kompresji koperty - każda stacja po kompresji ma te same relacje ZAWIERA. | średni |
| A4 | brak_relacji | relacje NASTAPILA_PO | Brak relacji NASTAPILA_PO między stacjami w grafie. Ciągłość stacji nie zapisana w grafie. | wysoki |
| A5 | anomalia_kompresji | checkpointy stan_dekompozycja..stan_monitoruj | `stacja_poprzednia` we wszystkich checkpointach poza inicjuj/analiza wynosi `'zmienne'` zamiast faktycznej stacji poprzedzającej. Wynik kompresji koperty w ścieżce doglebny (P5). | średni |
| A6 | false_positive | pole memgraph_written | Serwer raportował `memgraph_written: true` w każdej stacji, ale faktycznie zapisał tylko generyczne węzły relacji bez labeli. Wartość `true` nie odzwierciedla realnego stanu grafu strukturalnego. | wysoki |
| A7 | brak_efektu | close_run_node | `close_run_node` wywoływane w server.py:348, ale `MATCH (r:Run {run_id: $run_id})` nie znajduje węzła bo `write_run_node` nigdy nie został wywołany. Zamykanie run'u w grafie nieefektywne. | niski |
| A8 | brak_możliwości_audytu | execute_station | `audyt_runu` jako stacja audytowa ex-post powinna być wykonalna po zamknięciu run'u, ale `execute_station` blokuje rejestrację dla zamkniętych run'ów (`RunClosedError`). | średni |

---

## 8. Rekomendacje naprawcze

| Priorytet | Rekomendacja | Anomalia | Uzasadnienie |
| --- | --- | --- | --- |
| krytyczny | Dodać wywołanie `write_run_node` w `start_run` i `write_station_node` w `execute_station` przed `write_relations_from_envelope` | A1 | Brak strukturalnych węzłów Run/Stacja w grafie |
| wysoki | Naprawić `write_relation` aby nadawało labeli węzłom (`Run`, `Stacja`) na podstawie konwencji `id` (`run:*`, `stacja:*`) | A2 | Węzły bez labeli - zapytania Cypher po labelach nie działają |
| wysoki | Dodać relacje `NASTAPILA_PO` między stacjami w grafie na podstawie manifestu | A4 | Brak ciągułości stacji w grafie |
| wysoki | Raportować `memgraph_written: true` tylko gdy zapis strukturalnych węzłów (Run/Stacja) się powiódł, nie tylko relacji | A6 | False positive sygnału sukcesu |
| średni | Użyć `MERGE` zamiast `CREATE` dla relacji aby uniknąć duplikacji | A3 | Duplikacja relacji ZAWIERA |
| średni | Zachować `stacja_poprzednia` jako faktyczną stację poprzedzającą przy kompresji koperty | A5 | Anomalia kompresji w checkpointach |
| średni | Zezwolić na `execute_station` dla stacji `audyt_runu` po zamknięciu run'u | A8 | Audyt ex-post niemożliwy przez serwer |
| niski | `close_run_node` powinien tworzyć węzeł Run jeśli nie istnieje (MERGE zamiast MATCH) | A7 | Zamykanie run'u w grafie nieefektywne |

---

## 9. Wymiar merytoryczny vs warstwa techniczna

**Wynik merytoryczny run'u:** SUKCES
- Cel audytu osiągnięty: projekt realizuje cel orkiestracji agentów AI w pętli pipeline
- 13/13 stacji wykonanych, bramka jakości zgodna (ocena 95/100)
- 14 werdyktów weryfikacji potwierdzonych
- Raport audytu celu utworzony

**Warstwa techniczna run'u:** ANOMALIE
- 7 anomalii w persystencji grafowej i kompresji koperty
- Graf Memgraph niespójny (brak węzłów strukturalnych, brak relacji NASTAPILA_PO)
- Checkpointy z anomalią `stacja_poprzednia` (10/13 niespojne)
- `memgraph_written: true` to false positive

**Wniosek:** Anomalie techniczne nie podważają wyniku merytorycznego (cel audytu osiągnięty na podstawie kodu źródłowego i testów funkcjonalnych, nie na podstawie grafu). Wskazują jednak na defekty implementacyjne serwera w integracji z Memgraph, które należy naprawić.

---

## 10. Limitacje audytu

- `audyt_runu` nie mógł być zarejestrowany przez `execute_station` (run zamknięty - anomalia A8). Raport utworzony jako artefakt plikowy.
- Audyt grafu wykonany przez bezpośrednie zapytania Cypher (MCP memgraph), nie przez serwer pipeline'u.
- Pełne dane stacji merytorycznych dostępne w checkpointach plikowych (mimo anomalia A5, manifest zachowuje prawidłową kolejność stacji).

---

*Raport wygenerowany przez stację `audyt_runu` (tryb manual, artefakt plikowy) dla run'u `2026-06-29-sprawdzenie-celu-projektu`. Audyt grafu wykonany przez Memgraph MCP. Audyt checkpointów przez odczyt plików YAML.*
