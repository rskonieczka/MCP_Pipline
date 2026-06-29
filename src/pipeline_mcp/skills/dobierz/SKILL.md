---
name: dobierz
description: Dobiera najlepszy wariant działania, narzędzie, metodę, źródło, rozwiązanie lub opcję na podstawie celu, kontekstu, kryteriów, ograniczeń i dostępnych źródeł.
version: 1.0.0
argument-hint: "[CEL DOBORU] [opcjonalnie: WARIANTY, KONTEKST, KRYTERIA, OGRANICZENIA, ŹRÓDŁA, TRYB DOBORU]"
triggers:
  - user
  - model
---

# Workflow doboru wariantu do kontekstu

Celem workflowu jest przeprowadzenie rzetelnego, kontekstowego doboru jednej lub kilku opcji spośród możliwych wariantów, z jawnym uzasadnieniem kryteriów, metody wyboru, ryzyk, warunków brzegowych oraz wariantu rezerwowego.

Dobór odpowiada na pytanie "co wybrać i dlaczego w tym kontekście?", a nie tylko "jak coś zrobić?", "czym jest obiekt?" albo "czy twierdzenie jest prawdziwe?".

## Rola

Przyjmij rolę eksperta od decyzji technicznych, produktowych i operacyjnych, łączącego wieloletnią praktykę w analizie kryterialnej, projektowaniu systemów decyzyjnych, zarządzaniu ryzykiem i pracy ze źródłami prawdy.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- wybrać najlepszy wariant spośród kilku opcji,
- dobrać narzędzie, bibliotekę, framework, metodę, strategię, źródło, model, format, technikę albo procedurę,
- porównać opcje według jawnych kryteriów i ograniczeń,
- otrzymać rekomendację główną oraz wariant rezerwowy,
- rozstrzygnąć decyzję techniczną, architektoniczną, produktową, biznesową, organizacyjną albo operacyjną,
- dobrać metodę działania do kontekstu, ryzyka, zasobów, celu i poziomu niepewności,
- uporządkować subiektywne preferencje użytkownika w decyzję możliwą do uzasadnienia.

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce przeanalizować obiekt, pojęcie, proces albo artefakt bez wyboru wariantu - użyj skilla `analiza`,
- użytkownik chce zaplanować realizację wybranego celu krok po kroku - użyj skilla `planuj`,
- użytkownik chce zweryfikować prawdziwość twierdzeń, faktów albo zgodność ze źródłami - użyj skilla `weryfikacja`,
- użytkownik chce audytu odpowiedzi AI albo artefaktu - użyj skilla `sprawdzenie`,
- użytkownik chce wyekstrahować, znormalizować albo zwalidować zmienne wejściowe - użyj skilla `zmienne`,
- użytkownik pyta ogólnie "jak" bez potrzeby wyboru między wariantami - użyj skilla `jak`,
- decyzja wymaga danych krytycznych, których nie ma i których nie wolno samodzielnie uzupełnić ze źródeł,
- wybór byłby czysto losowy albo zależy wyłącznie od gustu bez wskazanych preferencji.

## Język

Dobór prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu. Nie używaj emoji w treści skilla, wyniku ani przykładach.

## Wejście

Wymagane:

- `CEL DOBORU` - co ma zostać dobrane i po co.

Wymagane warunkowo, co najmniej jedno z poniższych:

- `WARIANTY` - lista opcji do porównania,
- `ŹRÓDŁA` - materiały, z których można wyprowadzić warianty,
- `KONTEKST` - sytuacja pozwalająca sensownie zidentyfikować kandydatów do doboru.

Opcjonalnie:

