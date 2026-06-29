# Pipeline umiejętności - cykl życia rozwiązania

Pipeline orkiestruje skille w repozytorium `/etc/windsurf/skills/` w spójny cykl życia rozwiązania: od zamiaru użytkownika do zweryfikowanego, ocenionego i utrwalonego wyniku.

Skille traktowane są jako stacje montażowe. Każda stacja ma kontrakt wejścia/wyjścia i bramkę jakości. Pętla zwrotna pozwala na iteracyjną korektę (maks. 2 iteracje, potem eskalacja do użytkownika).

## Diagram pipeline'u

```text
[ZAMIAR UŻYTKOWNIKA]
   |
   v
[inicjuj] --trywialne?--> [odpowiedź bezpośrednia]
   | (rutynowe/złożone)
   v
[zmienne] -> [analiza]
   |
   +--(szybki/pełny)--> [dobierz]
   |
   +--(dogłębny)--> [dekompozycja] -> [dobierz] -> [routing]
   |
   v
[planuj]
   |
   v
[realizuj] (z jak + context7)
   |
   v
[weryfikacja] -> [sprawdzenie]
   |
   +--(szybki)--> [ROZWIĄZANIE]
   |
   v
[BRAMKA JAKOŚCI] --niezgodny--> powrót do [dobierz]/[planuj] (max 2 iteracje)
   | (zgodny)
   v
[ewaluacja] -> [utrwal] -> [monitoruj] -> [ROZWIĄZANIE ZAMKNIĘTE]
```

## Stacje pipeline'u

| # | Stacja | Skill | Faza | Wejście | Wyjście |
| --- | --- | --- | --- | --- | --- |
| 0 | inicjuj | `inicjuj` | Inicjacja | zamiar | klasyfikacja + punkt wejścia |
| 1 | zmienne | `zmienne` | Normalizacja | zamiar + kontekst (lub obiekt + oczekiwany wynik) | kontrakt zmiennych |
| 2 | analiza | `analiza` | Rozpoznanie | nazwa obiektu | raport: typ, struktura, relacje |
| 3 | dekompozycja | `dekompozycja` | Podział | problem złożony | podproblemy + zależności |
| 4 | dobierz | `dobierz` | Wybór | cel doboru + warianty + kryteria | rekomendacja wariantu |
| 5 | routing | `routing` | Routing ścieżki | zamiar + stawka + ryzyko | ścieżka: szybki/pełny/dogłębny |
| 6 | planuj | `planuj` | Planowanie | cel do zaplanowania | plan kroków, zasoby, ryzyka |
| 7 | realizuj | `realizuj` | Realizacja | plan | zrealizowane zmiany |
| 7a | jak | `jak` | Realizacja (wsp.) | plan | zasady wykonania |
| 7b | context7 | `context7` | Realizacja (wsp.) | biblioteka | aktualna dokumentacja |
| 8 | weryfikacja | `weryfikacja` | Weryfikacja | twierdzenia (wyprowadzone z rozwiązania) | werdykty prawdziwościowe |
| 9 | sprawdzenie | `sprawdzenie` | Audyt | pytanie + artefakt | audyt zgodności |
| 10 | ewaluacja | `ewaluacja` | Ewaluacja ex-post | rozwiązanie + cel | ocena skuteczności |
| 11 | utrwal | `utrwal` | Utrwalenie | wnioski | zapis do .ai-kb/Serena |
| 12 | monitoruj | `monitoruj` | Monitorowanie | zadanie + checkpointy | status postępu |

## Ścieżki pipeline'u

Routing (`routing`) wybiera jedną z trzech ścieżek na podstawie stawki decyzyjnej i ryzyka. W ścieżkach `szybki` i `pełny` wybór ścieżki jest wykonywany przez `inicjuj` (klasyfikacja zamiaru), a nie przez `routing`. `routing` jest uruchomiane tylko w ścieżce `dogłębny`, gdy stawka i ryzyko są wysokie i wymagają jawnej analizy ścieżki.

