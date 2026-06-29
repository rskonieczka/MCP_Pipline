---
name: analiza
description: Uniwersalny prompt do analizy obiektów.
version: 2.0.0
argument-hint: "[NAZWA OBIEKTU]"
triggers:
  - user
  - model
---

# Uniwersalny Prompt do Analizy

## Rola

Przyjmij rolę eksperta od analizy obiektów i systemów, łączącego myślenie systemowe, analityczne i krytyczne.

## Kiedy stosować

Stosuj, gdy użytkownik prosi o analizę:
- rzeczy fizycznej,
- procesu,
- pojęcia abstrakcyjnego,
- organizacji,
- systemu informatycznego,
- artefaktu informacyjnego (dokument, tekst, raport, strona, instrukcja, regulamin),
- innego obiektu, którego typ rozpoznasz w toku analizy.

## Kiedy nie stosować

Nie stosuj, gdy użytkownik chce:
- audytu odpowiedzi albo artefaktu AI - użyj skilla `sprawdzenie`,
- podjęcia decyzji między wariantami albo wyboru jednej opcji z wielu,
- wygenerowania kodu, konfiguracji albo plików,
- czystego researchu bez wskazanego obiektu analizy.

## Język

Analizę prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:
- `NAZWA OBIEKTU`

Opcjonalnie:
- `KONTEKST` - środowisko, ograniczenia, sytuacja,
- `ZAKRES` - które sekcje pominąć albo pogłębić,
- `ŹRÓDŁA` - materiały bazowe,
- `TRYB ANALIZY` - `szybki`, `pełny`, `dogłębny` (domyślnie `pełny`),
- `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` - `skrócony`, `standardowy`, `dogłębny`.

## Kontrola kompletności wejścia

1. Jeśli brakuje `NAZWA OBIEKTU`, nie wykonuj analizy. Poproś o wskazanie obiektu.
2. Jeśli obiekt jest niejednoznaczny (wiele znaczeń), najpierw rozstrzygnij, które znaczenie analizujesz, albo poproś o doprecyzowanie.
3. Jeśli `ŹRÓDŁA` są wskazane, traktuj je jako główną podstawę faktograficzną.
4. Jeśli brakuje źródeł dla twierdzeń wymagających weryfikacji, oznaczaj je jako `niezweryfikowane`, zamiast arbitralnie uznawać za fałszywe.
5. Jeśli `ZAKRES` wyklucza kluczowe sekcje, potwierdź z użytkownikiem, że świadomie rezygnuje z ich analizy.

## Tryby analizy

Jeśli użytkownik nie wskaże trybu, zastosuj tryb `pełny`.

- `szybki` - rozpoznanie typu, sekcje 1 i 7 oraz najistotniejsze ustalenia z pozostałych sekcji. Krótki werdykt.
- `pełny` - domyślny: wszystkie sekcje 1-7 z adaptacją do typu obiektu.
- `dogłębny` - pełne sekcje 1-7, rozbudowane podsekcje, tabele, schematy analityczne, podsekcje specyficzne dla typu obiektu, jawne poziomy pewności.

`OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` mapuje się na tryb:
- `skrócony` -> `szybki`,
- `standardowy` -> `pełny`,
- `dogłębny` -> `dogłębny`.

Jeśli `TRYB ANALIZY` i `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` są sprzeczne, stosuj bardziej wnikliwy z nich.

## Źródła prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pułapki.
2. Context7 - dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - notebooki i źródła badawcze użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zależności, graf wywołań, analiza architektury przez Cypher.

Stosuj w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi. Konflikty źródeł, hierarchia i reguły uzupełniające: patrz `_shared/zrodla-i-narzedzia.md`.

Reguły specyficzne dla analizy:
- Twierdzenia wymagające weryfikacji oznaczaj jako `niezweryfikowane`, jeśli brak źródeł.
- Oddzielaj fakt potwierdzony od hipotezy i interpretacji.
- Jeśli źródła są sprzeczne, wskaż konflikt i nie rozstrzygaj go bez uzasadnienia.

## Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza architektury przez Cypher.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Koperta

