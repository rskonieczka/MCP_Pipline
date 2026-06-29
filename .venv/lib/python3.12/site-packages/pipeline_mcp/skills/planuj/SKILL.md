---
name: planuj
description: Przeprowadza proces planowania celu, zadania lub projektu z ustaleniem kroków, zasobów, ryzyk i kryteriów sukcesu.
version: 1.0.0
argument-hint: "[CEL DO ZAPLANOWANIA] [opcjonalnie: KONTEKST, OGRANICZENIA, HORYZONT, TRYB]"
triggers:
  - user
  - model
---
# Workflow planowania celu, zadania lub projektu

Celem tego workflowu jest przeprowadzenie ustrukturyzowanego procesu planowania, który przekształca cel albo zamiar w wykonalny plan działania z jawnymi krokami, zasobami, ryzykami i kryteriami sukcesu.

Planowanie odpowiada na pytanie "jak osiągnąć X?", a nie "czy X jest prawdziwe?" albo "czym jest X?".

## Rola

Przyjmij rolę eksperta od planowania strategicznego, operacyjnego i projektowego, łączącego myślenie sekwencyjne, systemowe i probabilistyczne.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- zaplanować realizację celu, zadania lub projektu,
- przekształcić zamiar w wykonalny plan kroków,
- ustalić kolejność działań i alokację zasobów,
- zidentyfikować ryzyka i kontyngencje,
- zaplanować migrację, wdrożenie lub zmianę,
- określić kryteria sukcesu i punkty kontrolne,
- zaplanować pracę wieloetapową.

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce przeanalizować obiekt albo pojęcie - użyj skilla `analiza`,
- użytkownik chce zweryfikować twierdzenia - użyj skilla `weryfikacja`,
- użytkownik chce dokonać audytu odpowiedzi AI - użyj skilla `sprawdzenie`,
- użytkownik chce wybrać między wariantami - użyj skilla `jak` albo `zmienne`,
- zadanie jest trywialne i nie wymaga planowania,
- użytkownik chce wygenerować kod bez planowania jego tworzenia.

## Język

Planowanie prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `CEL DO ZAPLANOWANIA` - co ma zostać osiągnięte.

Opcjonalnie:

- `KONTEKST` - środowisko, sytuacja, ograniczenia,
- `OGRANICZENIA` - budżet, czas, zasoby, technologia, zespół,
- `HORYZONT` - `operacyjny` (dni/tygodnie), `taktyczny` (miesiące), `strategiczny` (kwartały/lata),
- `TRYB PLANOWANIA` - `szybki`, `pełny`, `dogłębny` (domyślnie `pełny`),
- `ŹRÓDŁA` - materiały bazowe,
- `KRYTERIA SUKCESU` - jak ocenić, czy plan się powiódł,
- `ZAKRES` - które elementy planu pogłębić albo pominąć.

## Kontrola kompletności wejścia

1. Jeśli brakuje `CEL DO ZAPLANOWANIA`, nie wykonuj planowania. Poproś o wskazanie celu.
2. Jeśli cel jest niejednoznaczny, najpierw rozstrzygnij, co dokładnie ma zostać zaplanowane.
3. Jeśli `OGRANICZENIA` nie są wskazane, zidentyfikuj je na podstawie kontekstu i oznacz jako `niezweryfikowane`.
4. Jeśli `KRYTERIA SUKCESU` nie są wskazane, zaproponuj je i potwierdź z użytkownikiem.
5. Jeśli `HORYZONT` nie jest wskazany, wnioskuj z zakresu celu.
6. Jeśli `ZAKRES` wyklucza kluczowe elementy (np. ryzyka), potwierdź z użytkownikiem, że świadomie rezygnuje z ich planowania.

## Tryby planowania

Jeśli użytkownik nie wskaże trybu, zastosuj tryb `pełny`.

- `szybki` - cel, kluczowe kroki, zasoby, najważniejsze ryzyka, kryteria sukcesu. Krótki plan.
- `pełny` - domyślny: wszystkie sekcje 1-7 z adaptacją do typu planu.
- `dogłębny` - pełne sekcje 1-7, rozbudowane analizy ryzyk, scenariusze alternatywne, tabele, punkty kontrolne, metryki.