### Ścieżka szybki (niska stawka, niskie ryzyko)

```text
[inicjuj] -> [zmienne] -> [analiza] -> [dobierz] -> [sprawdzenie] -> [ROZWIĄZANIE]
```

Pomija: dekompozycję, routing, planuj, realizuj, weryfikację, ewaluację, utrwal, monitoruj.

### Ścieżka pełny (średnia stawka, średnie ryzyko)

```text
[inicjuj] -> [zmienne] -> [analiza] -> [dobierz] -> [planuj] -> [realizuj]
-> [weryfikacja] -> [sprawdzenie] -> [utrwal] -> [ROZWIĄZANIE]
```

Pomija: dekompozycję, routing, ewaluację, monitoruj.

### Ścieżka dogłębny (wysoka stawka, wysokie ryzyko)

Pełny pipeline ze wszystkimi stacjami, w tym dekompozycją, routingiem, ewaluacją i monitorowaniem.

## Bramka jakości

Po stacji `sprawdzenie` następuje bramka jakości (z wyjątkiem ścieżki `szybki`, gdzie `sprawdzenie` kończy pipeline i przechodzi bezpośrednio do `ROZWIĄZANIE`):

- **status zgodny** -> przejście do `ewaluacja` (lub `utrwal` w ścieżce pełny).
- **status niezgodny** -> powrót do `dobierz` albo `planuj` (maks. 2 iteracje).
- **po 2 iteracjach** -> eskalacja do użytkownika z opisem blokady.

## Jak używać pipeline'u

### Wywołanie pełne

1. Rozpocznij od skilla `inicjuj` z zamiarem użytkownika.
2. `inicjuj` klasyfikuje zamiar i wskazuje punkt wejścia.
3. Wykonuj stacje sekwencyjnie, przekazując wyjście poprzedniej jako wejście następnej.
4. Po `sprawdzenie` sprawdź status bramki jakości.
5. Jeśli zgodny, kontynuuj do `ewaluacja` -> `utrwal` -> `monitoruj`.
6. Jeśli niezgodny, wróć do `dobierz` albo `planuj`.

### Wywołanie skrócone

Jeśli `inicjuj` sklasyfikuje zamiar jako `rutynowe`, pomiń `dekompozycja`, `routing`, `ewaluacja`, `monitoruj` i wykonaj ścieżkę pełny. Jeśli `inicjuj` sklasyfikuje zamiar jako `złożone`, wykonaj ścieżkę dogłębny (ze wszystkimi stacjami).

### Wywołanie bezpośrednie

Jeśli `inicjuj` sklasyfikuje zamiar jako `trywialne`, odpowiedz bezpośrednio bez uruchamiania pipeline'u.

### Wywołanie od środkowej stacji

Możesz uruchomić pipeline od dowolnej stacji, jeśli masz już wyniki poprzednich stacji (np. masz gotowy plan i chcesz zacząć od `realizuj`).

## Kontrakty między stacjami

Każda stacja przyjmuje wyjście poprzedniej jako wejście. Szczegółowe mapowanie pole-po-polu i typologiczne między stacjami znajduje się w `kontrakty_pipelines.md`.

Transformacja "zamiar" -> "problem": zamiar użytkownika (wejście `inicjuj`) staje się problemem do dekompozycji po `analiza` - sekcje 6 (Ograniczenia) i 7 (Wnioski) raportu analitycznego pozwalają wyprowadzić `PROBLEM LUB CEL ZŁOŻONY` dla `dekompozycja` przez transformację agenta (`agent_inference`).

