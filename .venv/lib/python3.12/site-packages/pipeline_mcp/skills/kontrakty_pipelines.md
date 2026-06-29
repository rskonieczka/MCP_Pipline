# Kontrakty I/O stacji pipeline'u

Kontrakty wejścia/wyjścia dla każdej stacji pipeline'u umiejętności, wyciągnięte z sekcji `Wejście` i `Wynik`/`Wyjście` każdego `SKILL.md`. Typy zmiennych klasyfikowane są według ontologii ze skilla `zmienne`: `fact`, `requirement`, `constraint`, `relationship` (podzbiór 4 typów wymieniony w zadaniu ekstrakcji; pełna ontologia `zmienne` obejmuje 12 typów).

Źródło pipeline'u: `pipeline_sklills.md`.

## Tabela zbiorcza kontraktów I/O

| # | Stacja | Wejście wymagane | Wejście opcjonalne | Wyjście | Typy zmiennych wejścia | Typy zmiennych wyjścia |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `inicjuj` | `ZAMIAR UŻYTKOWNIKA` | `KONTEKST`, `ŹRÓDŁA`, `TRYB INICJACJI` | `klasyfikacja`, `punkt_wejscia`, `uzasadnienie`, `ryzyka` | requirement, constraint, fact | decision, risk, fact |
| 1 | `zmienne` | `task_goal` + `context` LUB `object_of_analysis` + `expected_output` | `operation_mode`, profil domenowy, `ŹRÓDŁA`, `missing_data_resolution` | `variables`, `relations`, `sources_used`, `missing_data_resolution`, `domain_outputs` | fact, requirement, constraint, relationship (wszystkie 12 typów) | fact, requirement, constraint, relationship, assumption, hypothesis, metric, entity, risk, decision, preference, unknown |
| 2 | `analiza` | `NAZWA OBIEKTU` | `KONTEKST`, `ZAKRES`, `ŹRÓDŁA`, `TRYB ANALIZY`, `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` | raport 7-sekcyjny (Tożsamość, Struktura, Relacje, Zachowanie, Cel, Ograniczenia, Wnioski) + `Pewność rozpoznania` | entity, constraint, fact | entity, relationship, fact, constraint, risk |
| 3 | `dekompozycja` | `PROBLEM LUB CEL ZŁOŻONY` | `KONTEKST`, `OGRANICZENIA`, `ŹRÓDŁA`, `TRYB DEKOMPOZYCJI` | `podproblemy`, `zaleznosci`, `kolejnosc`, `krytyczne` | requirement, constraint, fact | entity, relationship, constraint, requirement |
| 4 | `dobierz` | `CEL DOBORU` + (≥1 z: `WARIANTY`, `ŹRÓDŁA`, `KONTEKST`) | `KRYTERIA`, `OGRANICZENIA`, `PREFERENCJE`, `TRYB DOBORU`, `LICZBA REKOMENDACJI`, `FORMAT WYNIKU`, `DOZWOLONE ŹRÓDŁA ZEWNĘTRZNE`, `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` | `STATUS DOBORU`, `METODA DOBORU`, `WARIANTY`, `KRYTERIA`, `PORÓWNANIE`, `REKOMENDACJA` (główna + rezerwowa), `RYZYKA I WARUNKI REWIZJI`, `NAJBLIŻSZY KROK` | requirement, entity, constraint, preference, fact | decision, entity, requirement, constraint, risk, fact |
| 5 | `routing` | `ZAMIAR LUB PROBLEM` | `STAWKA DECYZYJNA`, `RYZYKO`, `ZASOBY`, `TRYB ROUTINGU` | `sciezka`, `stawka`, `ryzyko`, `stacje_uruchomione`, `stacje_pominiete`, `stacje_poglebione` | requirement, constraint | decision, constraint, relationship |
| 6 | `planuj` | `CEL DO ZAPLANOWANIA` | `KONTEKST`, `OGRANICZENIA`, `HORYZONT`, `TRYB PLANOWANIA`, `ŹRÓDŁA`, `KRYTERIA SUKCESU`, `ZAKRES` | plan 7-sekcyjny (Cel, Sytuacja, Kroki, Zasoby, Ryzyka, Kryteria sukcesu, Punkty kontrolne) + walidacja planu + kryteria ukończenia | requirement, constraint, fact | requirement, constraint, assumption, risk, metric, entity |
| 7 | `realizuj` | `PLAN DO ZREALIZOWANIA` | `KONTEKST`, `ŹRÓDŁA`, `TRYB REALIZACJI` | `kroki_wykonane`, `kroki_pominiete`, `kroki_zablokowane`, `zmiany`, `status` | requirement, fact, constraint | fact, requirement, risk, decision |
| 7a | `jak` | pytanie "jak" + kontekst projektu (always_on, bez jawnej sekcji Wejście) | `.ai-kb`, kod, `ŹRÓDŁA` | odpowiedź oparta na źródłach prawdy + zapis do `.ai-kb` | fact, relationship | fact, relationship, decision |
| 7b | `context7` | nazwa biblioteki/frameworka | wersja, zakres | aktualna dokumentacja + przykłady kodu | requirement | fact |
| 8 | `weryfikacja` | `TWIERDZENIE LUB ZBIOR TWIERDZEN` | `KRYTERIUM WERYFIKACJI`, `ŹRÓDŁA`, `TRYB WERYFIKACJI`, `ZAKRES`, `DOZWOLONE ŹRÓDŁA ZEWNĘTRZNE`, `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` | werdykty (T1, T2...) z `Status` (potwierdzony/obalony/niezweryfikowany/sprzeczny), `Źródło`, `Metoda`, `Uzasadnienie` + `Konflikty źródeł` + `Braki dowodowe` + `Podsumowanie` | fact, constraint, relationship | fact, relationship, constraint |
| 9 | `sprawdzenie` | `PYTANIE ŹRÓDŁOWE` + (`ODPOWIEDŹ DO OCENY` LUB `ARTEFAKT DO AUDYTU`) | `TRYB AUDYTU`, `KONTEKST DODATKOWY`, `ŹRÓDŁA PRAWDY`, `KRYTERIA OCENY`, `OGRANICZENIA DZIEDZINOWE`, `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI`, `DOZWOLONE ŹRÓDŁA ZEWNĘTRZNE`, `FORMAT OCZEKIWANEJ POPRAWKI` | `STATUS AUDYTU`, `OCENA CAŁKOWITA`, `WERDYKT`, wymiary (Zgodność, Kompletność, Poprawność logiczna, Poprawność merytoryczna, Spójność ontologiczna, Bezpieczeństwo, Użyteczność), `POPRAWIONA ODPOWIEDŹ` | requirement, fact, constraint | fact, requirement, constraint, risk, relationship |
| 10 | `ewaluacja` | `ROZWIĄZANIE LUB ARTEFAKT` | `CEL ŹRÓDŁOWY`, `KRYTERIA EWALUACJI`, `HORYZONT`, `ŹRÓDŁA`, `TRYB EWALUACJI` | `typ_ewaluacji`, `ocena_ogolna`, `wymiary` (Trafność, Skuteczność, Wydajność, Trwałość, Skalowalność), `wnioski`, `rekomendacje`, `status` | entity, requirement, constraint, fact | metric, fact, requirement, decision |
| 11 | `utrwal` | `WNIOSKI LUB DECYZJE DO ZAPISANIA` | `TYP WIEDZY`, `CEL`, `ŹRÓDŁA`, `TRYB UTRWALANIA` | `typ_wiedzy`, `miejsca_zapisu`, `akcje`, `status` | decision, fact, requirement | decision, fact, entity |
| 12 | `monitoruj` | `ZADANIE LUB PLAN` | `CHECKPOINTY`, `METRYKI`, `ŹRÓDŁA`, `TRYB MONITOROWANIA` | `checkpointy`, `blokady`, `odchylenia`, `warunki_przejscia`, `status` | requirement, metric, fact | metric, risk, fact, requirement |
| 13 | `audyt_runu` | `RUN_ID` | `TRYB AUDYTU`, `ZAKRES`, `ŹRÓDŁA` | `wymiary_audytu`, `ocena_calkowita`, `liczba_anomalii`, `anomalie`, `rekomendacje`, `status` | fact, entity | fact, risk, requirement |

