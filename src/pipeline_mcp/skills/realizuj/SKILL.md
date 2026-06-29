---
name: realizuj
description: Wykonuje zmiany w kodzie, konfiguracji albo artefaktach zgodnie z zaakceptowanym planem, korzystając z zasady jak i dokumentacji context7.
version: 1.0.0
argument-hint: "[PLAN DO ZREALIZOWANIA] [opcjonalnie: KONTEKST, ŹRÓDŁA, TRYB]"
triggers:
  - user
  - model
---

# Workflow realizacji zmian

Celem workflowu jest wykonanie zmian w kodzie, konfiguracji albo artefaktach zgodnie z zaakceptowanym planem, z zachowaniem minimalnego zakresu, bezpieczeństwa i zgodności z konwencjami projektu.

Realizacja odpowiada na pytanie "jak wykonać te zmiany?", a nie "jak zaplanować?" albo "czy plan jest poprawny?".

## Rola

Przyjmij rolę eksperta od realizacji zmian w kodzie i artefaktach, łączącego myślenie sekwencyjne, krytyczne i systemowe.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- wykonać zmiany w kodzie zgodnie z planem,
- zaimplementować funkcjonalność,
- zmodyfikować konfigurację,
- wygenerować artefakt zgodnie z ustalonym planem,
- zrealizować kroki z planu `planuj`.

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce zaplanować realizację - użyj skilla `planuj`,
- użytkownik chce zweryfikować twierdzenia - użyj skilla `weryfikacja`,
- użytkownik chce dokonać audytu artefaktu - użyj skilla `sprawdzenie`,
- zadanie jest trywialne i nie wymaga planu - użyj skilla `jak`,
- brak zaakceptowanego planu - najpierw użyj `planuj`.

## Język

Realizację prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `PLAN DO ZREALIZOWANIA` - zaakceptowany plan z krokami.

Opcjonalnie:

- `KONTEKST` - środowisko, sytuacja, ograniczenia,
- `ŹRÓDŁA` - materiały bazowe, dokumentacja,
- `TRYB REALIZACJI` - `szybki`, `pełny` (domyślnie `pełny`), `dogłębny`.

## Kontrola kompletności wejścia

1. Jeśli brakuje `PLAN DO ZREALIZOWANIA`, poproś o wskazanie planu albo przejdź do `planuj`.
2. Jeśli plan jest niejednoznaczny, poproś o doprecyzowanie.
3. Jeśli plan wymaga zmiany w trakcie realizacji, przerwij i zgłoś to.

## Tryby realizacji

- `szybki` - wykonanie kroków z minimalnym komentarzem.
- `pełny` - domyślny: wykonanie kroków z uzasadnieniem decyzji implementacyjnych.
- `dogłębny` - pełne wykonanie z analizą edge case'ów, testami i weryfikacją każdego kroku.

## Źródła prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pułapki.
2. Context7 - dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - notebooki i źródła badawcze użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zależności, graf wywołań.

Stosuj w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi. Konflikty źródeł, hierarchia i reguły uzupełniające: patrz `_shared/zrodla-i-narzedzia.md`.

Reguły specyficzne dla realizacji:

- Składnię i API bibliotek oraz frameworków potwierdzaj przez Context7 przed użyciem.
- Konwencje kodu sprawdzaj w `.ai-kb` i sąsiednich plikach projektu.
- Nie wprowadzaj nowych zależności bez potwierdzenia dostępności.

## Narzędzia lokalne

- `desktop-commander` (pełne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje między encjami, graf zależności, analiza wpływu zmian.

Tabele narzędzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Koperta

`realizuj` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty emitowanej przez `planuj`:
- `pola_stacji.planuj.plan` -> `PLAN DO ZREALIZOWANIA` (wymagane, bezpośrednie),
- `pola_stacji.planuj.kryteria_sukcesu` -> `KONTEKST` (opcjonalne),
- `stan.zamiar` -> `KONTEKST` (kontekstowe).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: realizuj`,
- `stacja_poprzednia: planuj`,
- `pola_stacji.realizuj`: `kroki_wykonane`, `kroki_pominiete`, `kroki_zablokowane`, `zmiany`, `status`,
- `walidacja.stacja_docelowa: weryfikacja`,
- `walidacja.pola_wymagane: [TWIERDZENIE LUB ZBIOR TWIERDZEN]` -> wnioskowane z `zmiany` (każda zmiana implikuje twierdzenie do weryfikacji),
- `relacje`:
  - `stacja:realizuj` -> `stacja:weryfikacja` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:realizuj` (typ: `zawiera`),
  - `stacja:realizuj` -> `zmiana:Z1`, `zmiana:Z2`, ... (typ: `wyprodukowala`, per zmiana),
  - `zmiana:Z1` -> `krok:K1` (typ: `realizuje`, per zmiana realizująca krok planu).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_07_realizuj.yaml` i zaktualizuj manifest.

## Instrukcja główna

Najpierw rozpoznaj typ realizacji. Nie zakładaj z góry, że każda realizacja ma tę samą strukturę.

Możliwe typy realizacji:

- `kod` - zmiany w kodzie źródłowym,
- `konfiguracja` - zmiany w plikach konfiguracyjnych,
- `infrastruktura` - zmiany w infrastrukturze,
- `dokumentacja` - zmiany w dokumentacji,
- `artefakt` - generowanie artefaktu (raport, schemat, model).

Po rozpoznaniu typu dostosuj zakres realizacji.

Zasady:

- Stosuj minimalny konieczny zakres zmian.
- Zachowaj spójność z istniejącym kodem i konwencjami.
- Każda zmiana musi wynikać z planu.
- Jeśli plan wymaga zmiany, przerwij i zgłoś.
- Po każdej zmianie zweryfikuj poprawność (kompilacja, test, kontrola).

---

Realizacja: [PLAN DO ZREALIZOWANIA]

## Rozpoznanie typu realizacji

Określ typ realizacji i uzasadnij.

**Pewność rozpoznania: niski / średni / wysoki.**

## Wykonanie kroków

Dla każdego kroku planu:

| Krok | Status | Zmiany | Uwagi |
| --- | --- | --- | --- |
| 1 | wykonany / pominięty / zablokowany | ... | ... |

## Weryfikacja lokalna

Po wykonaniu zmian sprawdź:

- kompilowalność / poprawność składni,
- zgodność z konwencjami,
- brak błędów oczywistych.

## Wynik

```yaml
kroki_wykonane: []
kroki_pominiete: []
kroki_zablokowane: []
zmiany: []
status: zakonczony | czesciowy | zablokowany
```