- `KONTEKST` - środowisko, przypadek użycia, użytkownik, organizacja, system, etap projektu,
- `KRYTERIA` - kryteria wyboru, priorytety, wagi, metryki jakości,
- `OGRANICZENIA` - warunki twarde i miękkie, np. czas, budżet, kompatybilność, prawo, bezpieczeństwo,
- `PREFERENCJE` - preferencje użytkownika lub zespołu,
- `ŹRÓDŁA` - dokumentacja projektu, dokumentacja bibliotek, notebooki, dane wejściowe, wyniki testów,
- `TRYB DOBORU` - `szybki`, `pełny`, `dogłębny`, `kryterialny`, `źródłowy`, `techniczny`, `architektoniczny`, `strategiczny`, `ryzyka`, `preferencyjny`, `hybrydowy`,
- `LICZBA REKOMENDACJI` - ile wariantów wskazać,
- `FORMAT WYNIKU` - tabela, ranking, rekomendacja opisowa, macierz decyzyjna,
- `DOZWOLONE ŹRÓDŁA ZEWNĘTRZNE` - czy można użyć Context7, NotebookLM, web albo innych źródeł zewnętrznych,
- `OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` - `skrócony`, `standardowy`, `dogłębny`.

## Kontrola kompletności wejścia

1. Jeśli brakuje `CELU DOBORU`, nie wykonuj doboru. Poproś o wskazanie, co ma zostać dobrane i do jakiego celu.
2. Jeśli brakuje jednocześnie `WARIANTÓW`, `ŹRÓDEŁ` i wystarczającego `KONTEKSTU`, poproś o uzupełnienie co najmniej jednego z tych elementów.
3. Jeśli warianty są wskazane, nie dodawaj nowych wariantów bez potrzeby. Możesz dodać wariant uzupełniający tylko wtedy, gdy jawnie oznaczysz go jako `propozycja agenta`.
4. Jeśli kryteria nie są wskazane, wyprowadź je z celu i kontekstu, ale oznacz jako `kryteria wnioskowane`.
5. Jeśli istnieją warunki twarde, najpierw odfiltruj warianty niespełniające tych warunków, zanim wykonasz ranking.
6. Jeśli dane są niepełne, ale wystarczające do rekomendacji roboczej, ustaw status wyniku `ograniczony` i wskaż brakujące dane.
7. Jeśli braki uniemożliwiają odpowiedzialny wybór, ustaw status `nierozstrzygnięty` i zadaj jedno precyzyjne pytanie uzupełniające.
8. Jeśli decyzja dotyczy bezpieczeństwa, prawa, finansów, danych wrażliwych albo realnych skutków operacyjnych, zwiększ rygor źródłowy i jawnie wskaż ryzyka.

## Tryby doboru

Jeśli użytkownik nie wskaże trybu, zastosuj tryb `pełny`.

Tryby głębokości:

- `szybki` - minimalny dobór: cel, kryteria, krótki ranking, rekomendacja i ryzyko główne.
- `pełny` - domyślny: rozpoznanie typu doboru, kryteria, ograniczenia, metoda, porównanie, rekomendacja, wariant rezerwowy i warunki rewizji.
- `dogłębny` - pełna macierz decyzyjna, źródła, wagi, analiza ryzyk, scenariusze, konflikty kryteriów, analiza wrażliwości i warunki zmiany decyzji.

Tryby profilowe:

- `kryterialny` - używaj, gdy warianty są znane i można je porównać według mierzalnych kryteriów.
- `źródłowy` - używaj, gdy decyzja zależy od dokumentacji, faktów, standardów albo materiałów użytkownika.
- `techniczny` - używaj dla bibliotek, frameworków, API, CLI, konfiguracji, kodu, narzędzi i środowisk technicznych.
- `architektoniczny` - używaj, gdy wybór wpływa na strukturę systemu, zależności, skalowalność, utrzymanie albo integracje.
- `strategiczny` - używaj dla decyzji produktowych, biznesowych, organizacyjnych i długoterminowych.
- `ryzyka` - używaj, gdy najważniejsze są bezpieczeństwo, zgodność, koszt błędu, odwracalność albo skutki uboczne.
- `preferencyjny` - używaj, gdy wybór zależy głównie od preferencji użytkownika, stylu, wygody albo dopasowania do zespołu.
- `hybrydowy` - używaj, gdy decyzja wymaga połączenia co najmniej dwóch profili, np. technicznego i strategicznego.

`OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI` mapuje się na tryb:

- `skrócony` -> `szybki`,
- `standardowy` -> `pełny`,
- `dogłębny` -> `dogłębny`.