## Uwagi do kontraktów

1. **`jak` i `context7`** nie mają standardowej sekcji `Wejście`/`Wynik` w formacie YAML - są skillami pomocniczymi (always_on / narzędziowymi). Ich kontrakt jest niejawny: `jak` dostarcza zasad odpowiedzi na pytania "jak", a `context7` dostarcza dokumentację bibliotek.
2. **`zmienne`** jest jedyną stacją, która operuje na pełnej ontologii 12 typów zmiennych. Pozostałe stacje używają podzbioru. Zadanie ekstrakcji wymagało 4 typów (`fact`, `requirement`, `constraint`, `relationship`), które są obecne w kontraktach wszystkich stacji merytorycznych.
3. **Tryby** (`szybki`/`pełny`/`dogłębny`) są wspólne dla wszystkich stacji merytorycznych i wpływają na głębokość wyjścia, ale nie zmieniają struktury kontraktu.
4. **Źródła prawdy** są identyczne dla wszystkich stacji: `.ai-kb` -> Context7 -> notebooklm-mcp -> Memgraph MCP, z konfliktami rozstrzyganymi przez `_shared/zrodla-i-narzedzia.md`.
5. **Bramka kompletności wejścia**: każda stacja ma sekcję `Kontrola kompletności wejścia` określającą, kiedy poprosić o doprecyzowanie vs. oznaczyć jako `agent_inference`/`unavailable`.

## Mapowanie kontraktów pole-po-polu między stacjami

Mapowanie rozstrzyga konflikty T1, T2, T3 z weryfikacji (Krok 3). Każde mapowanie wskazuje pole wyjścia stacji źródłowej, pole wejścia stacji docelowej, typ transformacji i status.

Legenda statusów mapowania:
- `bezpośrednie` - pole wyjścia mapuje się 1:1 na pole wejścia. W kopercie: pole trafia do `pola_stacji.<stacja_zrodlowa>`, stacja docelowa odczytuje z koperty.
- `wnioskowane` - pole wejścia jest wyprowadzane z pól wyjścia przez transformację agenta (oznaczone `agent_inference`). W kopercie: stacja docelowa wyprowadza pole z `pola_stacji`, wynik zapisuje w swojej sekcji.
- `kontekstowe` - pole wejścia pochodzi z `stan.zamiar` w kopercie (zamiar użytkownika przekazywany przez pipeline), nie z wyjścia stacji źródłowej.
- `brak` - pole wejścia nie ma odpowiednika w wyjściu stacji źródłowej; stacja docelowa musi je pozyskać inaczej (pytanie do użytkownika, własne źródła). W kopercie: wynik zapisuje w swojej sekcji `pola_stacji`.