`analiza` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty emitowanej przez `zmienne`:
- `pola_stacji.zmienne.analysis_object.name` -> `NAZWA OBIEKTU` (wymagane, bezpośrednie),
- `pola_stacji.zmienne.variables` -> `KONTEKST` (opcjonalne, wnioskowane),
- `pola_stacji.zmienne.sources_used` -> `ŹRÓDŁA` (opcjonalne, bezpośrednie),
- `pola_stacji.zmienne.relations` -> `KONTEKST` (opcjonalne, wnioskowane).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: analiza`,
- `stacja_poprzednia: zmienne`,
- `pola_stacji.analiza`: `raport_streszczenie` (skrót raportu 7-sekcyjnego), `pewnosc` (poziom pewności rozpoznania), `ograniczenia` (sekcja 6), `wnioski` (sekcja 7 - kluczowe dla `dekompozycja`),
- `walidacja.stacja_docelowa: dekompozycja` (lub `dobierz` gdy pominięto dekompozycję),
- `walidacja.pola_wymagane: [PROBLEM LUB CEL ZŁOŻONY]` -> wnioskowane z `wnioski` + `ograniczenia` (`agent_inference`),
- `relacje`:
  - `stacja:analiza` -> `stacja:dekompozycja` (lub `stacja:dobierz`) (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:analiza` (typ: `zawiera`).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_02_analiza.yaml` i zaktualizuj manifest.

## Instrukcja główna

Najpierw rozpoznaj, czym jest analizowany obiekt. Nie zakładaj z góry jego typu.

Możliwe typy:
- rzecz fizyczna,
- proces,
- pojęcie abstrakcyjne,
- organizacja,
- system informatyczny,
- artefakt informacyjny (dokument, tekst, raport, strona internetowa, instrukcja, regulamin itp.),
- inny typ, jeśli analiza wykaże taką potrzebę.

Po rozpoznaniu typu obiektu dostosuj zakres analizy. Nie stosuj wszystkich sekcji i podsekcji mechanicznie. Uwzględniaj wyłącznie te elementy, które mają znaczenie dla badanego obiektu.

Zasady adaptacji:
- Pomijaj podsekcje nie mające zastosowania, z jawnym oznaczeniem `Nie dotyczy dla tego typu obiektu.`
- Twórz podsekcje specyficzne dla typu obiektu, jeśli są istotne dla zrozumienia (np. `Automatyzacja` dla umiejętności, `Cykl życia` dla procesu, `Topologia` dla systemu informatycznego). Numeruj je w ramach sekcji nadrzędnej.
- Stosuj tabele tam, gdzie zwiększają czytelność (składniki, granice pojęcia, kryteria oceny, porównania).
- Stosuj schematy analityczne w blokach `text` tam, gdzie pokazują przepływ, architekturę albo zależności (np. architektura działania, wzór zależności).

Analiza ma opierać się na faktach, logicznych zależnościach i obserwowalnych cechach. Unikaj spekulacji oraz generowania treści bez podstaw.

---

Analiza obiektu: [NAZWA OBIEKTU]

## Rozpoznanie typu obiektu

Określ typ obiektu i uzasadnij, dlaczego tak go rozpoznajesz. Wskaż cechy decydujące o przynależności do typu (np. dyspozycyjny, relacyjny, materialny, procesualny, informacyjny).

Zakończ sekcję jawną deklaracją:

**Pewność rozpoznania: niski / średni / wysoki.**

Jeśli pewność jest niższa niż wysoki, wskaż, czego brakuje do pewniejszego rozpoznania.

---

## 1. Tożsamość

### 1.1. Definicja

- Czym jest analizowany obiekt?
- Jak można go jednoznacznie zdefiniować (definicja syntetyczna)?
- Jakie elementy łączy definicja (np. podmiot, działanie, cel, warunki, kryterium)?

### 1.2. Kategoria

- Do jakiej kategorii pojęciowej należy obiekt?
- Do jakich kategorii należy jednocześnie, jeśli ma charakter wielokategorialny?
- Czym obiekt nie jest, choć bywa z nim mylony (np. umiejętność a kompetencja, proces a struktura)?

### 1.3. Zakres

- Co należy do tego obiektu?
- Co nie należy do tego obiektu?
- Wskaż typowe przykłady wchodzące w zakres oraz przykłady pozostające poza zakresem.

### 1.4. Granice pojęcia

- Gdzie przebiegają granice obiektu względem pojęć pokrewnych?
- Dla obiektów abstrakcyjnych przedstaw tabelę pokrewnych pojęć z ich podstawowym pytaniem i przykładem, jeśli zwiększa to czytelność.

Przykładowy układ tabeli:

| Pojęcie | Podstawowe pytanie | Przykład |
| --- | --- | --- |
| ... | ... | ... |

### 1.5. Kontekst

- W jakim środowisku funkcjonuje?
- W jakich sytuacjach występuje?
- Czy kontekst wpływa na wartość albo skuteczność obiektu?

---

## 2. Struktura

### 2.1. Charakter struktury

- Czy obiekt ma strukturę materialną, funkcjonalną, logiczną, czy nie ma struktury?
- Jeśli nie ma struktury materialnej, czy można wyodrębnić strukturę funkcjonalną (elementy niezbędne do działania)?

### 2.2. Składniki kluczowe

- Z jakich elementów składa się obiekt?
- Które elementy są kluczowe i dlaczego?
- Dla obiektów o wielu składnikach przedstaw tabelę składników z ich znaczeniem.

### 2.3. Składniki pomocnicze

- Które elementy są pomocnicze, a nie kluczowe?
- Co wspiera działanie obiektu, nie będąc jego częścią?

### 2.4. Hierarchia

- Jakie występują poziomy organizacji?
- Jakie są zależności między częściami?
- Czy proste elementy łączą się w bardziej złożone układy?

### 2.5. Architektura

- W jaki sposób elementy są uporządkowane?
- Jak wygląda organizacja całości?
- Jeśli ma zastosowanie, przedstaw schemat analityczny w bloku `text` pokazujący przepływ albo architekturę działania.

---

## 3. Relacje

### 3.1. Relacje wewnętrzne

- Jak elementy obiektu wpływają na siebie nawzajem?
- Jakie występują zależności?
- Które zależności są przyczynowo-skutkowe, a które korelacyjne?

### 3.2. Relacje zewnętrzne

- Z czym obiekt współpracuje?
- Od czego jest zależny?
- Na co oddziałuje?
- Jeśli ma zastosowanie, przedstaw schemat analityczny zależności w bloku `text`.

### 3.3. Powiązania systemowe

- Jaką pełni rolę w szerszym kontekście (np. w systemie, organizacji, dziedzinie)?
- Jakie są jego wejścia i wyjścia?

Wyróżnij jawnie:

**Wejścia:**
- ...

**Wyjścia:**
- ...

---

## 4. Zachowanie

### 4.1. Funkcjonowanie

- Jak działa obiekt?
- Jak przebiegają jego procesy lub mechanizmy?
- W jaki sposób ujawnia się jego działanie (jeśli nie jest obserwowane bezpośrednio)?

### 4.2. Rozwój

- Jak obiekt powstaje, rozwija się albo nabywa swoje właściwości?
- Jakie etapy albo mechanizmy rozwoju można wyróżnić?
- Czy rozwój ma charakter sekwencyjny, równoległy, czy zależny od warunków?

### 4.3. Stany

- Jakie stany albo poziomy może przyjmować obiekt?
- Jakie są granice między stanami i na jakiej podstawie się je ustala?

### 4.4. Zmiany i dynamika

- Jak reaguje na zmiany otoczenia?
- Co inicjuje działanie?
- Co wpływa na jego zachowanie w danej chwili?
- Jakie występują skutki działania?

### 4.5. Wykonanie a posiadanie

Jeśli ma zastosowanie (np. dyspozycje, zdolności, procesy), odróżnij:
- względnie trwałą właściwość obiektu,
- jednorazowe wykonanie albo przejaw w konkretnej chwili.

Wskaż, czy pojedyncze zdarzenie jest wystarczającym dowodem, czy wymagany jest wzorzec wyników.

---

## 5. Cel

### 5.1. Funkcja podstawowa

- Po co istnieje analizowany obiekt?
- Jaki problem rozwiązuje?
- Jaką rozbieżność niweluje (np. między wiedzą a praktyką, zamiarem a wykonaniem)?

### 5.2. Funkcja pojęcia

Dla obiektów abstrakcyjnych odróżnij funkcję samego obiektu od funkcji pojęcia, które go opisuje:
- Do czego służy pojęcie w opisie, planowaniu, ocenie albo porównywaniu?

### 5.3. Wartość

- Jaką korzyść dostarcza obiekt?
- Dla kogo jest użyteczny?

Jeśli ma zastosowanie, rozbij wartość na kategorie odbiorców (np. jednostka, organizacja, społeczeństwo, użytkownik końcowy).

### 5.4. Efekty

- Jakie rezultaty powinien generować?
- Czym charakteryzuje się dobrze zrealizowane działanie obiektu?

### 5.5. Ocena skuteczności

- Jak można ocenić skuteczność realizacji celu?
- Jakie kryteria oceny mają zastosowanie?

Jeśli ma zastosowanie, przedstaw tabelę kryteriów z pytaniem oceniającym:

| Kryterium | Pytanie oceniające |
| --- | --- |
| ... | ... |

---

## 6. Ograniczenia

### 6.1. Ograniczenia wewnętrzne

- Jakie cechy konstrukcyjne, organizacyjne albo strukturalne ograniczają działanie?
- Czy obiekt jest podatny na utratę właściwości i w jakich warunkach?

### 6.2. Ograniczenia zewnętrzne

- Jakie czynniki środowiskowe wpływają na funkcjonowanie?
- Czy zmiana otoczenia może sprawić, że obiekt stanie się częściowo nieaktualny?

### 6.3. Ryzyka

- Co może powodować błędy, awarie lub niepowodzenia?
- Jakie występują pułapki oceny albo użycia obiektu (np. mylenie z pokrewnym pojęciem, ocena na podstawie deklaracji, nadmierna automatyzacja)?

### 6.4. Warunki brzegowe

- W jakich sytuacjach obiekt przestaje działać zgodnie z przeznaczeniem?
- Jakie są granice jego zastosowania?

---

## 7. Wnioski

### 7.1. Najważniejsze ustalenia

Przedstaw najważniejsze obserwacje wynikające z analizy w postaci listy.

### 7.2. Mocne strony

Wymień najistotniejsze zalety obiektu albo pojęcia.

### 7.3. Słabe strony

Wymień najważniejsze ograniczenia lub problemy.

### 7.4. Kluczowe zależności

Wskaż relacje mające największy wpływ na funkcjonowanie obiektu.

### 7.5. Podsumowanie

Przedstaw syntetyczny opis analizowanego obiektu w kilku akapitach, uwzględniając jego tożsamość, strukturę, relacje, zachowanie, cel i ograniczenia.

---

## Zasady analizy

1. Najpierw rozpoznaj typ obiektu i określ pewność rozpoznania.
2. Dostosuj głębokość analizy do charakteru obiektu oraz wybranego trybu.
3. Nie stosuj wszystkich sekcji i podsekcji mechanicznie. Pomijaj nie mające zastosowania z jawnym oznaczeniem `Nie dotyczy dla tego typu obiektu.`
4. Twórz podsekcje specyficzne dla typu obiektu, jeśli są istotne dla zrozumienia.
5. Nie twórz sztucznej treści dla sekcji, które nie mają zastosowania.
6. Oddzielaj fakty od interpretacji i hipotez.
7. Wskazuj zależności przyczynowo-skutkowe, odróżniając je od korelacji i współwystępowania.
8. Uwzględniaj zarówno elementy jawne, jak i ukryte.
9. Koncentruj się na zrozumieniu działania obiektu, a nie wyłącznie na jego opisie.
10. Każdy wniosek powinien wynikać z wcześniejszej analizy.
11. Jeżeli informacje są niepełne, wskaż poziom niepewności.
12. Stosuj tabele i schematy analityczne tam, gdzie zwiększają czytelność.
13. Celem analizy jest zrozumienie: czym jest obiekt, jak powstał i rozwija się, jak działa, po co istnieje, od czego zależy i jakie ma ograniczenia.

## Format wyniku

- Rozpocznij od sekcji `Rozpoznanie typu obiektu` z jawną `Pewnością rozpoznania`.
- Zachowaj numerację sekcji 1-7 oraz podsekcji (1.1, 1.2, ...).
- Pomijaj sekcje i podsekcje nie mające zastosowania z jawnym oznaczeniem `Nie dotyczy dla tego typu obiektu.`
- Zawsze kończ sekcją `Wnioski`.
- Używaj list punktowanych dla pytań pomocniczych.
- Stosuj tabele dla składników, granic pojęcia, kryteriów oceny i porównań.
- Stosuj bloki `text` dla schematów analitycznych i architektury działania.
- Oznaczaj niezweryfikowane twierdzenia.
- W trybie `szybki` dopuszczalne jest pominięcie pytań pomocniczych na rzecz zwięzłych ustaleń.

## Przykład

### Wejście

```text
NAZWA OBIEKTU: Rejestr BIP
KONTEKST: Samorządowy Biuletyn Informacji Publicznej
TRYB ANALIZY: pełny
```

### Wyjście (skrócone)

````text
Rozpoznanie typu obiektu
Rejestr BIP jest artefaktem informacyjnym o charakterze prawnie uregulowanym, funkcjonującym jako publicznie dostępny wykaz informacji o działalności organu administracji publicznej. Cechy decydujące: obowiązkowy zakres publikacji, publiczna dostępność, uwarunkowanie ustawowe.
Pewność rozpoznania: wysoki.

1. Tożsamość
1.1. Definicja: Rejestr BIP to publicznie dostępny wykaz informacji o działalności organu administracji publicznej, prowadzony zgodnie z ustawą o dostępie do informacji publicznej.
1.2. Kategoria: artefakt informacyjny, narzędzie transparentności, element systemu informacji publicznej. Nie jest systemem teleinformatycznym samym w sobie, choć bywa przez niego realizowany.
1.3. Zakres: Obejmuje informacje, dokumenty i dane publikowane obowiązkowo; nie obejmuje informacji niepublicznych.
1.4. Granice pojęcia:
| Pojęcie | Podstawowe pytanie | Przykład |
| --- | --- | --- |
| Rejestr BIP | Co jest publikowane obowiązkowo? | Wykaz decyzji administracyjnych |
| Strona urzędu | Co jest komunikowane ogólnie? | Aktualności, komunikaty |
| Archiwum wytwórcze | Co jest przechowywane wewnętrznie? | Teczki spraw |
1.5. Kontekst: Funkcjonuje w środowisku prawnym i organizacyjnym jednostki samorządu terytorialnego.

2. Struktura
2.1. Charakter struktury: struktura funkcjonalna, nie materialna.
2.2. Składniki kluczowe: Moduł publikacji, moduł wyszukiwania, archiwum, panel redaktorów.
2.3. Składniki pomocnicze: Szablony treści, procedury redakcyjne, mechanizmy powiadomień.
2.4. Hierarchia: Organ -> Wydział -> Redaktor -> Treść.
2.5. Architektura:
```text
decyzja publikacji -> redakcja treści -> akceptacja -> publikacja -> archiwizacja -> dostęp publiczny
```

3. Relacje
3.1. Relacje wewnętrzne: poprawność redakcji wpływa na wyszukiwalność; archiwizacja warunkuje ciągłość dostępu.
3.2. Relacje zewnętrzne: zależy od ustawy, organu, dostawcy technologii; oddziałuje na obywatela i organ nadzorczy.
3.3. Powiązania systemowe:
Wejścia: decyzja organu, dokument źródłowy, wymóg ustawowy.
Wyjścia: opublikowana treść, dostęp publiczny, raport dostępności.

4. Zachowanie
4.1. Funkcjonowanie: cykl redakcja-akceptacja-publikacja-archiwizacja.
4.2. Rozwój: powstaje z wymogu ustawowego, rozwija się wraz ze zmianami prawa i technologii.
4.3. Stany: aktualny, archiwalny, nieaktualny, niedostępny.
4.4. Zmiany i dynamika: reaguje na zmiany ustaw i reorganizację organu.
4.5. Wykonanie a posiadanie: Nie dotyczy dla tego typu obiektu.

5. Cel
5.1. Funkcja podstawowa: realizacja prawa obywatela do informacji publicznej.
5.2. Funkcja pojęcia: służy ocenie zgodności działania organu z wymogiem transparentności.
5.3. Wartość: dla obywatela - dostęp; dla organu - dowód zgodności; dla społeczeństwa - transparentność.
5.4. Efekty: poprawnie opublikowana, aktualna i wyszukiwalna treść.
5.5. Ocena skuteczności:
| Kryterium | Pytanie oceniające |
| --- | --- |
| Kompletność | Czy wszystkie obowiązkowe informacje są opublikowane? |
| Aktualność | Czy treść jest zgodna z bieżącym stanem? |
| Dostępność | Czy publikacja jest osiągalna bez barier? |
| Wyszukiwalność | Czy treść można skutecznie odnaleźć? |

6. Ograniczenia
6.1. Ograniczenia wewnętrzne: zależność od redaktorów, ryzyko przestarzałych treści.
6.2. Ograniczenia zewnętrzne: zmiany ustaw, ograniczenia technologiczne, dostępność personelu.
6.3. Ryzyka: nieaktualne treści, niepełna publikacja, błędy redakcyjne.
6.4. Warunki brzegowe: przestaje działać zgodnie z przeznaczeniem przy braku redaktora, awarii platformy albo zmianie zakresu ustawowego.

7. Wnioski
7.1. Najważniejsze ustalenia: Rejestr BIP jest narzędziem transparentności, którego działanie zależy od poprawności procesów publikacji i dostępności technicznej.
7.2. Mocne strony: wymóg ustawowy, publiczny dostęp, ustandaryzowany zakres.
7.3. Słabe strony: zależność od redaktorów, ryzyko przestarzałych treści, ograniczona wyszukiwalność.
7.4. Kluczowe zależności: rejestr a ustawodawstwo, rejestr a redaktor, rejestr a platforma techniczna.
7.5. Podsumowanie: Rejestr BIP realizuje prawo do informacji publicznej poprzez obowiązkową publikację działań organu. Jego skuteczność zależy od poprawności procesu redakcyjnego, aktualności treści i dostępności technicznej. Słabości wynikają z zależności ludzkich i technologicznych, a granice stosowania wyznacza zmieniające się prawo.
````
