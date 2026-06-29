# Współdzielone: Graf powiązań pipeline'u w Memgraph

Kanoniczna wersja schematu grafu dla pipeline'u umiejętności. Wszystkie skille zapisujące do Memgraph używają tego schematu. Aktualizacja schematu w tym pliku wystarczy do zsynchronizowania wszystkich skilli.

Źródło pipeline'u: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami" i "Graf powiązań w Memgraph").

## Cel grafu

Graf służy do:
- audytowalności relacyjnej run'u (która stacja wyprodukowała dane dla której),
- zapytań grafowych o pochodzenie decyzji, twierdzeń, werdyktów i wniosków,
- weryfikacji spójności run'u (czy graf jest spójny, czy nie ma osieroconych węzłów),
- śledzenia zależności między runami (kontynuacja, naprawa, ponowne uruchomienie),
- wykrywania anomalii (stacje bez poprzednika, zmienne bez źródła, decyzje bez uzasadnienia).

## Schemat węzłów

| Etykieta | Klucze | Wymagane właściwości | Opcjonalne właściwości | Opis |
| --- | --- | --- | --- | --- |
| `Run` | `run_id` | `zamiar`, `sciezka`, `timestamp_start` | `timestamp_end`, `status`, `iteracja_bramki` | Pojedyncze uruchomienie pipeline'u |
| `Stacja` | `run_id`, `nazwa` | `status`, `timestamp`, `checkpoint_file` | `iteracja` (dla bramki jakości) | Stacja w run'ie |
| `Zmienna` | `run_id`, `variable_id` | `name`, `type`, `source_type` | `confidence_score`, `value` | Zmienna z `zmienne` |
| `Decyzja` | `run_id`, `decision_id` | `wariant`, `uzasadnienie` | `wariant_rezerwowy`, `metoda_doboru` | Rekomendacja z `dobierz` |
| `Podproblem` | `run_id`, `podproblem_id` | `opis`, `krytycznosc` | `typ_dekompozycji` | Podproblem z `dekompozycja` |
| `Twierdzenie` | `run_id`, `twierdzenie_id` | `tresc`, `status` | `zrodlo`, `metoda`, `uzasadnienie` | Twierdzenie z `weryfikacja` |
| `Werdykt` | `run_id`, `werdykt_id` | `status`, `zrodlo`, `metoda` | `uzasadnienie` | Werdykt z `weryfikacja` |
| `Wniosek` | `run_id`, `wniosek_id` | `tresc` | `typ_wiedzy`, `miejsce_zapisu` | Wniosek z `ewaluacja` lub `utrwal` |
| `KrokPlanu` | `run_id`, `krok_id` | `opis`, `kolejnosc` | `zaleznosci`, `szacowany_czas` | Krok z `planuj` |
| `Zmiana` | `run_id`, `zmiana_id` | `opis`, `status` | `plik`, `typ` | Zmiana z `realizuj` |
| `WymiarAudytu` | `run_id`, `wymiar_id` | `nazwa`, `ocena` | `uzasadnienie` | Wymiar z `sprawdzenie` |
| `Checkpoint` | `run_id`, `checkpoint_file` | `stacja`, `timestamp`, `yaml_poprawny` | `hash`, `rozmiar` | Checkpoint plikowy |

## Schemat krawędzi

| Typ relacji | Węzeł źródłowy | Węzeł docelowy | Wymagane właściwości | Opis |
| --- | --- | --- | --- | --- |
| `ZAWIERA` | `Run` | `Stacja` | - | Run zawiera stację |
| `NASTAPILA_PO` | `Stacja` | `Stacja` | - | Kolejność stacji w run'ie |
| `WYPRODUKOWALA` | `Stacja` | `Zmienna` \| `Decyzja` \| `Podproblem` \| `Twierdzenie` \| `Werdykt` \| `Wniosek` \| `KrokPlanu` \| `Zmiana` \| `WymiarAudytu` | - | Stacja wyprodukowała encję |
| `ZALEZY_OD` | `Zmienna` | `Zmienna` | `typ_zaleznosci` | Zależność między zmiennymi |
| `OPARTA_NA` | `Decyzja` | `Zmienna` \| `Twierdzenie` | - | Decyzja oparta na zmiennej lub twierdzeniu |
| `DOTYCZY` | `Werdykt` | `Twierdzenie` | - | Werdykt dotyczy twierdzenia |
| `WYPROWADZONY_Z` | `Wniosek` | `Stacja` | - | Wniosek wyprowadzony ze stacji |
| `ROZWIĄZUJE` | `KrokPlanu` | `Podproblem` | - | Krok planu rozwiązuje podproblem |
| `REALIZUJE` | `Zmiana` | `KrokPlanu` | - | Zmiana realizuje krok planu |
| `WERYFIKUJE` | `WymiarAudytu` | `Zmiana` \| `Twierdzenie` | - | Wymiar audytu weryfikuje zmianę lub twierdzenie |
| `ZAPISANA_W` | `Stacja` | `Checkpoint` | - | Stacja zapisana w checkpoincie |
| `KONTYNUACJA` | `Run` | `Run` | - | Run B jest kontynuacją runa A |
| `NAPRAWIA` | `Run` | `Run` | `blad_naprawiany` | Run C naprawia błąd z runa A |
| `PONOWNE_URUCHOMIENIE` | `Run` | `Run` | `powod` | Run D jest ponownym uruchomieniem runa A |