Specyfikacja koperty i checkpointowania: patrz `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### inicjuj -> zmienne

| Pole wyjścia `inicjuj` | Pole wejścia `zmienne` | Status | Uwagi |
| --- | --- | --- | --- |
| `klasyfikacja` | (decyzja czy uruchomić `zmienne`) | bezpośrednie | Jeśli `rutynowe`/`złożone` -> uruchom `zmienne`. |
| `punkt_wejscia` | (stacja startowa) | bezpośrednie | Wskazuje `zmienne` jako punkt wejścia. |
| `uzasadnienie` | `context` (opcjonalne) | wnioskowane | Uzasadnienie klasyfikacji wzbogaca kontekst. |
| `ryzyka` | `context` (opcjonalne) | wnioskowane | Ryzyka z `inicjuj` stają się ograniczeniami w `zmienne`. |
| (brak) | `task_goal` (wymagane) | kontekstowe | `task_goal` pochodzi z `ZAMIARU UŻYTKOWNIKA` przekazywanego przez kontekst konwersacji, nie z wyjścia `inicjuj`. |

### zmienne -> analiza (rozstrzyga T1)

| Pole wyjścia `zmienne` | Pole wejścia `analiza` | Status | Uwagi |
| --- | --- | --- | --- |
| `analysis_object.name` | `NAZWA OBIEKTU` (wymagane) | bezpośrednie | Pole `name` w strukturze `AnalysisObject` ze skilla `zmienne` mapuje się 1:1 na `NAZWA OBIEKTU`. **Rozstrzyga T1: mapowanie istnieje, ale było niejawne w `pipeline_sklills.md`.** |
| `variables` | `KONTEKST` (opcjonalne) | wnioskowane | Zmienne z `zmienne` dostarczają kontekstu dla analizy. |
| `sources_used` | `ŹRÓDŁA` (opcjonalne) | bezpośrednie | Źródła wykorzystane w `zmienne` przekazywane do `analiza`. |
| `relations` | `KONTEKST` (opcjonalne) | wnioskowane | Relacje między zmiennymi wzbogacają kontekst analizy. |
| `missing_data_resolution` | `KONTEKST` (opcjonalne) | wnioskowane | Braki danych z `zmienne` informują o ograniczeniach analizy. |
| (brak) | `ZAKRES` (opcjonalne) | brak | `ZAKRES` pochodzi od użytkownika lub jest wnioskowany w `analiza`. |
| (brak) | `TRYB ANALIZY` (opcjonalne) | brak | `TRYB ANALIZY` pochodzi od użytkownika lub domyślnie `pełny`. |

### analiza -> dekompozycja (rozstrzyga T2)

| Pole wyjścia `analiza` | Pole wejścia `dekompozycja` | Status | Uwagi |
| --- | --- | --- | --- |
| Sekcja 6 (Ograniczenia) + Sekcja 7 (Wnioski) raportu | `PROBLEM LUB CEL ZŁOŻONY` (wymagane) | wnioskowane | **Rozstrzyga T2: `analiza` nie zwraca sformułowanego problemu, ale sekcje 6 (Ograniczenia) i 7 (Wnioski) raportu analitycznego pozwalają wyprowadzić problem do dekompozycji przez transformację agenta.** Status `agent_inference`. Jeśli raport nie pozwala wyprowadzić problemu, `dekompozycja` pyta użytkownika. |
| Sekcja 3 (Relacje) raportu | `KONTEKST` (opcjonalne) | wnijkowane | Relacje z analizy dostarczają kontekstu dla dekompozycji. |
| Sekcja 6 (Ograniczenia) raportu | `OGRANICZENIA` (opcjonalne) | bezpośrednie | Ograniczenia z analizy mapują się na ograniczenia dekompozycji. |
| `Pewność rozpoznania` | `KONTEKST` (opcjonalne) | wnioskowane | Niska pewność rozpoznania sygnalizuje ryzyko dla dekompozycji. |
| (brak) | `ŹRÓDŁA` (opcjonalne) | kontekstowe | `ŹRÓDŁA` przekazywane z kontekstu konwersacji (od `zmienne`). |
| (brak) | `TRYB DEKOMPOZYCJI` (opcjonalne) | brak | Domyślnie `pełny` lub od użytkownika. |

### analiza -> dobierz (gdy pominięto dekompozycję)

| Pole wyjścia `analiza` | Pole wejścia `dobierz` | Status | Uwagi |
| --- | --- | --- | --- |
| Sekcja 7 (Wnioski) raportu | `CEL DOBORU` (wymagane) | wnioskowane | Wnioski z analizy pozwalają sformułować cel doboru. |
| Sekcja 2 (Struktura) raportu | `WARIANTY` (wymagane warunkowo) | wnijkowane | Składniki obiektu mogą być wariantami doboru. |
| `Pewność rozpoznania` | `KONTEKST` (opcjonalne) | wnioskowane | Pewność rozpoznania wpływa na rygor doboru. |

### dekompozycja -> dobierz

| Pole wyjścia `dekompozycja` | Pole wejścia `dobierz` | Status | Uwagi |
| --- | --- | --- | --- |
| `podproblemy` | `WARIANTY` (wymagane warunkowo) | wnioskowane | Podproblemy mogą być wariantami doboru, jeśli dobór dotyczy rozwiązania podproblemu. |
| `krytyczne` | `KRYTERIA` (opcjonalne) | wnijkowane | Krytyczność podproblemu staje się kryterium priorytetu. |
| `zaleznosci` | `KONTEKST` (opcjonalne) | bezpośrednie | Zależności między podproblemami dostarczają kontekstu doboru. |

### dobierz -> routing (rozstrzyga T3)

| Pole wyjścia `dobierz` | Pole wejścia `routing` | Status | Uwagi |
| --- | --- | --- | --- |
| (brak) | `ZAMIAR LUB PROBLEM` (wymagane) | kontekstowe | **Rozstrzyga T3: `ZAMIAR LUB PROBLEM` pochodzi z kontekstu konwersacji (zamiar użytkownika przekazywany od `inicjuj`), nie z wyjścia `dobierz`.** `dobierz` nie zwraca zamiaru - zamiar jest stałym elementem kontekstu pipeline'u. |
| `RYZYKA I WARUNKI REWIZJI` | `KONTEKST` (dodatkowy, nie jawne pole wejścia `routing`) | wnioskowane | **Rozstrzyga P6: ryzyka rekomendacji wariantu (np. "wariant X ryzykuje rozrost plików") to inny poziom abstrakcji niż ryzyko pipeline'u.** Ryzyka rekomendacji dostarczają kontekstu, ale nie mapują się bezpośrednio na `RYZYKO` w `routing`. Status `agent_inference`. |
| (brak) | `RYZYKO` (opcjonalne) | kontekstowe | **Rozstrzyga P6: `RYZYKO` w `routing` (niskie/średnie/wysokie) jest ryzykiem zadania/pipeline'u, wnioskowanym z kontekstu zadania (wpływ na system, odwracalność, stawka), nie z ryzyk rekomendacji `dobierz`.** Pochodzi z kontekstu konwersacji. |
| (brak) | `STAWKA DECYZYJNA` (opcjonalne) | wnijkowane | Stawka decyzyjna jest wnioskowana z kontekstu zadania (wpływ na system, odwracalność), nie z wyjścia `dobierz`. |
| `REKOMENDACJA` | (decyzja czy routing jest potrzebny) | bezpośrednie | Jeśli rekomendacja jest jednoznaczna i stawka niska, routing może być pominięty. |
| `NAJBLIŻSZY KROK` | `ZASOBY` (opcjonalne) | wnijkowane | Najbliższy krok z `dobierz` informuje o zasobach potrzebnych do realizacji. |

### dobierz -> planuj (gdy pominięto routing, ścieżka szybki/pełny)

| Pole wyjścia `dobierz` | Pole wejścia `planuj` | Status | Uwagi |
| --- | --- | --- | --- |
| `REKOMENDACJA` (główna) | `CEL DO ZAPLANOWANIA` (wymagane) | wnioskowane | Rekomendowany wariant staje się celem planowania. Status `agent_inference`. |
| `WARIANTY` + `PORÓWNANIE` | `KONTEKST` (opcjonalne) | bezpośrednie | Porównanie wariantów dostarcza kontekstu planowania. |
| `KRYTERIA` | `KRYTERIA SUKCESU` (opcjonalne) | wnioskowane | Kryteria doboru mapują się na kryteria sukcesu planu. |
| `RYZYKA I WARUNKI REWIZJI` | `OGRANICZENIA` (opcjonalne) | bezpośrednie | Ryzyka rekomendacji stają się ograniczeniami planu. |
| `NAJBLIŻSZY KROK` | (pierwszy krok planu) | bezpośrednie | Najbliższy krok z `dobierz` jest punktem startowym sekwencji planu. |

### routing -> planuj

| Pole wyjścia `routing` | Pole wejścia `planuj` | Status | Uwagi |
| --- | --- | --- | --- |
| `sciezka` | `TRYB PLANOWANIA` (opcjonalne) | wnijkowane | Ścieżka `szybki`/`pełny`/`dogłębny` mapuje się na tryb planowania. |
| `stacje_uruchomione` | `ZAKRES` (opcjonalne) | bezpośrednie | Stacje uruchomione określają zakres planowania. |
| `stacje_pominiete` | `ZAKRES` (opcjonalne) | bezpośrednie | Stacje pominięte wyłączają elementy z planu. |
| `stawka` | `HORYZONT` (opcjonalne) | wnioskowane | Wysoka stawka -> horyzont strategiczny; niska -> operacyjny. |
| `ryzyko` | `OGRANICZENIA` (opcjonalne) | wnijkowane | Wysokie ryzyko -> bardziej restrykcyjne ograniczenia. |

### planuj -> realizuj

| Pole wyjścia `planuj` | Pole wejścia `realizuj` | Status | Uwagi |
| --- | --- | --- | --- |
| Plan 7-sekcyjny (Kroki i sekwencja) | `PLAN DO ZREALIZOWANIA` (wymagane) | bezpośrednie | Sekcja 3 planu (Kroki i sekwencja) jest bezpośrednim wejściem `realizuj`. |
| Plan sekcja 4 (Zasoby) | `KONTEKST` (opcjonalne) | bezpośrednie | Zasoby z planu dostarczają kontekstu realizacji. |
| Plan sekcja 5 (Ryzyka) | `KONTEKST` (opcjonalne) | bezpośrednie | Ryzyka z planu informują o ograniczeniach realizacji. |

### realizuj -> weryfikacja

| Pole wyjścia `realizuj` | Pole wejścia `weryfikacja` | Status | Uwagi |
| --- | --- | --- | --- |
| `zmiany` | `TWIERDZENIE LUB ZBIOR TWIERDZEN` (wymagane) | wnioskowane | Zmiany z `realizuj` są transformowane na twierdzenia do weryfikacji (np. "funkcjonalność X działa zgodnie z planem"). Status `agent_inference`. |
| `status` | `KRYTERIUM WERYFIKACJI` (opcjonalne) | wnioskowane | Status `zakonczony`/`czesciowy`/`zablokowany` określa zakres weryfikacji. |
| `kroki_zablokowane` | `ZAKRES` (opcjonalne) | bezpośrednie | Zablokowane kroki wyłączają się z weryfikacji. |

### weryfikacja -> sprawdzenie

| Pole wyjścia `weryfikacja` | Pole wejścia `sprawdzenie` | Status | Uwagi |
| --- | --- | --- | --- |
| Werdykty (T1, T2...) + `POPRAWIONA ODPOWIEDŹ` (jeśli) | `ODPOWIEDŹ DO OCENY` LUB `ARTEFAKT DO AUDYTU` (wymagane) | bezpośrednie | Werdykty weryfikacji + poprawiona odpowiedź są artefaktem do audytu. |
| (brak) | `PYTANIE ŹRÓDŁOWE` (wymagane) | kontekstowe | **Rozstrzyga P7: `PYTANIE ŹRÓDŁOWE` pochodzi z kontekstu konwersacji (zamiar użytkownika przekazywany od `inicjuj`), nie z wyjścia `weryfikacja`.** `Podsumowanie` z `weryfikacja` nie jest pytaniem źródłowym - to podsumowanie wyników weryfikacji. |
| `Konflikty źródeł` | `ŹRÓDŁA PRAWDY` (opcjonalne) | bezpośrednie | Konflikty źródeł z weryfikacji dostarczają kontekstu audytu. |
| `Braki dowodowe` | `KRYTERIA OCENY` (opcjonalne) | wnijkowane | Braki dowodowe wskazują obszary wymagające uwagi w audycie. |

### sprawdzenie -> ewaluacja LUB utrwal (bramka jakości)

| Pole wyjścia `sprawdzenie` | Pole wejścia `ewaluacja` | Status | Uwagi |
| --- | --- | --- | --- |
| `STATUS AUDYTU` + `WERDYKT` | (decyzja bramki: zgodny/niezgodny) | bezpośrednie | `zgodny` -> `ewaluacja` (lub `utrwal` w ścieżce pełny). `niezgodny` -> powrót do `dobierz`/`planuj`. |
| `POPRAWIONA ODPOWIEDŹ` | `ROZWIĄZANIE LUB ARTEFAKT` (wymagane) | bezpośrednie | Poprawiona odpowiedź jest rozwiązaniem do ewaluacji. |
| `OCENA CAŁKOWITA` | `KRYTERIA EWALUACJI` (opcjonalne) | wnijkowane | Ocena całkowita informuje o kryteriach ewaluacji. |

| Pole wyjścia `sprawdzenie` | Pole wejścia `utrwal` | Status | Uwagi |
| --- | --- | --- | --- |
| `WERDYKT` + wymiary audytu | `WNIOSKI LUB DECYZJE DO ZAPISANIA` (wymagane) | wnioskowane | Werdykt i wymiary audytu są transformowane na wnioski do utrwalenia. |
| `POPRAWIONA ODPOWIEDŹ` | `CEL` (opcjonalne) | wnijkowane | Poprawiona odpowiedź informuje o celu utrwalenia. |

### sprawdzenie -> dobierz/planuj (pętla bramki jakości, niezgodny)

Uruchamiane, gdy `sprawdzenie` zwraca status `niezgodny`. Limit 2 iteracji, potem eskalacja do użytkownika.

| Pole wyjścia `sprawdzenie` | Pole wejścia `dobierz` (powrót) | Status | Uwagi |
| --- | --- | --- | --- |
| `WERDYKT` + wymiary audytu | `CEL DOBORU` (wymagane) | wnioskowane | Werdykt niezgodności wskazuje, co trzeba dobrać na nowo. |
| `POPRAWIONA ODPOWIEDŹ` | `WARIANTY` (wymagane warunkowo) | wnijkowane | Poprawiona odpowiedź sugeruje nowe warianty do rozważenia. |
| Wymiary audytu (Zgodność, Kompletność) | `KRYTERIA` (opcjonalne) | wnijkowane | Wymiary niezgodności stają się nowymi kryteriami doboru. |

| Pole wyjścia `sprawdzenie` | Pole wejścia `planuj` (powrót) | Status | Uwagi |
| --- | --- | --- | --- |
| `WERDYKT` + wymiary audytu | `CEL DO ZAPLANOWANIA` (wymagane) | wnioskowane | Werdykt niezgodności wskazuje, co trzeba zaplanować na nowo. |
| `POPRAWIONA ODPOWIEDŹ` | `KONTEKST` (opcjonalne) | bezpośrednie | Poprawiona odpowiedź dostarcza kontekstu do rewizji planu. |
| Wymiary audytu (Poprawność logiczna, Kompletność) | `OGRANICZENIA` (opcjonalne) | wnijkowane | Wymiary niezgodności stają się ograniczeniami zrewidowanego planu. |

### ewaluacja -> utrwal

| Pole wyjścia `ewaluacja` | Pole wejścia `utrwal` | Status | Uwagi |
| --- | --- | --- | --- |
| `wnioski` | `WNIOSKI LUB DECYZJE DO ZAPISANIA` (wymagane) | bezpośrednie | Wnioski z ewaluacji są bezpośrednim wejściem utrwalania. |
| `rekomendacje` | `WNIOSKI LUB DECYZJE DO ZAPISANIA` (wymagane) | bezpośrednie | Rekomendacje są dodatkowymi wnioskami do zapisu. |
| `typ_ewaluacji` | `TYP WIEDZY` (opcjonalne) | wnijkowane | Typ ewaluacji wskazuje typ wiedzy do utrwalenia (np. `skutecznościowa` -> `wzorzec`). |

### utrwal -> monitoruj LUB audyt_runu LUB koniec

| Pole wyjścia `utrwal` | Pole wejścia `monitoruj`/`audyt_runu` | Status | Uwagi |
| --- | --- | --- | --- |
| `status` | (decyzja czy monitorować/audytować) | bezpośrednie | `zapisany` -> `monitoruj` (w ścieżce dogłębny) lub `audyt_runu` (weryfikacja ex-post) lub koniec (w ścieżce pełny). |
| `miejsca_zapisu` | `ZADANIE LUB PLAN` (wymagane, `monitoruj`) | wnijkowane | Miejsca zapisu informują, co monitorować. |
| `akcje` | `CHECKPOINTY` (opcjonalne, `monitoruj`) | wnijkowane | Akcje utrwalania mogą być checkpointami monitorowania. |
| `checkpoint_zapisany` + `manifest_zaktualizowany` | `RUN_ID` (wymagane, `audyt_runu`) | bezpośrednie | `utrwal` zapisuje checkpoint i manifest, `audyt_runu` odczytuje `RUN_ID` do weryfikacji ex-post. |
| `graf_zapisany` | (warunek uruchomienia `audyt_runu`) | bezpośrednie | `audyt_runu` wymaga grafu w Memgraph; jeśli `graf_zapisany: false`, audyt jest ograniczony do checkpointów plikowych. |

## Mapowanie typologiczne między stacjami

Mapowanie rozstrzyga konflikty P8-P11 z audytu (Krok 5). Pokazuje, jak typy zmiennych wyjścia stacji N przekształcają się na typy wejścia stacji N+1. Typy klasyfikowane są według ontologii ze skilla `zmienne` (12 typów).

Legenda:
- `1:1` - typ wyjścia mapuje się bezpośrednio na typ wejścia.
- `transformacja` - typ wyjścia jest przekształcany na typ wejścia przez transformację agenta.
- `kontekstowe` - typ wejścia pochodzi z `stan.zamiar` w kopercie, nie z wyjścia stacji źródłowej.
- `nadmiarowe` - typ wyjścia nie ma odbiorcy w wejściu stacji docelowej; pozostaje w sekcji `pola_stacji.<stacja_zrodlowa>` w kopercie, ale nie jest jawnie mapowany do wejścia stacji docelowej.

| Para stacji | Typy wyjścia N | Typy wejścia N+1 | Mapowanie | Uwagi |
| --- | --- | --- | --- | --- |
| `inicjuj` -> `zmienne` | decision, risk, fact | fact, requirement, constraint, relationship (12 typów) | `decision` -> `requirement` (transformacja), `risk` -> `constraint` (transformacja), `fact` -> `fact` (1:1) | `zmienne` przyjmuje wszystkie typy, więc nadmiarowych nie ma. |
| `zmienne` -> `analiza` | 12 typów | entity, constraint, fact | `entity` -> `entity` (1:1), `fact` -> `fact` (1:1), `constraint` -> `constraint` (1:1), `requirement`/`assumption`/`hypothesis`/`metric`/`risk`/`decision`/`preference`/`unknown` -> `KONTEKST` (nadmiarowe) | **Rozstrzyga P8:** `analiza` przyjmuje tylko 3 typy; 9 typów z `zmienne` pozostaje w kontekście konwersacji jako nadmiarowe. |
| `analiza` -> `dekompozycja` | entity, relationship, fact, constraint, risk | requirement, constraint, fact | `entity` -> `requirement` (transformacja), `relationship` -> `requirement` (transformacja), `fact` -> `fact` (1:1), `constraint` -> `constraint` (1:1), `risk` -> `constraint` (transformacja) | **Rozstrzyga P9:** `entity` i `relationship` są przekształcane na `requirement` (podproblemy jako wymagania). `risk` na `constraint` (ryzyka jako ograniczenia dekompozycji). |
| `analiza` -> `dobierz` | entity, relationship, fact, constraint, risk | requirement, entity, constraint, preference, fact | `entity` -> `entity` (1:1), `fact` -> `fact` (1:1), `constraint` -> `constraint` (1:1), `relationship` -> `requirement` (transformacja), `risk` -> `constraint` (transformacja) | Brak nadmiarowych - `dobierz` przyjmuje 5 typów. |
| `dekompozycja` -> `dobierz` | entity, relationship, constraint, requirement | requirement, entity, constraint, preference, fact | `entity` -> `entity` (1:1), `requirement` -> `requirement` (1:1), `constraint` -> `constraint` (1:1), `relationship` -> `requirement` (transformacja) | `preference` i `fact` w wejściu `dobierz` pochodzą z kontekstu (kontekstowe). |
| `dobierz` -> `routing` | decision, entity, requirement, constraint, risk, fact | requirement, constraint | `decision` -> `requirement` (transformacja), `requirement` -> `requirement` (1:1), `constraint` -> `constraint` (1:1), `entity`/`risk`/`fact` -> nadmiarowe | **Rozstrzyga P10:** `decision` (rekomendacja) jest przekształcana na `requirement` (wymaganie ścieżki). `entity`, `risk`, `fact` pozostają w kontekście. |
| `dobierz` -> `planuj` (gdy pominięto routing) | decision, entity, requirement, constraint, risk, fact | requirement, constraint, fact | `decision` -> `requirement` (transformacja), `requirement` -> `requirement` (1:1), `constraint` -> `constraint` (1:1), `fact` -> `fact` (1:1), `entity`/`risk` -> nadmiarowe | `entity` i `risk` pozostają w kontekście konwersacji. |
| `routing` -> `planuj` | decision, constraint, relationship | requirement, constraint, fact | `decision` -> `requirement` (transformacja), `constraint` -> `constraint` (1:1), `relationship` -> `requirement` (transformacja) | `fact` w wejściu `planuj` pochodzi z kontekstu (kontekstowe). |
| `planuj` -> `realizuj` | requirement, constraint, assumption, risk, metric, entity | requirement, fact, constraint | `requirement` -> `requirement` (1:1), `constraint` -> `constraint` (1:1), `assumption` -> `fact` (transformacja), `risk` -> `constraint` (transformacja), `metric` -> `fact` (transformacja), `entity` -> `fact` (transformacja) | `assumption`, `metric`, `entity` są przekształcane na `fact` (założenia i metryki jako fakty planu). |
| `realizuj` -> `weryfikacja` | fact, requirement, risk, decision | fact, constraint, relationship | `fact` -> `fact` (1:1), `requirement` -> `constraint` (transformacja), `risk` -> `constraint` (transformacja), `decision` -> `relationship` (transformacja) | **Rozstrzyga P11:** `requirement` na `constraint` (wymagania jako kryteria weryfikacji), `decision` na `relationship` (decyzje jako relacje między twierdzeniami a stanem faktycznym). |
| `weryfikacja` -> `sprawdzenie` | fact, relationship, constraint | requirement, fact, constraint, risk, relationship | `fact` -> `fact` (1:1), `relationship` -> `relationship` (1:1), `constraint` -> `constraint` (1:1) | `requirement` i `risk` w wejściu `sprawdzenie` pochodzą z kontekstu (kontekstowe). |
| `sprawdzenie` -> `ewaluacja` | fact, requirement, constraint, risk, relationship | entity, requirement, constraint, fact | `fact` -> `fact` (1:1), `requirement` -> `requirement` (1:1), `constraint` -> `constraint` (1:1), `risk` -> `constraint` (transformacja), `relationship` -> `entity` (transformacja) | `entity` w wejściu `ewaluacja` pochodzi z transformacji `relationship`. |
| `sprawdzenie` -> `utrwal` | fact, requirement, constraint, risk, relationship | decision, fact, requirement | `fact` -> `fact` (1:1), `requirement` -> `requirement` (1:1), `constraint` -> `decision` (transformacja), `risk` -> `decision` (transformacja), `relationship` -> `decision` (transformacja) | Wymiary audytu są przekształcane na decyzje do zapisu. |
| `ewaluacja` -> `utrwal` | metric, fact, requirement, decision | decision, fact, requirement | `decision` -> `decision` (1:1), `fact` -> `fact` (1:1), `requirement` -> `requirement` (1:1), `metric` -> `fact` (transformacja) | `metric` na `fact` (metryki jako fakty ewaluacji). |
| `utrwal` -> `monitoruj` | decision, fact, entity | requirement, metric, fact | `fact` -> `fact` (1:1), `decision` -> `requirement` (transformacja), `entity` -> `metric` (transformacja) | `decision` na `requirement` (decyzje jako wymagania monitorowania), `entity` na `metric` (encje jako metryki postępu). |
| `utrwal` -> `audyt_runu` | decision, fact, entity | fact, entity | `fact` -> `fact` (1:1), `entity` -> `entity` (1:1), `decision` -> `fact` (transformacja) | `decision` na `fact` (decyzje utrwalenia jako fakty do audytu). `audyt_runu` odczytuje `RUN_ID` z manifestu, nie z koperty. |

### Wzorce transformacji typologicznej

Powtarzające się transformacje między stacjami:

| Z typu | Na typ | Wzorzec | Przykład |
| --- | --- | --- | --- |
| `entity` | `requirement` | Obiekt staje się wymaganiem do zrealizowania | Podproblem (entity) -> wymaganie dekompozycji |
| `relationship` | `requirement` | Zależność staje się wymaganiem kolejności | Zależność między podproblemami -> wymaganie sekwencji |
| `risk` | `constraint` | Ryzyko staje się ograniczeniem | Ryzyko migracji -> ograniczenie planu |
| `decision` | `requirement` | Decyzja staje się wymaganiem wykonania | Rekomendacja wariantu -> wymaganie planu |
| `assumption` | `fact` | Założenie staje się faktem planu | Założenie o zasobach -> fakt planu |
| `metric` | `fact` | Metryka staje się faktem ewaluacji | Metryka sukcesu -> fakt ewaluacji |
| `entity` | `metric` | Encja staje się metryką postępu | Encja zapisu -> metryka monitorowania |

## Rozstrzygnięcia konfliktów z weryfikacji (Krok 3)

| Konflikt | Rozstrzygnięcie | Status po rozstrzygnięciu |
| --- | --- | --- |
| **T1** (`zmienne` -> `analiza`) | `analysis_object.name` z `zmienne` mapuje się 1:1 na `NAZWA OBIEKTU` w `analiza`. Mapowanie było niejawne w `pipeline_sklills.md`, ale istnieje w strukturze `AnalysisObject` skilla `zmienne`. | `potwierdzony` (mapowanie istnieje) |
| **T2** (`analiza` -> `dekompozycja`) | `analiza` nie zwraca sformułowanego problemu, ale sekcje 6 (Ograniczenia) i 7 (Wnioski) raportu pozwalają wyprowadzić `PROBLEM LUB CEL ZŁOŻONY` przez transformację agenta (`agent_inference`). Jeśli raport nie pozwala, `dekompozycja` pyta użytkownika. | `potwierdzony warunkowo` (mapowanie wnioskowane, nie bezpośrednie) |
| **T3** (`dobierz` -> `routing`) | `ZAMIAR LUB PROBLEM` pochodzi z `stan.zamiar` w kopercie (nie z `dobierz`). `RYZYKO` jest wnioskowane z `RYZYKA I WARUNKI REWIZJI` z `dobierz`. `STAWKA DECYZYJNA` jest wnioskowana z kontekstu zadania. | `potwierdzony warunkowo` (mapowanie kontekstowe + wnioskowane, nie bezpośrednie) |

## Mapowanie pól kontraktu na sekcje koperty

Każde pole wejścia stacji docelowej pochodzi z jednej z sekcji koperty emitowanej przez stację źródłową. Poniższa tabela wskazuje, z której sekcji koperty stacja docelowa odczytuje każde pole wymagane.

| Stacja docelowa | Pole wejścia wymagane | Sekcja koperty | Stacja źródłowa w kopercie |
| --- | --- | --- | --- |
| `zmienne` | `task_goal` | `stan.zamiar` | `inicjuj` (kontekstowe) |
| `analiza` | `NAZWA OBIEKTU` | `pola_stacji.zmienne.analysis_object.name` | `zmienne` (bezpośrednie) |
| `dekompozycja` | `PROBLEM LUB CEL ZŁOŻONY` | `pola_stacji.analiza.raport_streszczenie` | `analiza` (wnioskowane) |
| `dobierz` | `CEL DOBORU` | `pola_stacji.dekompozycja.podproblemy` lub `stan.zamiar` | `dekompozycja` lub `analiza` (wnioskowane) |
| `routing` | `ZAMIAR LUB PROBLEM` | `stan.zamiar` | `inicjuj` (kontekstowe) |
| `planuj` | `CEL DO ZAPLANOWANIA` | `pola_stacji.dobierz.rekomendacja` lub `pola_stacji.routing.sciezka` | `dobierz` lub `routing` (wnioskowane) |
| `realizuj` | `PLAN DO ZREALIZOWANIA` | `pola_stacji.planuj.plan` | `planuj` (bezpośrednie) |
| `weryfikacja` | `TWIERDZENIE LUB ZBIOR TWIERDZEN` | `pola_stacji.realizuj.zmiany` | `realizuj` (wnioskowane) |
| `sprawdzenie` | `PYTANIE ŹRÓDŁOWE` | `stan.zamiar` | `inicjuj` (kontekstowe) |
| `sprawdzenie` | `ODPOWIEDŹ DO OCENY` / `ARTEFAKT` | `pola_stacji.realizuj.zmiany` + `pola_stacji.weryfikacja.werdykty` | `realizuj` + `weryfikacja` (wnioskowane) |
| `ewaluacja` | `ROZWIĄZANIE LUB ARTEFAKT` | `pola_stacji.realizuj.zmiany` | `realizuj` (wnioskowane) |
| `ewaluacja` | `CEL ŹRÓDŁOWY` | `stan.zamiar` | `inicjuj` (kontekstowe) |
| `utrwal` | `WNIOSKI LUB DECYZJE` | `pola_stacji.ewaluacja.wnioski` lub `pola_stacji.sprawdzenie.werdykt` | `ewaluacja` lub `sprawdzenie` (wnioskowane) |
| `monitoruj` | `ZADANIE LUB PLAN` | `pola_stacji.planuj.plan` + `manifest.yaml` | `planuj` (bezpośrednie) |
| `audyt_runu` | `RUN_ID` | `manifest.yaml` + graf Memgraph | `utrwal` (bezpośrednie - run zakończony) |

Pełna specyfikacja koperty, checkpointowania i manifestu: patrz `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami"). Schemat grafu powiązań w Memgraph, mapowanie koperty na węzły/krawędzie i reguły integralności: patrz `_shared/graf-pipeline.md`.