Jeśli tryb profilowy i poziom szczegółowości są podane razem, połącz je, np. `techniczny + dogłębny`.

## Źródła prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pułapki.
2. Context7 - dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - notebooki i źródła badawcze użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zależności, graf wywołań, analiza architektury przez Cypher.

Stosuj w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi. Konflikty źródeł, hierarchia i reguły uzupełniające: patrz `_shared/zrodla-i-narzedzia.md`.

Reguły specyficzne dla doboru:

- Dla faktów projektowych pierwszeństwo ma `.ai-kb`, README, dokumentacja repozytorium i kod źródłowy.
- Dla bibliotek, frameworków, SDK, API, CLI i konfiguracji używaj Context7, jeśli decyzja zależy od aktualnej dokumentacji.
- Dla materiałów badawczych użytkownika używaj `notebooklm-mcp`, jeśli użytkownik wskazał notebooki albo źródła użytkownika.
- Dla relacji architektonicznych używaj Memgraph MCP, jeśli wybór zależy od grafu zależności albo wpływu na system.
- Jeśli źródła są sprzeczne, wskaż konflikt, wpływ na decyzję i sposób rozstrzygnięcia.

## Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza architektury przez Cypher.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Koperta

`dobierz` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty:
- Jeśli poprzednią stacją był `dekompozycja`: `pola_stacji.dekompozycja.podproblemy` -> `CEL DOBORU` + `WARIANTY` (wnioskowane),
- Jeśli poprzednią stacją był `analiza` (gdy pominięto dekompozycję): `pola_stacji.analiza.raport_streszczenie` -> `CEL DOBORU` + `WARIANTY` (wnioskowane),
- `stan.zamiar` -> `KONTEKST` (kontekstowe),
- `pola_stacji.zmienne.variables` -> `KRYTERIA` / `OGRANICZENIA` (wnioskowane, jeśli dostępne).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: dobierz`,
- `stacja_poprzednia: dekompozycja` (lub `analiza`),
- `pola_stacji.dobierz`: `status_doboru`, `metoda_doboru`, `rekomendacja` (główna), `rekomendacja_rezerwowa`, `ryzyka_i_warunki_rewizji`, `najblizszy_krok`,
- `walidacja.stacja_docelowa: routing` (lub `planuj` gdy pominięto routing),
- `walidacja.pola_wymagane: [ZAMIAR LUB PROBLEM]` -> z `stan.zamiar` (kontekstowe),
- `relacje`:
  - `stacja:dobierz` -> `stacja:routing` (lub `stacja:planuj`) (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:dobierz` (typ: `zawiera`),
  - `stacja:dobierz` -> `decyzja:D001` (typ: `wyprodukowala`, dla rekomendacji),
  - `decyzja:D001` -> `zmienna:V001`, ... (typ: `oparta_na`, per zmienna użyta w uzasadnieniu rekomendacji).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_04_dobierz.yaml` i zaktualizuj manifest.

## Analiza pojęciowa doboru

### Definicja

Dobór to kontekstowa umiejętność decyzyjna polegająca na wyborze wariantu najlepiej dopasowanego do celu, warunków, ograniczeń, kryteriów jakości i dostępnych zasobów.

Nie jest tym samym co analiza, ponieważ analiza wyjaśnia strukturę obiektu, a dobór kończy się rekomendacją wyboru. Nie jest też planowaniem, ponieważ planowanie ustala sekwencję działań po wyborze celu lub wariantu. Dobór może poprzedzać planowanie, weryfikację albo implementację.

### Składniki funkcjonalne doboru

| Składnik | Znaczenie w doborze |
| --- | --- |
| Cel działania | Określa, do czego wariant ma być dobrany |
| Rozpoznanie sytuacji | Identyfikuje kontekst, ograniczenia i stawkę decyzji |
| Wiedza operacyjna | Dostarcza informacji o wariantach, źródłach i kryteriach |
| Know-how | Pozwala dobrać właściwą metodę selekcji |
| Procedura lub strategia | Porządkuje eliminację, porównanie i rekomendację |
| Wykonanie | Przeprowadza ranking lub wybór |
| Kontrola | Sprawdza spójność wyboru z celem i ograniczeniami |
| Korekta | Pozwala zmienić rekomendację po wykryciu konfliktu lub braku danych |
| Adaptacja | Dopasowuje metodę do kontekstu technicznego, strategicznego, źródłowego lub preferencyjnego |

### Architektura działania

```text
cel doboru -> rozpoznanie kontekstu -> identyfikacja wariantów -> kryteria i ograniczenia -> wybór metody -> porównanie -> rekomendacja -> kontrola ryzyk -> warunki rewizji -> wynik
```

### Granice pojęcia

| Pojęcie | Podstawowe pytanie | Różnica względem doboru |
| --- | --- | --- |
| Analiza | Czym jest obiekt i jak działa? | Nie musi kończyć się wyborem wariantu |
| Weryfikacja | Czy twierdzenie jest prawdziwe? | Sprawdza status prawdziwościowy, nie rekomenduje opcji |
| Planowanie | Jak osiągnąć cel krok po kroku? | Zakłada cel lub wariant i ustala realizację |
| Audyt | Czy artefakt jest poprawny? | Ocenia istniejący materiał, nie musi wybierać opcji |
| Ekstrakcja zmiennych | Jakie dane są potrzebne? | Przygotowuje kontrakt danych, nie rozstrzyga decyzji |
| Dobór | Co wybrać w tym kontekście? | Kończy się rekomendacją i uzasadnieniem wyboru |

## Kontekstowe metody doboru

### 1. Metoda eliminacji warunków twardych

Stosuj, gdy istnieją ograniczenia nieprzekraczalne, np. zgodność prawna, kompatybilność, budżet maksymalny, wymagania bezpieczeństwa, licencja albo brak uprawnień.

Procedura:

1. Wypisz warunki twarde.
2. Oznacz warianty spełniające i niespełniające każdy warunek.
3. Usuń warianty niespełniające warunków twardych.
4. Dopiero pozostałe warianty oceniaj jakościowo albo punktowo.

### 2. Metoda macierzy ważonej

Stosuj, gdy warianty są porównywalne, a kryteria można uszeregować według ważności.

Procedura:

1. Zdefiniuj kryteria.
2. Przypisz wagi, jeśli użytkownik je podał albo wynikają z kontekstu.
3. Oceń każdy wariant względem każdego kryterium.
4. Oblicz ranking albo opisz wynik jakościowo.
5. Sprawdź, czy wynik nie zależy nadmiernie od jednego niepewnego kryterium.

### 3. Metoda źródłowa

Stosuj, gdy decyzja zależy od dokumentacji, standardów, faktów, polityk projektu albo materiałów użytkownika.

Procedura:

1. Określ typ źródła właściwy dla decyzji.
2. Pobierz albo odczytaj najwyższe dostępne źródło prawdy.
3. Porównaj warianty ze źródłem.
4. Oznacz warianty jako `zgodny`, `częściowo zgodny`, `niezgodny`, `niezweryfikowany`.
5. Nie rekomenduj wariantu niezweryfikowanego jako głównego, jeśli stawka decyzji jest wysoka.

### 4. Metoda techniczna

Stosuj dla decyzji o kodzie, narzędziach, bibliotekach, API, CLI, konfiguracji, infrastrukturze albo środowisku.

Kryteria typowe:

- zgodność z istniejącą architekturą,
- dostępność w projekcie,
- kompatybilność wersji,
- bezpieczeństwo,
- utrzymywalność,
- wydajność,
- krzywa uczenia,
- koszt integracji,
- stabilność i dojrzałość.

### 5. Metoda architektoniczna

Stosuj, gdy wybór wpływa na strukturę systemu, zależności, odpowiedzialności modułów, skalowanie, observability albo przyszłe zmiany.

Kryteria typowe:

- spójność z obecnymi wzorcami,
- sprzężenie i kohezja,
- odwracalność decyzji,
- zakres wpływu na system,
- złożoność operacyjna,
- ścieżka migracji,
- ryzyko długu technicznego.

### 6. Metoda strategiczna

Stosuj, gdy wybór dotyczy produktu, organizacji, rynku, priorytetów, zasobów albo długiego horyzontu.

Kryteria typowe:

- wpływ na cel biznesowy,
- koszt alternatywny,
- czas do wartości,
- skalowalność organizacyjna,
- ryzyko strategiczne,
- zgodność z kierunkiem projektu,
- łatwość komunikacji decyzji.

### 7. Metoda ryzyka

Stosuj, gdy najważniejszy jest koszt błędu, bezpieczeństwo, zgodność, prywatność, stabilność albo realne skutki operacyjne.

Procedura:

1. Określ najgorszy realistyczny skutek wyboru każdego wariantu.
2. Oceń prawdopodobieństwo i wpływ ryzyka.
3. Preferuj wariant o akceptowalnym profilu ryzyka, nawet jeśli nie maksymalizuje wszystkich korzyści.
4. Wskaż warunki monitorowania i plan wycofania decyzji.

### 8. Metoda preferencyjna

Stosuj, gdy kryteria są w dużej części subiektywne, np. styl, ergonomia, wygoda, estetyka, preferencje zespołu.

Procedura:

1. Oddziel fakty od preferencji.
2. Ustal preferencje jawnie albo wywnioskuj je z wypowiedzi użytkownika i oznacz jako `wnioskowane`.
3. Nie przedstawiaj preferencji jako obiektywnej przewagi.
4. Rekomenduj wariant najlepiej dopasowany do preferencji, z informacją, co zmieniłoby wybór.

### 9. Metoda satysfakcjonująca

Stosuj, gdy nie trzeba maksymalizować wyniku, a celem jest szybki wybór wariantu wystarczająco dobrego.

Procedura:

1. Określ minimalne kryteria akceptacji.
2. Odfiltruj warianty poniżej minimum.
3. Wybierz pierwszy lub najprostszy wariant spełniający kryteria.
4. Zaznacz, że wynik jest optymalizowany pod szybkość i prostotę, nie pod pełną optymalność.

### 10. Metoda hybrydowa

Stosuj, gdy decyzja łączy kilka typów kontekstu, np. techniczny, architektoniczny i strategiczny.

Procedura:

1. Ustal najpierw warunki twarde.
2. Dobierz dwa lub trzy profile decyzyjne.
3. Nadaj priorytet kryteriom według stawki decyzji.
4. Wykonaj porównanie.
5. Wskaż, który profil miał największy wpływ na rekomendację.

## Instrukcja główna

1. Rozpoznaj cel doboru i typ zadania: techniczny, architektoniczny, strategiczny, operacyjny, źródłowy, preferencyjny, ryzykowy albo hybrydowy.
2. Sprawdź kompletność wejścia: cel, warianty albo źródła wariantów, kontekst, kryteria, ograniczenia i preferencje.
3. Określ stawkę decyzji: niska, średnia, wysoka. Im wyższa stawka, tym większy rygor źródłowy i ostrożniejsza rekomendacja.
4. Zidentyfikuj warianty do porównania. Jeśli warianty są wnioskowane, oznacz je jako `propozycja agenta`.
5. Oddziel warunki twarde od kryteriów miękkich.
6. Dobierz metodę kontekstową. Uzasadnij, dlaczego ta metoda pasuje do zadania.
7. Zbierz i oceń źródła potrzebne do decyzji, zgodnie z hierarchią źródeł prawdy.
8. Porównaj warianty według kryteriów. Stosuj tabelę, jeśli zwiększa czytelność.
9. Wskaż rekomendację główną, wariant rezerwowy i warianty odrzucone.
10. Uzasadnij rekomendację przez cel, kryteria, źródła, ograniczenia i ryzyka.
11. Wskaż warunki rewizji, czyli co musiałoby się zmienić, aby rekomendacja przestała być aktualna.
12. Jeśli wybór nie jest możliwy, nie zgaduj. Podaj status `nierozstrzygnięty`, braki danych i jedno pytanie uzupełniające.

## Sekcje merytoryczne wyniku

### 1. Rozpoznanie typu doboru

Określ, jaki typ decyzji jest wykonywany i dlaczego. Wskaż:

- typ doboru,
- stawkę decyzji,
- poziom niepewności,
- tryb lub metodę doboru,
- poziom pewności rozpoznania.

### 2. Cel i kontekst

Opisz:

- cel wyboru,
- użytkownika lub interesariusza decyzji,
- środowisko decyzji,
- ograniczenia twarde i miękkie,
- preferencje użytkownika,
- kryterium sukcesu wyboru.

### 3. Warianty

Wypisz warianty i oznacz ich pochodzenie:

- `user_provided` - podany przez użytkownika,
- `verified_source` - potwierdzony w źródle,
- `agent_inference` - wywnioskowany przez agenta,
- `hypothesis` - hipoteza do potwierdzenia.

### 4. Kryteria i wagi

Wypisz kryteria, ich status i ewentualne wagi:

| Kryterium | Typ | Waga / priorytet | Źródło | Uwagi |
| --- | --- | --- | --- | --- |
| ... | twarde / miękkie | ... | ... | ... |

### 5. Porównanie

Porównaj warianty w tabeli albo opisie. Dobierz format do złożoności decyzji.

Przykładowa tabela:

| Wariant | Mocne strony | Słabe strony | Ryzyka | Ocena kontekstowa |
| --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... |

### 6. Rekomendacja

Wskaż:

- rekomendację główną,
- uzasadnienie,
- wariant rezerwowy,
- warianty odrzucone i powód odrzucenia,
- poziom pewności rekomendacji.

### 7. Warunki rewizji

Wskaż, co może zmienić rekomendację:

- nowe źródło,
- zmiana ograniczeń,
- zmiana celu,
- zmiana preferencji,
- wynik testu,
- wzrost ryzyka,
- brak dostępności rekomendowanego wariantu.

## Zasady wykonania

- Oddzielaj fakty, preferencje, interpretacje, hipotezy i rekomendacje.
- Nie przedstawiaj wariantu jako najlepszego bez wskazania kryterium najlepszego wyboru.
- Nie zgaduj brakujących danych krytycznych. Oznaczaj je jako `niezweryfikowane`, `wnioskowane` albo `brak danych`.
- Nie nadawaj wag kryteriom jako faktów, jeśli nie wynikają ze źródeł lub wypowiedzi użytkownika.
- Nie rekomenduj wariantu niespełniającego warunków twardych, chyba że jawnie oznaczysz rekomendację jako wyjątek wymagający akceptacji użytkownika.
- Zachowuj intencję użytkownika i nie zmieniaj celu doboru bez uzasadnienia.
- Preferuj najmniejszą skuteczną decyzję: wybór wystarczająco dobry i bezpieczny jest lepszy niż nadmiernie złożona optymalizacja, jeśli kontekst nie wymaga optymalizacji.
- Jeśli decyzja dotyczy kodu, konfiguracji, bibliotek albo API, nie zakładaj dostępności zależności bez sprawdzenia projektu lub dokumentacji.
- Jeśli decyzja może mieć skutki destrukcyjne, finansowe, prawne albo prywatnościowe, wskaż ryzyko i nie wykonuj działań z efektem ubocznym bez zgody użytkownika.
- Jeśli wynik jest wrażliwy na niepewne dane, wskaż analizę wrażliwości lub warunek rewizji.
- Jeśli dwa warianty są równorzędne, nie wymuszaj fałszywego rozstrzygnięcia. Wskaż remis, kryterium rozstrzygające i pytanie uzupełniające.

## Format wyniku

Zwracaj wynik w poniższej strukturze:

```text
STATUS DOBORU: pełny | ograniczony | nierozstrzygnięty
TRYB DOBORU: [tryb głębokości] + [tryb profilowy]
TYP DOBORU: [techniczny | architektoniczny | strategiczny | operacyjny | źródłowy | preferencyjny | ryzyka | hybrydowy]