## Instrukcja zapisu do Memgraph

### Po każdej stacji (w `utrwal`)

Po zapisie checkpointu `utrwal` zapisuje węzły i krawędzie do Memgraph na podstawie koperty:

1. **Węzeł `Stacja`** - dla stacji bieżącej, z `run_id`, `nazwa`, `status`, `timestamp`, `checkpoint_file`.
2. **Krawędź `ZAWIERA`** - od `Run` do `Stacja` (jeśli `Run` jeszcze nie istnieje, utwórz go).
3. **Krawędź `NASTAPILA_PO`** - od `Stacja` bieżącej do `Stacja` poprzedniej (z `stacja_poprzednia` w kopercie).
4. **Krawędź `ZAPISANA_W`** - od `Stacja` do `Checkpoint`.
5. **Węzły encji** - dla każdej encji wyprodukowanej przez stację (zmienne, decyzje, podproblemy, twierdzenia, werdykty, wnioski, kroki planu, zmiany, wymiary audytu).
6. **Krawędź `WYPRODUKOWALA`** - od `Stacja` do każdej encji.
7. **Krawędzie relacyjne** - na podstawie sekcji `relacje` w kopercie (`ZALEZY_OD`, `OPARTA_NA`, `DOTYCZY`, `ROZWIĄZUJE`, `REALIZUJE`, `WERYFIKUJE`, `WYPROWADZONY_Z`).

### Po zakończeniu run'u

1. **Węzeł `Run`** - z `timestamp_end`, `status: zakonczony`, `iteracja_bramki` ostateczna.
2. **Krawędzie między runami** - jeśli run jest kontynuacją, naprawą albo ponownym uruchomieniem, zapisz `KONTYNUACJA` / `NAPRAWIA` / `PONOWNE_URUCHOMIENIE`.

### Walidacja po checkpoincie

Po zapisie checkpointu `utrwal` wykonuje zapytanie weryfikujące ciągłość grafu:

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja {nazwa: $stacja})
MATCH (s)-[:NASTAPILA_PO]->(s_prev:Stacja)
RETURN s_prev.nazwa AS poprzednia, s.nazwa AS aktualna, s_prev.status AS status_poprzedniej
```

Jeśli `s_prev.status` != `zakonczona`, zgłoś anomalię: stacja bieżąca nastąpiła po stacji niezakończonej.

## Wzorcowe zapytania Cypher

### Pochodzenie decyzji

```cypher
MATCH (d:Decyzja {run_id: $run_id})<-[:WYPRODUKOWALA]-(s:Stacja)
MATCH (d)-[:OPARTA_NA]->(z:Zmienna)
RETURN d.wariant, s.nazwa AS stacja_zrodlo, collect(z.name) AS zmienne_bazowe
```

### Twierdzenia oparte na hipotezach

```cypher
MATCH (t:Twierdzenie {run_id: $run_id})<-[:DOTYCZY]-(w:Werdykt)
MATCH (t)<-[:WYPRODUKOWALA]-(s:Stacja)
WHERE w.status = 'potwierdzony'
MATCH (t)-[:OPARTA_NA]->(z:Zmienna {source_type: 'hypothesis'})
RETURN t.tresc, z.name, z.source_type
```

### Wszystkie stacje run'u w kolejności

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja)
OPTIONAL MATCH (s)-[:NASTAPILA_PO]->(s_prev:Stacja)
RETURN s.nazwa, s.status, s.timestamp, s_prev.nazwa AS poprzednia
ORDER BY s.timestamp
```

### Osierocone węzły (anomalie)

```cypher
MATCH (n) WHERE n.run_id = $run_id
AND NOT ()-[:WYPRODUKOWALA]->(n)
AND NOT ()-[:ZAWIERA]->(n)
AND NOT (n)-[:ZAPISANA_W]->()
RETURN labels(n), n
```

