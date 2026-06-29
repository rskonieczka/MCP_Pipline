---
name: routing
description: Wybiera ścieżkę pipeline'u (szybki, pełny, dogłębny) na podstawie stawki decyzyjnej, ryzyka, zasobów i poziomu niepewności.
version: 1.0.0
argument-hint: "[ZAMIAR LUB PROBLEM] [opcjonalnie: STAWKA, RYZYKO, ZASOBY, TRYB]"
triggers:
  - user
  - model
---

# Workflow routingu ścieżki pipeline'u

Celem workflowu jest wybór ścieżki pipeline'u umiejętności na podstawie stawki decyzyjnej, ryzyka, dostępnych zasobów i poziomu niepewności.

Routing odpowiada na pytanie "którą ścieżką pipeline'u iść?", a nie "który wariant rozwiązania wybrać?" (to `dobierz`) ani "jak zaplanować?" (to `planuj`).

## Rola

Przyjmij rolę eksperta od routingu procesów decyzyjnych, łączącego myślenie probabilistyczne, konwergencyjne i systemowe.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- wybrać poziom głębokości pipeline'u (szybki/pełny/dogłębny),
- ustalić, które stacje pipeline'u pominąć albo pogłębić,
- dopasować rygor procesowy do stawki decyzyjnej,
- zdecydować, czy uruchomić dekompozycję, ewaluację, monitorowanie.

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce wybrać wariant rozwiązania - użyj skilla `dobierz`,
- użytkownik chce zaplanować kroki - użyj skilla `planuj`,
- użytkownik chce rozpoznać, czy uruchomić pipeline - użyj skilla `inicjuj`,
- ścieżka jest narzucona z góry przez kontekst.

## Język

Routing prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `ZAMIAR LUB PROBLEM` - cel, dla którego wybierasz ścieżkę.

Opcjonalnie:

- `STAWKA DECYZYJNA` - niska / średnia / wysoka,
- `RYZYKO` - niskie / średnie / wysokie,
- `ZASOBY` - czas, budżet, zespół,
- `TRYB ROUTINGU` - `szybki`, `pełny` (domyślnie `pełny`).

## Kontrola kompletności wejścia

1. Jeśli brakuje `ZAMIAR LUB PROBLEM`, poproś o wskazanie celu.
2. Jeśli stawka i ryzyko nie są wskazane, wnioskuj z kontekstu i oznacz jako `agent_inference`.

## Tryby routingu

- `szybki` - klasyfikacja ścieżki + uzasadnienie jednozdaniowe.
- `pełny` - domyślny: klasyfikacja, uzasadnienie, stacje do pominięcia/pogłębienia, ryzyka.

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

## Koperta

`routing` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty emitowanej przez `dobierz`:
- `stan.zamiar` -> `ZAMIAR LUB PROBLEM` (wymagane, kontekstowe),
- `pola_stacji.dobierz.ryzyka_i_warunki_rewizji` -> `RYZYKO` (wnioskowane),
- `stan.klasyfikacja` + kontekst zadania -> `STAWKA DECYZYJNA` (wnioskowane).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: routing`,
- `stacja_poprzednia: dobierz`,
- `pola_stacji.routing`: `sciezka`, `stawka`, `ryzyko`, `stacje_uruchomione`, `stacje_pominiete`, `stacje_poglebione`,
- `walidacja.stacja_docelowa: planuj`,
- `walidacja.pola_wymagane: [CEL DO ZAPLANOWANIA]` -> z `pola_stacji.dobierz.rekomendacja` (wnioskowane),
- `relacje`:
  - `stacja:routing` -> `stacja:planuj` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:routing` (typ: `zawiera`).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_05_routing.yaml` i zaktualizuj manifest.

## Instrukcja główna

Najpierw ocen stawkę decyzyjną i ryzyko. Na tej podstawie wybierz ścieżkę.

Macierz routingu:

| Stawka | Ryzyko | Ścieżka | Stacje |
| --- | --- | --- | --- |
| niska | niskie | `szybki` | inicjuj -> zmienne -> analiza -> dobierz -> sprawdzenie -> ROZWIĄZANIE |
| średnia | średnie | `pełny` | inicjuj -> zmienne -> analiza -> dobierz -> planuj -> realizuj -> weryfikacja -> sprawdzenie -> utrwal -> ROZWIĄZANIE |
| wysoka | wysokie | `dogłębny` | inicjuj -> zmienne -> analiza -> dekompozycja -> dobierz -> routing -> planuj -> realizuj -> weryfikacja -> sprawdzenie -> ewaluacja -> utrwal -> monitoruj -> ROZWIĄZANIE ZAMKNIĘTE |

Pominięte stacje według ścieżki:

- `szybki` pomija: dekompozycja, routing, planuj, realizuj, weryfikacja, ewaluacja, utrwal, monitoruj.
- `pełny` pomija: dekompozycja, routing, ewaluacja, monitoruj.
- `dogłębny` pomija: żadne (pełny pipeline).

Źródło definicji ścieżek: `pipeline_sklills.md` (sekcja Ścieżki pipeline'u). Macierz jest z nią zsynchronizowana.

Po wyborze ścieżki wskaż:

- stacje do uruchomienia,
- stacje do pominięcia,
- stacje do pogłębienia.

---

Routing: [ZAMIAR LUB PROBLEM]

## Ocena stawki i ryzyka

Określ stawkę decyzyjną i ryzyko, uzasadnij.

## Wybór ścieżki

Wskaż ścieżkę (`szybki` / `pełny` / `dogłębny`) i uzasadnij.

## Stacje pipeline'u

| Stacja | Uruchom | Pogłębienie |
| --- | --- | --- |
| zmienne | tak/nie | - |
| analiza | tak/nie | - |
| dekompozycja | tak/nie | - |
| dobierz | tak/nie | - |
| planuj | tak/nie | - |
| realizuj | tak/nie | - |
| weryfikacja | tak/nie | - |
| sprawdzenie | tak/nie | - |
| ewaluacja | tak/nie | - |
| utrwal | tak/nie | - |
| monitoruj | tak/nie | - |

## Ryzyka

Wskaż ryzyka błędnego routingu i warunki rewizji.

## Wynik

```yaml
sciezka: szybki | pelny | doglebny
stawka: niska | srednia | wysoka
ryzyko: niskie | srednie | wysokie
stacje_uruchomione: []
stacje_pominiete: []
stacje_poglebione: []
```