CEL I KONTEKST:
[cel, sytuacja, ograniczenia, kryterium sukcesu]

METODA DOBORU:
[wybrana metoda i uzasadnienie jej użycia]

WARIANTY:
[lista wariantów z pochodzeniem]

KRYTERIA:
[tabela albo lista kryteriów, wag i statusu]

PORÓWNANIE:
[tabela albo opis porównania]

REKOMENDACJA:
- Rekomendacja główna: [...]
- Uzasadnienie: [...]
- Wariant rezerwowy: [...]
- Odrzucone warianty: [...]
- Poziom pewności: niski | średni | wysoki

RYZYKA I WARUNKI REWIZJI:
[ryzyka, braki danych, co zmieniłoby decyzję]

NAJBLIŻSZY KROK:
[jeden konkretny następny krok]
```

Jeśli dobór nie jest możliwy, zwróć:

```text
STATUS DOBORU: nierozstrzygnięty
BRAKUJĄCE DANE:
[list]
DLACZEGO NIE MOŻNA DOBRAĆ:
[krótkie uzasadnienie]
PYTANIE UZUPEŁNIAJĄCE:
[jedno precyzyjne pytanie]
```

## Przykład

### Wejście

```text
CEL DOBORU: Wybrać sposób przechowywania krótkich notatek projektu dla agenta AI.
WARIANTY: pliki Markdown w repo, baza SQLite, zewnętrzne API dokumentacyjne.
KONTEKST: mały projekt, praca lokalna, ważna prostota i łatwy przegląd w git.
KRYTERIA: prostota, wersjonowanie, brak dodatkowej infrastruktury, możliwość automatycznego odczytu przez agenta.
TRYB DOBORU: techniczny
OCZEKIWANY POZIOM SZCZEGÓŁOWOŚCI: standardowy
```

### Wyjście

```text
STATUS DOBORU: pełny
TRYB DOBORU: pełny + techniczny
TYP DOBORU: techniczny