## Sekcja `relacje` w kopercie

Oprócz pól kontraktowych mapowanych powyżej, koperta zawiera sekcję `relacje` deklarującą jawne powiązania między encjami w run'ie. Sekcja ta jest konsumowana przez `utrwal` przy zapisie do Memgraph i przez `audyt_runu` przy weryfikacji ex-post.

| Stacja źródłowa | Encje źródłowe | Encje docelowe | Typ relacji | Opis |
| --- | --- | --- | --- | --- |
| `inicjuj` | `stacja:inicjuj` | `stacja:zmienne` | `nastapila_po` | Kolejność stacji |
| `inicjuj` | `run:<run_id>` | `stacja:inicjuj` | `zawiera` | Run zawiera stację |
| `zmienne` | `stacja:zmienne` | `zmienna:V001...` | `wyprodukowala` | Stacja produkuje zmienne |
| `zmienne` | `zmienna:V001` | `zmienna:V003` | `zalezy_od` | Zależność między zmiennymi |
| `dekompozycja` | `stacja:dekompozycja` | `podproblem:P1...` | `wyprodukowala` | Stacja produkuje podproblemy |
| `dekompozycja` | `podproblem:P1` | `podproblem:P2` | `zalezy_od` | Zależność między podproblemami |
| `dobierz` | `stacja:dobierz` | `decyzja:D001` | `wyprodukowala` | Stacja produkuje decyzję |
| `dobierz` | `decyzja:D001` | `zmienna:V001` | `oparta_na` | Decyzja oparta na zmiennej |
| `planuj` | `stacja:planuj` | `krok:K1...` | `wyprodukowala` | Stacja produkuje kroki planu |
| `planuj` | `krok:K1` | `podproblem:P1` | `rozwiazuje` | Krok rozwiązuje podproblem |
| `realizuj` | `stacja:realizuj` | `zmiana:Z1...` | `wyprodukowala` | Stacja produkuje zmiany |
| `realizuj` | `zmiana:Z1` | `krok:K1` | `realizuje` | Zmiana realizuje krok planu |
| `weryfikacja` | `stacja:weryfikacja` | `twierdzenie:T1...`, `werdykt:W1...` | `wyprodukowala` | Stacja produkuje twierdzenia i werdykty |
| `weryfikacja` | `werdykt:W1` | `twierdzenie:T1` | `dotyczy` | Werdykt dotyczy twierdzenia |
| `sprawdzenie` | `stacja:sprawdzenie` | `wymiar:WA1...` | `wyprodukowala` | Stacja produkuje wymiary audytu |
| `sprawdzenie` | `wymiar:WA1` | `zmiana:Z1` | `weryfikuje` | Wymiar weryfikuje zmianę |
| `ewaluacja` | `stacja:ewaluacja` | `wniosek:WN1...` | `wyprodukowala` | Stacja produkuje wnioski |
| `ewaluacja` | `wniosek:WN1` | `stacja:ewaluacja` | `wyprowadzony_z` | Wniosek wyprowadzony ze stacji |

Mapowanie typów relacji (wartości w kopercie) na etykiety krawędzi w Memgraph: patrz `_shared/graf-pipeline.md` (sekcja "Schemat krawędzi").
