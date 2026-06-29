---
name: sprawdzenie
description: Wielowymiarowy audyt odpowiedzi i artefaktów AI pod kątem zgodności z pytaniem, kompletności, logiki, źródeł, ontologii, bezpieczeństwa i użyteczności.
version: 3.1.0
argument-hint: "[PYTANIE ŹRÓDŁOWE] [ODPOWIEDŹ DO OCENY albo ARTEFAKT DO AUDYTU] [opcjonalnie: TRYB AUDYTU, ŹRÓDŁA, KRYTERIA]"
triggers:
  - user
  - model
---

# Workflow wielowymiarowego audytu odpowiedzi i artefaktów AI

Celem tego workflowu jest rzetelny, wielowymiarowy audyt odpowiedzi albo artefaktu AI pod kątem zgodności z pytaniem źródłowym, kompletności, poprawności logicznej, poprawności merytorycznej, zgodności ze źródłami, spójności pojęciowej, bezpieczeństwa oraz praktycznej użyteczności.

Ocena ontologiczna jest jednym z modułów audytu, a nie jedynym zakresem sprawdzania.

## Rola

Przyjmij rolę eksperta od ewaluacji odpowiedzi AI, inżynierii wiedzy, walidacji źródeł, logiki argumentacji i audytu jakości informacji.

## Kiedy stosować

Stosuj, gdy użytkownik chce:
- sprawdzić odpowiedź AI,
- porównać odpowiedź z pytaniem źródłowym,
- wykryć błędy logiczne, faktograficzne, zakresowe, pojęciowe lub źródłowe,
- ocenić kompletność odpowiedzi,
- sprawdzić zgodność z dostarczonymi źródłami,
- ocenić bezpieczeństwo, ryzyka albo praktyczną użyteczność odpowiedzi,
- otrzymać poprawioną wersję odpowiedzi.

## Kiedy nie stosować

Nie stosuj, gdy:
- użytkownik nie dostarczył odpowiedzi ani artefaktu do audytu i nie wskazał, co zweryfikować,
- użytkownik prosi o wygenerowanie kodu, konfiguracji albo plików zamiast audytu,
- użytkownik prosi o czysty research od zera bez materiału do oceny,
- zadanie wymaga analizy obiektu zamiast audytu odpowiedzi - użyj skilla `analiza`.

## Zasady pracy

1. Oceniaj wyłącznie sekcję `ODPOWIEDŹ DO OCENY` albo `ARTEFAKT DO AUDYTU`.
2. Traktuj `PYTANIE ŹRÓDŁOWE` jako źródło celu, zakresu i kryterium trafności odpowiedzi.
3. `KONTEKST DODATKOWY` i `ŹRÓDŁA PRAWDY` wykorzystuj pomocniczo, nie jako substytut odpowiedzi.
4. Nie zakładaj brakujących definicji, faktów, źródeł ani relacji, jeśli nie wynikają z materiału albo ze zweryfikowanych źródeł.
5. Jeśli wejście jest niepełne, przerwij pełny audyt i zgłoś brakujące dane.
6. Oddzielaj od siebie: błąd faktograficzny, błąd logiczny, błąd kategorialny, słabą relację, ukryte założenie, brakujący element, ryzyko i ograniczenie audytu.
7. Nie myl krytyki odpowiedzi z uzupełnianiem wiedzy dziedzinowej, jeśli ta nie wynika z pytania ani ze źródeł.
8. Przy poprawianiu odpowiedzi zachowaj jej intencję, chyba że sama intencja narusza logikę, bezpieczeństwo, źródła albo zakres pytania.
9. Jeśli brak problemów w danej sekcji, wpisz jednoznacznie `Brak stwierdzonych problemów`.
10. Preferuj mniej ustaleń o wysokiej pewności zamiast wielu spekulacyjnych uwag.
11. W trybie audytu nie modyfikuj plików, nie uruchamiaj komend mutujących i nie wykonuj działań z efektami ubocznymi, chyba że użytkownik wyraźnie poprosi o wdrożenie poprawek.

## Wejście wymagane

Do pełnego audytu wymagane są:
- `PYTANIE ŹRÓDŁOWE`
- `ODPOWIEDŹ DO OCENY` albo `ARTEFAKT DO AUDYTU`