CEL I KONTEKST:
Celem jest wybór sposobu przechowywania krótkich notatek projektu. Kontekst premiuje prostotę, pracę lokalną, kontrolę wersji i brak infrastruktury.

METODA DOBORU:
Zastosowano metodę eliminacji warunków twardych oraz uproszczoną macierz kryterialną, ponieważ warianty są znane, a kryteria wynikają z kontekstu.

WARIANTY:
- Pliki Markdown w repo - user_provided.
- Baza SQLite - user_provided.
- Zewnętrzne API dokumentacyjne - user_provided.

KRYTERIA:
| Kryterium | Typ | Priorytet | Źródło | Uwagi |
| --- | --- | --- | --- | --- |
| Prostota | miękkie | wysoki | user_provided | Mały projekt |
| Wersjonowanie | miękkie | wysoki | user_provided | Ważny git |
| Brak infrastruktury | twarde | wysoki | user_provided | Preferowana praca lokalna |
| Odczyt przez agenta | miękkie | średni | user_provided | Wszystkie warianty możliwe |

PORÓWNANIE:
| Wariant | Mocne strony | Słabe strony | Ryzyka | Ocena kontekstowa |
| --- | --- | --- | --- | --- |
| Pliki Markdown | Proste, wersjonowane, łatwe do odczytu | Mniej dobre dla zapytań relacyjnych | Rozrost liczby plików | Najlepsze dopasowanie |
| SQLite | Struktura i zapytania | Wymaga schematu i obsługi pliku DB | Nadmiarowe dla małego projektu | Dobre, ale zbyt ciężkie |
| API dokumentacyjne | Integracje i dostęp zewnętrzny | Wymaga sieci i konfiguracji | Zależność od usługi | Słabe dopasowanie |

REKOMENDACJA:
- Rekomendacja główna: pliki Markdown w repo.
- Uzasadnienie: najlepiej spełniają prostotę, wersjonowanie i brak infrastruktury.
- Wariant rezerwowy: SQLite, jeśli pojawi się potrzeba zapytań strukturalnych.
- Odrzucone warianty: zewnętrzne API dokumentacyjne, bo łamie preferencję pracy lokalnej i prostoty.
- Poziom pewności: wysoki.

RYZYKA I WARUNKI REWIZJI:
Rekomendacja zmieni się, jeśli notatki zaczną wymagać relacji, filtrowania po wielu polach albo równoczesnej pracy wielu procesów.

NAJBLIŻSZY KROK:
Utwórz katalog na notatki Markdown i ustal minimalny szablon pliku.
```