### Stacje bez poprzednika (anomalie)

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja)
WHERE s.nazwa <> 'inicjuj'
AND NOT (s)-[:NASTAPILA_PO]->()
RETURN s.nazwa, s.status
```

### Łańcuch pochodzenia zmiany

```cypher
MATCH (z:Zmiana {run_id: $run_id})<-[:WERYFIKUJE]-(wa:WymiarAudytu)
MATCH (z)-[:REALIZUJE]->(k:KrokPlanu)
MATCH (k)-[:ROZWIĄZUJE]->(p:Podproblem)
MATCH (p)<-[:WYPRODUKOWALA]-(sd:Stacja {nazwa: 'dekompozycja'})
RETURN z.opis, k.opis, p.opis, sd.nazwa
```

### Spójność grafu run'u

```cypher
MATCH (r:Run {run_id: $run_id})-[:ZAWIERA]->(s:Stacja)
WITH r, count(s) AS liczba_stacji, collect(s.nazwa) AS stacje
MATCH (r)-[:ZAWIERA]->(s2:Stacja)-[:NASTAPILA_PO]->(s3:Stacja)
WITH r, liczba_stacji, stacje, count(s2) AS liczba_relacji
RETURN r.run_id, liczba_stacji, liczba_relacji,
       CASE WHEN liczba_relacji = liczba_stacji - 1 THEN 'spójny' ELSE 'niespójny' END AS status
```

### Wszystkie run'y i ich statusy

```cypher
MATCH (r:Run)
OPTIONAL MATCH (r)-[:KONTYNUACJA|:NAPRAWIA|:PONOWNE_URUCHOMIENIE]->(r2:Run)
RETURN r.run_id, r.zamiar, r.sciezka, r.status, r2.run_id AS powiazany_run
ORDER BY r.timestamp_start DESC
```

## Mapowanie sekcji koperty na węzły grafu

| Sekcja koperty | Węzeł grafu | Krawędzie |
| --- | --- | --- |
| `run_id`, `sciezka`, `stan.zamiar` | `Run` | - |
| `stacja_aktualna`, `stacja_poprzednia` | `Stacja` | `ZAWIERA`, `NASTAPILA_PO` |
| `pola_stacji.zmienne.variables[]` | `Zmienna` (per zmienna) | `WYPRODUKOWALA`, `ZALEZY_OD` |
| `pola_stacji.zmienne.relations[]` | - | `ZALEZY_OD` |
| `pola_stacji.dekompozycja.podproblemy[]` | `Podproblem` | `WYPRODUKOWALA` |
| `pola_stacji.dobierz.rekomendacja` | `Decyzja` | `WYPRODUKOWALA`, `OPARTA_NA` |
| `pola_stacji.planuj.plan.kroki[]` | `KrokPlanu` | `WYPRODUKOWALA`, `ROZWIĄZUJE` |
| `pola_stacji.realizuj.zmiany[]` | `Zmiana` | `WYPRODUKOWALA`, `REALIZUJE` |
| `pola_stacji.weryfikacja.werdykty[]` | `Werdykt` + `Twierdzenie` | `WYPRODUKOWALA`, `DOTYCZY` |
| `pola_stacji.sprawdzenie.wymiary[]` | `WymiarAudytu` | `WYPRODUKOWALA`, `WERYFIKUJE` |
| `pola_stacji.ewaluacja.wnioski[]` | `Wniosek` | `WYPRODUKOWALA`, `WYPROWADZONY_Z` |
| `relacje[]` w kopercie | - | wszystkie krawędzie relacyjne |
| Checkpoint plikowy | `Checkpoint` | `ZAPISANA_W` |

## Reguły integralności grafu

1. **Każdy `Run` musi mieć co najmniej jedną stację (`ZAWIERA`).**
2. **Każda `Stacja` (poza `inicjuj`) musi mieć `NASTAPILA_PO` do stacji poprzedniej.**
3. **Każda `Stacja` musi mieć `ZAPISANA_W` do `Checkpoint` (poza stacjami `pominieta`).**
4. **Każda encja (`Zmienna`, `Decyzja`, itd.) musi mieć `WYPRODUKOWALA` od `Stacja`.**
5. **Każdy `Werdykt` musi mieć `DOTYCZY` do `Twierdzenie`.**
6. **Każdy `KrokPlanu` musi mieć `ROZWIĄZUJE` do `Podproblem` (w ścieżce `dogłębny`).**
7. **Każda `Zmiana` musi mieć `REALIZUJE` do `KrokPlanu`.**
8. **Brak osieroconych węzłów** - węzły bez `WYPRODUKOWALA` albo `ZAWIERA` są anomalią.
9. **Ciągłość `NASTAPILA_PO`** - liczba relacji `NASTAPILA_PO` = liczba stacji - 1.
10. **`run_id` spójny** - wszystkie węzły w run'ie mają ten sam `run_id`.

Naruszenie którejkolwiek reguły oznacza anomalię zgłaszaną przez `monitoruj` (przy restarcie) albo `audyt_runu` (weryfikacja ex-post).