| Stacja źródłowa | Wyjście | Stacja docelowa | Wejście |
| --- | --- | --- | --- |
| inicjuj | klasyfikacja + punkt wejścia | zmienne | zamiar + kontekst |
| zmienne | kontrakt zmiennych | analiza | zmienne + obiekt |
| analiza | raport analityczny | dekompozycja | problem złożony |
| analiza | raport analityczny | dobierz (gdy pominięto dekompozycja) | cel doboru + warianty |
| dekompozycja | podproblemy + zależności | dobierz | raport + kryteria |
| dobierz | rekomendacja wariantu | routing | zamiar + stawka + ryzyko |
| dobierz | rekomendacja wariantu | planuj (gdy pominięto routing) | cel do zaplanowania |
| routing | ścieżka pipeline'u | planuj | rekomendacja |
| planuj | plan kroków | realizuj | plan |
| realizuj | zrealizowane zmiany | weryfikacja | rozwiązanie + twierdzenia |
| weryfikacja | werdykty prawdziwościowe | sprawdzenie | pytanie + artefakt |
| sprawdzenie | audyt zgodności | ewaluacja | rozwiązanie + cel |
| sprawdzenie | audyt niezgodny | dobierz/planuj (pętla bramki) | werdykt + wymiary audytu |
| ewaluacja | ocena skuteczności | utrwal | wnioski |
| utrwal | zapis do .ai-kb/Serena | monitoruj | zadanie + checkpointy |

## Mechanizm wymiany danych między stacjami

Pipeline używa formalnego nośnika danych - **koperty** - jako jedynego kanału przekazu pól kontraktowych między stacjami. Kontekst konwersacji służy wyłącznie do uzasadnień i rozumowania, nie do przenoszenia pól kontraktu.

### Koperta

Koperta to blok YAML emitowany na końcu wyjścia każdej stacji i konsumowany na początku wejścia stacji następnej. Koperta jest jedynym formalnym nośnikiem danych między stacjami.

```yaml
KOPERTA:
  run_id: "<timestamp>-<skrot-zamiaru>"
  sciezka: szybki | pelny | doglebny
  stacja_aktualna: <nazwa-stacji>
  stacja_poprzednia: <nazwa-stacji> | null
  stan:                      # skumulowane pola kluczowe z wszystkich poprzednich stacji
    zamiar: ""
    klasyfikacja: ""
    punkt_wejscia: ""
  pola_stacji:               # wyjścia poszczególnych stacji (kluczowe pola kontraktu)
    inicjuj:
      klasyfikacja: ""
      punkt_wejscia: ""
      uzasadnienie: ""
      ryzyka: []
    zmienne:
      variables: []
      relations: []
      sources_used: []
      missing_data_resolution: {}
    analiza:
      raport_streszczenie: ""
      pewnosc: ""
    # ... dalsze stacje dodają swoje pola
  walidacja:                 # walidacja kompletności przed przejściem do stacji następnej
    stacja_docelowa: <nazwa-stacji>
    pola_wymagane: []         # z kontraktu wejścia stacji docelowej
    pola_obecne: []
    pola_brakujace: []
    status: gotowy | wnioskowane | niekompletne
    akcja_naprawcza: ""       # gdy niekompletne: pytanie do uzytkownika / agent_inference / powrot
  relacje:                    # jawne relacje między encjami w run'ie (zapisywane do Memgraph)
    - zrodlo: "stacja:zmienne"        # identyfikator encji źródłowej
      cel: "stacja:analiza"           # identyfikator encji docelowej
      typ: dostarcza_dane             # typ relacji (zgodny ze schematem grafu)
      pola: [analysis_object.name]    # które pola są przekazywane
    - zrodlo: "zmienna:V001"
      cel: "zmienna:V003"
      typ: zalezy_od
    - zrodlo: "stacja:dobierz"
      cel: "stacja:planuj"
      typ: dostarcza_rekomendacje
      pola: [rekomendacja]
```

### Zasady koperty

