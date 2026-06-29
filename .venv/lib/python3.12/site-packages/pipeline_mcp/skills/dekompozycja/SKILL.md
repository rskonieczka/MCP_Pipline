---
name: dekompozycja
description: Dzieli złożony problem na podproblemy zależne i niezależne, ustala kolejność i warunki brzegowe rozwiązywania.
version: 1.0.0
argument-hint: "[PROBLEM LUB CEL ZŁOŻONY] [opcjonalnie: KONTEKST, OGRANICZENIA, TRYB]"
triggers:
  - user
  - model
---

# Workflow dekompozycji problemu

Celem workflowu jest rozbicie złożonego problemu albo celu na mniejsze, wykonalne podproblemy z jawnymi zależnościami, kolejnością i warunkami brzegowymi.

Dekompozycja odpowiada na pytanie "z jakich podproblemów składa się ten problem i w jakiej kolejności je rozwiązywać?", a nie "czym jest obiekt?" albo "jak osiągnąć cel krok po kroku?".

## Rola

Przyjmij rolę eksperta od dekompozycji problemów, łączącego myślenie systemowe, analityczne i sekwencyjne.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- podzielić złożony problem na podproblemy,
- ustalić zależności między częściami problemu,
- zidentyfikować podproblemy krytyczne i pomocnicze,
- zaplanować kolejność rozwiązywania podproblemów,
- rozbić duży cel na jednostki wykonalne.

## Kiedy nie stosować

Nie stosuj, gdy:

- problem jest pojedynczy i nie wymaga podziału - użyj skilla `analiza`,
- użytkownik chce zaplanować kroki realizacji - użyj skilla `planuj`,
- użytkownik chce wybrać wariant rozwiązania - użyj skilla `dobierz`,
- użytkownik chce rozpoznać, czy problem wymaga pipeline'u - użyj skilla `inicjuj`.

## Język

Dekompozycję prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `PROBLEM LUB CEL ZŁOŻONY` - co ma zostać podzielone.

Opcjonalnie:

- `KONTEKST` - środowisko, sytuacja, ograniczenia,
- `OGRANICZENIA` - warunki twarde i miękkie,
- `ŹRÓDŁA` - materiały bazowe,
- `TRYB DEKOMPOZYCJI` - `szybki`, `pełny` (domyślnie `pełny`), `dogłębny`.

## Kontrola kompletności wejścia

1. Jeśli brakuje `PROBLEM LUB CEL ZŁOŻONY`, poproś o wskazanie problemu.
2. Jeśli problem jest niejednoznaczny, najpierw rozstrzygnij, co dokładnie dzielisz.
3. Jeśli ograniczenia nie są wskazane, wnioskuj z kontekstu i oznacz jako `agent_inference`.

## Tryby dekompozycji

- `szybki` - lista podproblemów + zależności + kolejność.
- `pełny` - domyślny: podproblemy, zależności, kolejność, krytyczność, warunki brzegowe.
- `dogłębny` - pełna analiza zależności, scenariusze alternatywne, analiza wrażliwości.

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

`dekompozycja` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty emitowanej przez `analiza`:
- `pola_stacji.analiza.wnioski` + `pola_stacji.analiza.ograniczenia` -> `PROBLEM LUB CEL ZŁOŻONY` (wymagane, wnioskowane przez `agent_inference`),
- `pola_stacji.analiza.raport_streszczenie` -> `KONTEKST` (opcjonalne),
- `stan.zamiar` -> `KONTEKST` (opcjonalne, kontekstowe).

Jeśli `wnioski` i `ograniczenia` nie pozwalają wyprowadzić `PROBLEM LUB CEL ZŁOŻONY`, poproś użytkownika o doprecyzowanie.

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: dekompozycja`,
- `stacja_poprzednia: analiza`,
- `pola_stacji.dekompozycja`: `podproblemy`, `zaleznosci`, `kolejnosc`, `krytyczne`,
- `walidacja.stacja_docelowa: dobierz`,
- `walidacja.pola_wymagane: [CEL DOBORU]` -> wnioskowane z `podproblemy`,
- `relacje`:
  - `stacja:dekompozycja` -> `stacja:dobierz` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:dekompozycja` (typ: `zawiera`),
  - `stacja:dekompozycja` -> `podproblem:P1`, `podproblem:P2`, ... (typ: `wyprodukowala`, per podproblem),
  - `podproblem:P1` -> `podproblem:P2` (typ: `zalezy_od`, per zależność z `zaleznosci{}`).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_03_dekompozycja.yaml` i zaktualizuj manifest.

## Instrukcja główna

Najpierw rozpoznaj typ problemu. Nie zakładaj z góry, że każdy problem dzieli się tak samo.

Możliwe typy dekompozycji:

- `funkcjonalna` - podział według funkcji albo modułów,
- `warstwowa` - podział według warstw abstrakcji,
- `przestrzenna` - podział według obszarów problemu,
- `czasowa` - podział według faz czasowych,
- `zależnościowa` - podział według grafu zależności.

Po rozpoznaniu typu dostosuj zakres dekompozycji.

Zasady:

- Każdy podproblem musi być wykonalny niezależnie albo z jawnymi zależnościami.
- Oznacz podproblemy krytyczne (blokujące inne) i pomocnicze.
- Ustal kolejność rozwiązywania na podstawie zależności.

---

Dekompozycja: [PROBLEM LUB CEL ZŁOŻONY]

## Rozpoznanie typu problemu

Określ typ problemu i uzasadnij wybór metody dekompozycji.

**Pewność rozpoznania: niski / średni / wysoki.**

## Podproblemy

Przedstaw podproblemy w tabeli:

| ID | Podproblem | Typ | Krytyczność | Zależności |
| --- | --- | --- | --- | --- |
| P1 | ... | funkcjonalna / warstwowa / ... | krytyczny / pomocniczy | - |
| P2 | ... | ... | ... | P1 |

## Graf zależności

Przedstaw schemat zależności w bloku `text`:

```text
P1 -> P2 -> P3
P1 -> P4
P2 -> P5
```

## Kolejność rozwiązywania

Ustal kolejność na podstawie zależności i krytyczności.

## Warunki brzegowe

Wskaż warunki, w których dekompozycja wymaga rewizji.

## Wynik

```yaml
podproblemy: []
zaleznosci: {}
kolejnosc: []
krytyczne: []
```