## Źródła prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pułapki.
2. Context7 - dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - notebooki i źródła badawcze użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zależności, graf wywołań.

Stosuj w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi. Konflikty źródeł, hierarchia i reguły uzupełniające: patrz `_shared/zrodla-i-narzedzia.md`.

Reguły specyficzne dla planowania:

- Plan opieraj na zweryfikowanych informacjach o projekcie i technologii.
- Jeśli informacja jest kluczowa dla planu, ale niezweryfikowana, oznacz to jawne i wskaż ryzyko.
- Nie zakładaj dostępności zasobów, narzędzi ani uprawnień bez potwierdzenia.

## Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza wpływu zmian.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Koperta

`planuj` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty:
- Jeśli poprzednią stacją był `routing`: `pola_stacji.routing.sciezka` + `pola_stacji.dobierz.rekomendacja` -> `CEL DO ZAPLANOWANIA` (wnioskowane),
- Jeśli poprzednią stacją był `dobierz` (gdy pominięto routing): `pola_stacji.dobierz.rekomendacja` -> `CEL DO ZAPLANOWANIA` (wnioskowane),
- `pola_stacji.dobierz.ryzyka_i_warunki_rewizji` -> `OGRANICZENIA` (wnioskowane),
- `stan.zamiar` -> `KONTEKST` (kontekstowe).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: planuj`,
- `stacja_poprzednia: routing` (lub `dobierz`),
- `pola_stacji.planuj`: `plan` (pełny plan 7-sekcyjny), `kryteria_sukcesu`, `punkty_kontrolne`, `walidacja_planu`,
- `walidacja.stacja_docelowa: realizuj`,
- `walidacja.pola_wymagane: [PLAN DO ZREALIZOWANIA]` -> z `pola_stacji.planuj.plan` (bezpośrednie),
- `relacje`:
  - `stacja:planuj` -> `stacja:realizuj` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:planuj` (typ: `zawiera`),
  - `stacja:planuj` -> `krok:K1`, `krok:K2`, ... (typ: `wyprodukowala`, per krok planu),
  - `krok:K1` -> `podproblem:P1` (typ: `rozwiazuje`, per krok rozwiązujący podproblem).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_06_planuj.yaml` i zaktualizuj manifest.

## Instrukcja główna

Najpierw rozpoznaj, jaki typ planowania jest wymagany. Nie zakładaj z góry, że każdy plan ma tę samą strukturę.

Możliwe typy planu:

- plan zadania (pojedyncze zadanie techniczne lub biznesowe),
- plan projektu (wieloetapowe przedsięwzięcie z zespołem i zasobami),
- plan migracji / wdrożenia (zmiana stanu systemu lub organizacji),
- plan strategiczny (długoterminowy cel z wieloma inicjatywami),
- plan kontyngencyjny (reakcja na przewidywane ryzyko),
- plan sprintu / iteracji (krótkoterminowy cykl dostarczania),
- plan release'u (wydanie wersji produktu),
- inny typ, jeśli analiza wykaże taką potrzebę.

Po rozpoznaniu typu planu dostosuj zakres planowania. Uwzględniaj wyłącznie te elementy, które mają znaczenie dla danego typu.

Zasady adaptacji:

- Pomijaj sekcje nie mające zastosowania, z jawnym oznaczeniem `Nie dotyczy dla tego typu planu.`
- Twórz sekcje specyficzne dla typu planu, jeśli są istotne (np. `Strategia rollbacku` dla migracji, `Harmonogram wydania` dla release'u).
- Stosuj tabele tam, gdzie zwiększają czytelność (kroki, zasoby, ryzyka, metryki).
- Stosuj schematy w blokach `text` tam, gdzie pokazują przepływ albo zależności.

Plan musi opierać się na faktach, logicznych zależnościach i obserwowalnych ograniczeniach. Unikaj spekulacji oraz zakładania optymistycznych scenariuszy bez podstaw.

---

Planowanie: [CEL DO ZAPLANOWANIA]

## Rozpoznanie typu planu

Określ typ planu i uzasadnij, dlaczego tak go rozpoznajesz. Wskaż cechy decydujące: horyzont czasowy, liczba etapów, wymagane zasoby, stopień niepewności, liczba zaangażowanych osób.

Zakończ sekcję jawną deklaracją:

**Pewność rozpoznania: niski / średni / wysoki.**

Jeśli pewność jest niższa niż wysoki, wskaż, czego brakuje do pewniejszego rozpoznania.

---

## 1. Cel i założenia

### 1.1. Cel planowania

- Co ma zostać osiągnięte?
- Jaki jest mierzalny rezultat?
- Jakie jest kryterium ukończenia?

### 1.2. Kontekst

- W jakim środowisku plan jest realizowany?
- Jakie są warunki wyjściowe?
- Co zostało już zrobione?

### 1.3. Ograniczenia

- Jakie są ograniczenia czasowe, budżetowe, zasobowe, technologiczne?
- Jakie są ograniczenia organizacyjne, prawne, regulacyjne?
- Które ograniczenia są twarde, a które miękkie?

### 1.4. Założenia

- Jakie założenia przyjmujesz?
- Które założenia są zweryfikowane, a które są hipotezami?
- Co się stanie, jeśli założenie okaże się błędne?

Przedstaw założenia w tabeli:

| Założenie | Status                                      | Wpływ na plan, jeśli błędne |
| ----------- | ------------------------------------------- | ------------------------------- |
| ...         | zweryfikowane / hipoteza / niezweryfikowane | ...                             |

---

## 2. Analiza sytuacji wyjściowej

### 2.1. Stan obecny

- Jaki jest punkt wyjścia?
- Co istnieje i działa?
- Co brakuje albo nie działa?

### 2.2. Luka między stanem obecnym a celem

- Co trzeba zbudować, zmienić albo usunąć?
- Jaki jest dystans między stanem obecnym a celem?

### 2.3. Zależności i warunki wstępne

- Co musi zostać zrobione przed rozpoczęciem?
- Od czego zależą kluczowe kroki?
- Czy istnieją zależności zewnętrzne (dostawcy, zespoły, decyzje)?

Jeśli ma zastosowanie, przedstaw schemat zależności w bloku `text`.

---

## 3. Kroki i sekwencja

### 3.1. Dekompozycja celu

- Jakie są główne etapy?
- Jak cel rozkłada się na mniejsze, mierzalne jednostki?

### 3.2. Sekwencja kroków

- Jaka jest kolejność działań?
- Które kroki są sekwencyjne, a które równoległe?
- Jakie są zależności między krokami?

Przedstaw kroki w tabeli:

| Krok | Opis | Zależności | Typ                        | Szacowany czas |
| ---- | ---- | ------------ | -------------------------- | -------------- |
| ...  | ...  | ...          | sekwencyjny / równoległy | ...            |

### 3.3. Punkty kontrolne

- W których momentach planu należy zweryfikować postęp?
- Co jest kryterium przejścia do kolejnego etapu?
- Kto decyduje o przejściu?

### 3.4. Schemat przepływu

Jeśli ma zastosowanie, przedstaw schemat planu w bloku `text` pokazujący przepływ kroków i zależności.

---

## 4. Zasoby

### 4.1. Zasoby ludzkie

- Kto jest potrzebny do realizacji planu?
- Jakie umiejętności są wymagane?
- Czy zespoły są dostępne w wymaganym czasie?

### 4.2. Zasoby techniczne

- Jakie narzędzia, technologie, infrastruktura są potrzebne?
- Co jest dostępne, a co trzeba pozyskać albo zbudować?

### 4.3. Zasoby czasowe i budżetowe

- Jaki jest szacowany czas realizacji?
- Jaki jest budżet?
- Jakie są rezerwy?

Przedstaw zasoby w tabeli:

| Zasób | Typ                                        | Wymagana ilość | Dostępność                   | Ryzyko niedostępności |
| ------ | ------------------------------------------ | ---------------- | ------------------------------- | ----------------------- |
| ...    | ludzki / techniczny / czasowy / budżetowy | ...              | potwierdzona / niezweryfikowana | ...                     |

---

## 5. Ryzyka i kontyngencje

### 5.1. Identyfikacja ryzyk

- Co może pójść nie tak?
- Które ryzyka są najbardziej prawdopodobne?
- Które ryzyka mają największy wpływ?

Przedstaw ryzyka w tabeli:

| Ryzyko | Prawdopodobieństwo      | Wpływ                   | Priorytet | Strategia reagowania                         |
| ------ | ------------------------ | ------------------------ | --------- | -------------------------------------------- |
| ...    | niski / średni / wysoki | niski / średni / wysoki | ...       | unikanie / mitigacja / transfer / akceptacja |

### 5.2. Kontyngencje

- Jaki jest plan B dla kluczowych kroków?
- Kiedy uruchomić kontyngencję?
- Jaki jest koszt kontyngencji?

### 5.3. Punkty decyzyjne

- W których momentach należy podjąć decyzję: kontynuować czy zmienić plan?
- Kto jest decyzyjny?
- Jakie są kryteria decyzji?

---

## 6. Kryteria sukcesu i weryfikacja

### 6.1. Kryteria sukcesu

- Po czym poznamy, że plan się powiódł?
- Jakie są mierzalne wskaźniki?
- Jaki jest minimalny akceptowalny rezultat?

### 6.2. Metryki i monitorowanie

- Co mierzyć w trakcie realizacji?
- Jak często weryfikować postęp?
- Jakie są sygnały ostrzegawcze?

### 6.3. Definicja ukończenia

- Kiedy plan jest uznany za zrealizowany?
- Kto potwierdza ukończenie?
- Jakie są kryteria akceptacji?

---

## 7. Plan i podsumowanie

### 7.1. Plan wykonania

Zbierz wszystkie elementy w spójny plan. Przedstaw go w formie:

1. Krótkie podsumowanie celu i kontekstu.
2. Kroki w kolejności wykonania z przypisanymi zasobami i czasem.
3. Punkty kontrolne i kryteria przejścia.
4. Ryzyka i kontyngencje.
5. Kryteria sukcesu i definicja ukończenia.

### 7.2. Harmonogram

Jeśli ma zastosowanie, przedstaw harmonogram w bloku `text`:

```text
Etap 1 [data] -> Etap 2 [data] -> Punkt kontrolny -> Etap 3 [data] -> Ukończenie [data]
```

### 7.3. Założenia i ograniczenia

Wypisz jawnie:

- założenia przyjęte w planie,
- ograniczenia, które mogą wpłynąć na realizację,
- elementy niezweryfikowane wymagające potwierdzenia.

### 7.4. Najbliższy krok

Wskaż jeden konkretny pierwszy krok operacyjny, który rozpoczyna realizację planu.

---

## Walidacja planu

Przed przedstawieniem planu sprawdź:

- Czy cel jest mierzalny i jasny?
- Czy kroki są w logicznej kolejności?
- Czy zależności są uwzględnione?
- Czy zasoby są wystarczające?
- Czy ryzyka są zidentyfikowane i mają strategię reagowania?
- Czy kryteria sukcesu są mierzalne?
- Czy punkty kontrolne są wyznaczone?
- Czy założenia są oznaczone jako zweryfikowane lub hipotezy?
- Czy plan jest adaptacyjny (może być korygowany)?
- Czy najbliższy krok jest konkretny i wykonalny?

Jeżeli którekolwiek pole ma odpowiedź `nie`, popraw plan albo wyraźnie wskaż ograniczenie.

---

## Kryteria ukończenia

Zadanie można uznać za wykonane, gdy:

- cel planowania został jasno określony,
- kontekst i ograniczenia są zidentyfikowane,
- cel jest rozłożony na kroki w logicznej kolejności,
- zależności między krokami są uwzględnione,
- zasoby są zidentyfikowane z oznaczeniem dostępności,
- ryzyka są zidentyfikowane z strategią reagowania,
- kryteria sukcesu są mierzalne,
- punkty kontrolne są wyznaczone,
- założenia są oznaczone jako zweryfikowane lub hipotezy,
- plan jest przedstawiony w spójnej formie,
- najbliższy krok operacyjny jest wskazany.