1. **Emituj na końcu:** każda stacja merytoryczna kończy wyjście blokiem `KOPERTA`.
2. **Konsumuj na początku:** stacja następna rozpoczyna od odczytu koperty z wyjścia poprzedniej stacji.
3. **Kumuluj stan:** `stan` zawiera pola kluczowe skumulowane ze wszystkich poprzednich stacji. `pola_stacji` zawiera wyjścia poszczególnych stacji w sekcjach nazwanych według stacji.
4. **Waliduj przed przejściem:** przed przekazaniem do stacji następnej sprawdź `pola_wymagane` vs `pola_obecne`. Jeśli brakuje pól wymaganych, ustaw `status: niekompletne` i wskaż `akcja_naprawcza`.
5. **Nie duplikuj w kontekście:** pola kontraktowe przekazuj wyłącznie przez kopertę, nie przez powtarzanie w treści konwersacji.
6. **Kompresuj w ścieżce dogłębny:** po stacjach `analiza`, `dobierz`, `sprawdzenie` rozważ usunięcie starszych sekcji `pola_stacji` z kontekstu konwersacji, jeśli zostały zapisane w checkpointie (patrz niżej). Pozostaw tylko `stan` i sekcję stacji bieżącej.
7. **Stacje pomocnicze:** `jak` i `context7` nie emitują koperty - są skillami narzędziowymi wywoływanymi wewnątrz `realizuj`.

### Checkpointowanie plikowe

Po zakończeniu każdej stacji merytorycznej koperta jest zapisywana do pliku checkpointu. Umożliwia to restart od dowolnej stacji oraz kompresję kontekstu w długich pipeline'ach.

**Struktura katalogów:**

```
.ai-kb/pipeline-runs/
  <run_id>/
    manifest.yaml              # indeks stacji, statusy, ścieżka, iteracje bramki
    stan_00_inicjuj.yaml       # checkpoint po stacji inicjuj
    stan_01_zmienne.yaml       # checkpoint po stacji zmienne
    stan_02_analiza.yaml
    ...
```

**Manifest:**

```yaml
MANIFEST:
  run_id: "<timestamp>-<skrot-zamiaru>"
  zamiar: ""
  sciezka: szybki | pelny | doglebny
  iteracja_bramki: 0
  stacje:
    - stacja: inicjuj
      status: zakonczona           # zakonczona | w_trakcie | zablokowana | pominieta
      timestamp: "2026-06-29T14:32:10"
      checkpoint: stan_00_inicjuj.yaml
    - stacja: zmienne
      status: zakonczona
      timestamp: "2026-06-29T14:35:22"
      checkpoint: stan_01_zmienne.yaml
    - stacja: analiza
      status: w_trakcie
      timestamp: null
      checkpoint: null
```

### Zasady checkpointowania

1. **Tworzenie run:** stacja `inicjuj` tworzy katalog `.ai-kb/pipeline-runs/<run_id>/` i plik `manifest.yaml` z pustym stanem stacji.
2. **Zapis po stacji:** po zakończeniu każdej stacji merytorycznej zapisz kopertę do `stan_<NN>_<stacja>.yaml` i zaktualizuj `manifest.yaml` (status `zakonczona`, timestamp, nazwa checkpointu).
3. **Aktualizacja statusu:** przed rozpoczęciem stacji ustaw jej status na `w_trakcie` w manifeście. Po zakończeniu na `zakonczona`. Przy blokadzie na `zablokowana`.
4. **Restart od stacji:** przy restarcie odczytaj `manifest.yaml`, zidentyfikuj ostatnią stację `zakonczona`, odczytaj jej checkpoint i kontynuuj od stacji następnej. Skilla `monitoruj` użyj do raportowania statusu restartu.
5. **Kompresja kontekstu:** w ścieżce `dogłębny` (10+ stacji), po zapisaniu checkpointu dla stacji starszych niż 3 wstecz, możesz usunąć ich sekcje `pola_stacji` z koperty w kontekście konwersacji. Pozostaw tylko `stan` i sekcje 3 ostatnich stacji. Pełne dane pozostają w plikach checkpointów.
6. **Bramka jakości:** iteracje bramki zwiększają `iteracja_bramki` w manifeście. Przy powrocie do `dobierz`/`planuj` zapisz nowy checkpoint z sufiksem `_iter<N>`.
7. **Stacje pominięte:** stacje pominięte w ścieżce `szybki`/`pełny` oznaczaj w manifeście jako `pominieta` bez checkpointu.
8. **Czyszczenie:** po zakończeniu pipeline'u (status `zakonczony` dla ostatniej stacji) katalog run pozostaje jako historia audytowa. Nie usuwaj automatycznie.