Opcjonalnie:
- `TRYB AUDYTU`
- `KONTEKST DODATKOWY`
- `ŹRÓDŁA PRAWDY`
- `KRYTERIA OCENY`
- `OGRANICZENIA DZIEDZINOWE`
- `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI`
- `DOZWOLONE ŹRÓDŁA ZEWNĘTRZNE`
- `FORMAT OCZEKIWANEJ POPRAWKI`

### Oznaczanie sekcji wejścia

Użytkownik dostarcza sekcje oznaczone jawnymi tagami lub nagłówkami:
- `PYTANIE ŹRÓDŁOWE:`
- `ODPOWIEDŹ DO OCENY:` albo `ARTEFAKT DO AUDYTU:`
- opcjonalnie `TRYB AUDYTU:`, `KONTEKST DODATKOWY:`, `ŹRÓDŁA PRAWDY:`, `KRYTERIA OCENY:`, `OGRANICZENIA DZIEDZINOWE:`, `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI:`, `DOZWOLONE ŹRÓDŁA ZEWNĘTRZNE:`, `FORMAT OCZEKIWANEJ POPRAWKI:`

Gdy sekcje nie są oznaczone, nie zgaduj, co jest pytaniem, a co odpowiedzią albo artefaktem. Najpierw poproś o rozgraniczenie materiału wejściowego.

## Kontrola kompletności wejścia

1. Jeśli brakuje `PYTANIA ŹRÓDŁOWEGO`, nie oceniaj zgodności z pytaniem w sposób pełny.
2. Jeśli brakuje `ODPOWIEDZI DO OCENY` i `ARTEFAKTU DO AUDYTU`, nie wykonuj audytu.
3. Jeśli wejście jest częściowe lub niejednoznaczne, ustaw status `ograniczony` albo `niemożliwy` i wskaż dokładnie, czego brakuje.
4. Nie wystawiaj punktowej oceny liczbowej, jeśli materiał nie pozwala na rzetelny audyt.
5. Jeśli brakuje źródeł dla audytu faktograficznego, oznacz twierdzenia jako `niezweryfikowane`, zamiast arbitralnie uznawać je za błędne.

## Tryby audytu

Jeśli użytkownik nie wskaże trybu, zastosuj tryb `pełny`.

Dostępne tryby:
- `szybki` - krótki werdykt, najważniejsze problemy i minimalna poprawka.
- `pełny` - domyślny audyt wielowymiarowy.
- `źródłowy` - zgodność z dostarczonymi albo zweryfikowanymi źródłami.
- `logiczny` - spójność rozumowania, sprzeczności, wnioskowanie, przyczynowość i warunki.
- `ontologiczny` - pojęcia, kategorie, relacje, założenia i poziomy abstrakcji.
- `techniczny` - odpowiedzi o kodzie, architekturze, konfiguracji, API, CLI albo narzędziach. Sprawdź: kompilowalność, bezpieczeństwo (OWASP), wydajność, zgodność z konwencjami projektu, obsługę błędów, pokrycie testami.
- `decyzyjny` - rekomendacje, warianty, kompromisy, ryzyka i kryteria wyboru.
- `bezpieczeństwa` - ryzyka prawne, techniczne, prywatnościowe, operacyjne albo zgodnościowe.
- `instrukcyjny` - procedury krok po kroku, kompletność instrukcji i wykonalność działań.

## Źródła prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pułapki.
2. Context7 - dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - notebooki i źródła badawcze użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zależności, graf wywołań, analiza architektury przez Cypher.

Stosuj w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi. Konflikty źródeł i hierarchia: patrz `_shared/zrodla-i-narzedzia.md`.

### Polityka oceny źródłowej

1. Najpierw oceniaj odpowiedź albo artefakt względem `PYTANIA ŹRÓDŁOWEGO`, `ODPOWIEDZI DO OCENY` albo `ARTEFAKTU DO AUDYTU` i dostarczonego kontekstu.
2. Jeśli użytkownik dostarczył źródła, traktuj je jako główną podstawę oceny faktograficznej.
3. Jeśli użytkownik nie dostarczył źródeł, nie oznaczaj twierdzeń jako fałszywych wyłącznie na podstawie domysłu.
4. Twierdzenia wymagające weryfikacji oznacz jako `niezweryfikowane`, jeśli brak źródeł.
5. Jeśli odpowiedź albo artefakt dotyczy biblioteki, frameworka, SDK, API, CLI albo konfiguracji, użyj aktualnej dokumentacji przez `Context7 MCP`, gdy narzędzia są dostępne i użytkownik dopuszcza źródła zewnętrzne. Dla kodu źródłowego projektu używaj `Serena MCP` do nawigacji semantycznej i weryfikacji symboli.
6. Jeśli użytkownik wyraźnie prosi o aktualną dokumentację, najnowsze źródła albo weryfikację zewnętrzną, traktuj to jako zgodę na użycie adekwatnych źródeł zewnętrznych.
7. Oddzielaj: fakt potwierdzony, sprzeczność ze źródłem, lukę w odpowiedzi, hipotezę i ocenę poza zakresem.
8. Jeśli źródła są sprzeczne, wskaż konflikt i nie rozstrzygaj go bez uzasadnienia.

## Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza architektury przez Cypher.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Koperta

`sprawdzenie` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty:
- `stan.zamiar` -> `PYTANIE ŹRÓDŁOWE` (wymagane, kontekstowe),
- `pola_stacji.realizuj.zmiany` + `pola_stacji.weryfikacja.werdykty` -> `ODPOWIEDŹ DO OCENY` / `ARTEFAKT DO AUDYTU` (wymagane, wnioskowane),
- `pola_stacji.zmienne.sources_used` -> `ŹRÓDŁA PRAWDY` (opcjonalne, bezpośrednie).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: sprawdzenie`,
- `stacja_poprzednia: weryfikacja`,
- `pola_stacji.sprawdzenie`: `status_audytu`, `ocena_calkowita`, `werdykt`, `wymiary` (7 wymiarów), `poprawiona_odpowiedz`,
- `walidacja.stacja_docelowa: ewaluacja` (lub `utrwal` w ścieżce pełny, lub `ROZWIĄZANIE` w ścieżce szybki),
- `walidacja.pola_wymagane` zależne od stacji docelowej,
- `relacje`:
  - `stacja:sprawdzenie` -> `stacja:ewaluacja` (lub `stacja:utrwal`) (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:sprawdzenie` (typ: `zawiera`),
  - `stacja:sprawdzenie` -> `wymiar:WA1`, `wymiar:WA2`, ... (typ: `wyprodukowala`, per wymiar audytu),
  - `wymiar:WA1` -> `zmiana:Z1` (typ: `weryfikuje`, per wymiar weryfikujący zmianę).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_09_sprawdzenie.yaml` i zaktualizuj manifest.

Jeśli `status_audytu` to `niezgodny`, bramka jakości wraca do `dobierz`/`planuj` (zwiększ `iteracja_bramki` w manifeście, zapisz nowy checkpoint z sufiksem `_iter<N>`, zapisz nową krawędź `NASTAPILA_PO` do Memgraph z adnotacją iteracji).

## Wymiary audytu

### 1. Zgodność z pytaniem

Sprawdź:
- czy odpowiedź realizuje cel pytania,
- czy nie odpowiada obok tematu,
- czy uwzględnia ograniczenia użytkownika,
- czy zachowuje oczekiwany poziom szczegółowości,
- czy nie pomija jawnych wymagań.

### 2. Kompletność

Sprawdź:
- czy brakuje kluczowych elementów,
- czy odpowiedź pomija warunki, wyjątki, zależności albo ograniczenia,
- czy użytkownik dostał wszystkie elementy potrzebne do użycia odpowiedzi,
- czy pominięcia zmieniają sens albo użyteczność odpowiedzi.

### 3. Poprawność logiczna

Sprawdź:
- czy rozumowanie jest spójne,
- czy nie ma sprzeczności wewnętrznych,
- czy wnioski wynikają z przesłanek,
- czy odpowiedź nie myli korelacji, współwystępowania i przyczynowości,
- czy warunki, skutki i wyjątki są poprawnie powiązane.

### 4. Poprawność merytoryczna i źródłowa

Sprawdź:
- czy twierdzenia są zgodne z dostępnymi źródłami,
- czy odpowiedź nie przedstawia hipotez lub interpretacji jako faktów,
- czy dane liczbowe, wersje, API, przepisy, terminy albo rekomendacje wymagają źródła,
- czy odpowiedź jasno oznacza niepewność,
- czy nie zawiera twierdzeń niemożliwych do sprawdzenia w dostarczonym materiale.

### 5. Spójność pojęciowa i ontologiczna

Sprawdź:
- czy pojęcia są jasno zdefiniowane,
- czy odpowiedź nie miesza kategorii, przykładów, procesów, przyczyn, skutków i cech,
- czy relacje między pojęciami są logicznie poprawne,
- czy zakres twierdzeń jest właściwie ograniczony,
- czy ukryte założenia są uzasadnione,
- czy odpowiedź tworzy spójny opis rzeczywistości.

### 6. Bezpieczeństwo i ryzyka

Sprawdź, jeśli ma zastosowanie:
- czy odpowiedź nie prowadzi do niebezpiecznych, nielegalnych albo nieuprawnionych działań,
- czy nie ignoruje ryzyk technicznych, prywatnościowych, prawnych, operacyjnych lub biznesowych,
- czy nie zaleca destrukcyjnych działań bez ostrzeżenia i potwierdzenia,
- czy nie ujawnia ani nie utrwala sekretów,
- czy nie obniża poziomu bezpieczeństwa systemu, danych lub użytkowników.

### 7. Zgodność z konwencjami projektu

Sprawdź, jeśli artefakt dotyczy kodu albo konfiguracji projektu:
- czy zachowuje styl kodowania i nazewnictwo projektu,
- czy stosuje istniejące w projekcie wzorce i abstrakcje,
- czy nie wprowadza obcych konwencji ani zależności bez uzasadnienia,
- czy jest spójny z architekturą opisaną w `.ai-kb/`, `docs/` albo pamięci Serena.

### 8. Wydajność i jakość kodu

Sprawdź w trybie `techniczny`, jeśli artefakt jest kodem:
- czy nie wprowadza zbędnej złożoności obliczeniowej albo pamięciowej,
- czy nie zawaje jawnych wąskich gardeł (pętle zagnieżdżone, N+1, synchroniczne IO),
- czy obsługa błędów i przypadków brzegowych jest adekwatna,
- czy kod jest pokryty albo pokrywalny testami.

### 9. Użyteczność praktyczna

Sprawdź:
- czy odpowiedź daje użytkownikowi realnie wykonalny rezultat,
- czy następne kroki są jasne,
- czy poziom szczegółowości pasuje do pytania,
- czy poprawka jest minimalna i zachowuje intencję odpowiedzi,
- czy forma odpowiedzi jest czytelna dla odbiorcy.

### 10. Zgodność z oczekiwanym formatem

Sprawdź:
- czy odpowiedź zachowuje wymagany format,
- czy nie pomija wymaganych sekcji,
- czy nie dodaje niechcianych elementów,
- czy język, styl i poziom szczegółowości odpowiadają instrukcji użytkownika.

## Skala oceny

Ocena liczbowa jest orientacyjna i nie zastępuje uzasadnienia w sekcjach wymiarowych.

- `90-100` - odpowiedź bardzo dobra, zgodna z pytaniem, kompletna, logiczna, źródłowo uzasadniona, pojęciowo spójna i praktycznie użyteczna.
- `70-89` - odpowiedź zasadniczo dobra, ale zawiera luki, skróty, nieprecyzyjne twierdzenia albo drobne braki.
- `40-69` - odpowiedź częściowo użyteczna, ale ma istotne błędy logiczne, faktograficzne, zakresowe, pojęciowe albo kompletnościowe.
- `0-39` - odpowiedź jest myląca, niezgodna z pytaniem, niespójna, niebezpieczna albo wymaga gruntownego przepisania.

## Procedura

1. Ustal, co w dostarczonym materiale jest pytaniem, a co odpowiedzią albo artefaktem do audytu.
2. Ustal `TRYB AUDYTU`; jeśli nie podano, użyj trybu `pełny`.
3. Sprawdź kompletność wejścia i w razie braków wstrzymaj pełny audyt.
4. Określ ograniczenia audytu, zwłaszcza brak źródeł, brak pytania źródłowego albo niejednoznaczny zakres.
5. Oceń zgodność odpowiedzi z pytaniem i instrukcjami użytkownika.
6. Oceń kompletność, logikę, merytorykę, źródła, ontologię, bezpieczeństwo, użyteczność i format zgodnie z trybem audytu.
7. Odróżnij problemy wysokiej pewności od twierdzeń niezweryfikowanych.
8. Wystaw ocenę liczbową tylko wtedy, gdy materiał jest wystarczający.
9. Zaproponuj minimalną poprawkę, która usuwa najważniejsze problemy i zachowuje intencję odpowiedzi.
10. Przy statusie `niemożliwy` wskaż, czego brakuje, zamiast przepisywać treść z domysłów.

## Format wyniku

### Format trybu `szybki`

W trybie `szybki` zwróć tylko:
- `STATUS AUDYTU`
- `TRYB AUDYTU`
- `OCENA CAŁKOWITA`
- `WERDYKT`
- maksymalnie 3 najważniejsze problemy
- `POPRAWIONA ODPOWIEDŹ`

Pomiń szczegółowe sekcje wymiarowe, chyba że zawierają problem wysokiego priorytetu.

### Gdy audyt jest pełny albo ograniczony

**STATUS AUDYTU:** [pełny|ograniczony]

**TRYB AUDYTU:** [szybki|pełny|źródłowy|logiczny|ontologiczny|techniczny|decyzyjny|bezpieczeństwa|instrukcyjny]

**OCENA CAŁKOWITA:** [0-100 albo nieustalona]

**OGRANICZENIA AUDYTU:**
[Krótki opis ograniczeń albo "Brak istotnych ograniczeń"]

**WERDYKT:**
[Krótka, konkretna ocena odpowiedzi]

**ZGODNOŚĆ Z PYTANIEM:**
[Ocena realizacji celu pytania]

**KOMPLETNOŚĆ:**
[Braki, pominięcia, nieobsłużone warunki albo "Brak stwierdzonych problemów"]

**POPRAWNOŚĆ LOGICZNA:**
[Sprzeczności, błędne wnioskowanie, słabe relacje przyczynowe albo "Brak stwierdzonych problemów"]

**POPRAWNOŚĆ MERYTORYCZNA I ŹRÓDŁOWA:**
[Fakty, źródła, twierdzenia niezweryfikowane albo "Brak stwierdzonych problemów"]

**SPÓJNOŚĆ POJĘCIOWA I ONTOLOGICZNA:**
[Błędy kategorialne, mylenie pojęć, relacje między bytami albo "Brak stwierdzonych problemów"]

**RYZYKA I BEZPIECZEŃSTWO:**
[Ryzyka prawne, techniczne, operacyjne, prywatnościowe albo "Brak stwierdzonych problemów"]

**NAJWAŻNIEJSZE PROBLEMY:**
[Tabela: priorytet, fragment, problem, dlaczego to problem, minimalna poprawka]

**NIEZWERYFIKOWANE TWIERDZENIA:**
[Lista albo "Brak stwierdzonych problemów"]

**POPRAWIONA ODPOWIEDŹ:**
[Poprawiona wersja zachowująca intencję odpowiedzi albo informacja, że odpowiedź nie wymaga korekty]

### Gdy audyt jest niemożliwy

**STATUS AUDYTU:** niemożliwy

**TRYB AUDYTU:** [ustalony albo nieustalony]

**OCENA CAŁKOWITA:** nieustalona

**BRAKUJĄCE DANE:**
[Lista brakujących elementów wejścia]

**POWÓD WSTRZYMANIA:**
[Krótka informacja, dlaczego pełny audyt byłby nierzetelny]

**PYTANIE UZUPEŁNIAJĄCE:**
[Jedno precyzyjne pytanie do użytkownika]

## Przykład minimalnego wejścia i wyjścia

### Wejście

```text
PYTANIE ŹRÓDŁOWE:
Czym różni się klasa od obiektu?