### Integracja z istniejącymi kontraktami

Mapowanie kontraktów pole-po-polu w `kontrakty_pipelines.md` używa statusów `bezpośrednie`, `wnioskowane`, `kontekstowe`, `brak`. Z wprowadzeniem koperty:

- `bezpośrednie` -> pole trafia do `pola_stacji.<stacja_zrodlowa>` w kopercie, stacja docelowa odczytuje z koperty.
- `wnioskowane` -> stacja docelowa wyprowadza pole z `pola_stacji` przez `agent_inference`, wynik zapisuje w swojej sekcji koperty.
- `kontekstowe` -> pole pochodzi z `stan.zamiar` w kopercie (nie z nieokreślonego "kontekstu konwersacji").
- `brak` -> stacja docelowa pozyskuje pole przez pytanie do użytkownika albo własne źródła, wynik zapisuje w swojej sekcji koperty.

### Graf powiązań w Memgraph

Pipeline zapisuje relacje między encjami w run'ie do Memgraph jako graf. Graf służy do audytowalności relacyjnej, zapytań o pochodzenie decyzji i weryfikacji spójności run'u.

**Schemat grafu:** węzły (`Run`, `Stacja`, `Zmienna`, `Decyzja`, `Podproblem`, `Twierdzenie`, `Werdykt`, `Wniosek`, `KrokPlanu`, `Zmiana`, `WymiarAudytu`, `Checkpoint`) i krawędzie (`ZAWIERA`, `NASTAPILA_PO`, `WYPRODUKOWALA`, `ZALEZY_OD`, `OPARTA_NA`, `DOTYCZY`, `WYPROWADZONY_Z`, `ROZWIĄZUJE`, `REALIZUJE`, `WERYFIKUJE`, `ZAPISANA_W`, `KONTYNUACJA`, `NAPRAWIA`, `PONOWNE_URUCHOMIENIE`). Pełny schemat, mapowanie koperty na węzły, wzorcowe zapytania Cypher i reguły integralności: patrz `_shared/graf-pipeline.md`.

**Zapis do Memgraph:** po każdej stacji `utrwal` zapisuje węzły i krawędzie na podstawie sekcji `relacje` w kopercie. Po zakończeniu run'u zapisuje węzeł `Run` i relacje między runami (`KONTYNUACJA`, `NAPRAWIA`, `PONOWNE_URUCHOMIENIE`). Szczegóły: patrz `utrwal/SKILL.md` (sekcja "Graf powiązań w Memgraph").

**Walidacja po checkpoincie:** po zapisie checkpointu `utrwal` wykonuje zapytanie Cypher weryfikujące ciągłość grafu (czy stacja bieżąca nastąpiła po stacji zakończonej). Naruszenie zgłasza jako anomalię.

**Weryfikacja ex-post:** skill `audyt_runu` weryfikuje spójność całego run'u przez zapytania Cypher - osierocone węzły, stacje bez poprzednika, brakujące krawędzie, niespójność `run_id`. Szczegóły: patrz `audyt_runu/SKILL.md`.

## Granice ról skilli

Każdy skill ma jednoznaczną rolę. Nie dubluj ról:

| Skill | Pytanie podstawowe | Nie mylić z |
| --- | --- | --- |
| inicjuj | Czy to wymaga pipeline'u? | analiza (czym jest?) |
| zmienne | Jakie zmienne i skąd? | analiza (jaka struktura?) |
| analiza | Czym jest obiekt? | dobierz (co wybrać?) |
| dekompozycja | Z jakich podproblemów? | planuj (jakie kroki?) |
| dobierz | Który wariant rozwiązania? | routing (którą ścieżką?) |
| routing | Którą ścieżką pipeline'u? | dobierz (który wariant?) |
| planuj | Jakie kroki realizacji? | dekompozycja (jakie podproblemy?) |
| realizuj | Jak wykonać zmiany? | planuj (jak zaplanować?) |
| weryfikacja | Czy twierdzenie jest prawdziwe? | sprawdzenie (czy zgodne z pytaniem?) |
| sprawdzenie | Czy zgodne z pytaniem? | ewaluacja (jaka wartość ex-post?) |
| ewaluacja | Jaka wartość ex-post? | sprawdzenie (czy zgodne?) |
| utrwal | Co zapisać na przyszłość? | monitoruj (jaki status?) |
| monitoruj | Gdzie jesteśmy względem planu? | planuj (jak zaplanować?) |
| audyt_runu | Czy run jest spójny relacyjnie? | sprawdzenie (czy artefakt zgodny?) |

## Ryzyka i warunki rewizji

- **Dryf ontologiczny:** jeśli stacje zaczynają dublować role, wróć do tabeli granic.
- **Pętla nieskończona:** bramka jakości ma limit 2 iteracji, potem eskalacja.
- **Luka źródłowa:** `weryfikacja` bez źródeł oznacza `niezweryfikowany`, nie `obalony`.
- **Zbyt wąska ścieżka:** jeśli w trakcie realizacji okaże się, że problem jest złożony, wróć do `inicjuj` i przeklasyfikuj.
- **Utrata kontekstu:** w ścieżce `dogłębny` (10+ stacji) kontekst konwersacji może przekroczyć okno modelu. Rozwiązane przez kopertę z kompresją (patrz "Mechanizm wymiany danych") - starsze sekcje `pola_stacji` można usunąć z kontekstu po zapisie checkpointu.
- **Brak walidacji wyjścia:** rozwiązane przez sekcję `walidacja` w kopercie - każda stacja sprawdza `pola_wymagane` vs `pola_obecne` przed przejściem dalej.
- **Brak checkpointowania:** rozwiązane przez checkpointowanie plikowe w `.ai-kb/pipeline-runs/<run_id>/` - przerwanie umożliwia restart od ostatniej stacji `zakonczona` w manifeście.

## Zapis do bazy wiedzy

Po zakończeniu pipeline'u (lub po bramce jakości) uruchom `utrwal`, aby zapisać:

- decyzje architektoniczne z uzasadnieniem,
- preferencje techniczne,
- znane błędy i obejścia,
- kamienie milowe,
- wzorce i antywzorce.

Miejsca zapisu: `.ai-kb/`, pamięć Serena (`write_memory` / `edit_memory`), Memgraph (relacje). Hierarchia źródeł prawdy i reguły rozstrzygania konfliktów: patrz `_shared/zrodla-i-narzedzia.md`.

## Spis skilli w pipeline'u

### Skille istniejące (8)

- `analiza` - rozpoznanie obiektu
- `context7` - aktualna dokumentacja
- `dobierz` - dobór wariantu
- `jak` - zasady odpowiedzi "jak"
- `planuj` - planowanie realizacji
- `sprawdzenie` - audyt artefaktu
- `weryfikacja` - status prawdziwościowy
- `zmienne` - kontrakt zmiennych

### Skille nowe (7)

- `inicjuj` - klasyfikacja zamiaru i punkt wejścia
- `dekompozycja` - podział problemu na podproblemy
- `realizuj` - wykonanie zmian zgodnie z planem
- `routing` - wybór ścieżki pipeline'u
- `ewaluacja` - ocena ex-post rozwiązania
- `utrwal` - zapis wiedzy do .ai-kb/Serena
- `monitoruj` - śledzenie postępu i blokad

## Scenariusze uzycia

Scenariusze uzycia pipeline'u z krokami i kontraktami I/O znajduja sie w pliku `scenariusze_uzycia.md`. Szczegolowe mapowanie kontraktow pole-po-polu i typologiczne miedzy stacjami znajduje sie w `kontrakty_pipelines.md`.