ODPOWIEDŹ DO OCENY:
Klasa to obiekt, który tworzy inne obiekty.
```

### Wyjście skrócone

```text
STATUS AUDYTU: pełny
TRYB AUDYTU: pełny
OCENA CAŁKOWITA: 55
OGRANICZENIA AUDYTU:
Brak istotnych ograniczeń.

WERDYKT:
Odpowiedź częściowo dotyczy pytania, ale miesza klasę z obiektem i fabryką obiektów.

ZGODNOŚĆ Z PYTANIEM:
Odpowiedź próbuje wyjaśnić różnicę, ale nie rozdziela jasno klasy jako abstrakcji i obiektu jako instancji.

SPÓJNOŚĆ POJĘCIOWA I ONTOLOGICZNA:
| priorytet | fragment | problem | dlaczego to problem | minimalna poprawka |
| --- | --- | --- | --- | --- |
| wysoki | "Klasa to obiekt" | Błąd kategorialny | Klasa jest wzorcem lub abstrakcją, a obiekt konkretną instancją | Rozdziel klasę jako definicję od obiektu jako instancji |

POPRAWIONA ODPOWIEDŹ:
Klasa to wzorzec lub abstrakcja definiująca stan i zachowanie obiektów. Obiekt to konkretna instancja utworzona na podstawie klasy.
```
