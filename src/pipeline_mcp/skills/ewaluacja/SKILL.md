---
name: ewaluacja
description: Ocenia długoterminową wartość, skuteczność i trafność rozwiązania po jego wdrożeniu, wykraczając poza audyt zgodności.
version: 1.0.0
argument-hint: "[ROZWIĄZANIE LUB ARTEFAKT] [opcjonalnie: CEL ŹRÓDŁOWY, KRYTERIA, HORYZONT, TRYB]"
triggers:
  - user
  - model
---

# Workflow ewaluacji ex-post rozwiązania

Celem workflowu jest ocena długoterminowej wartości, skuteczności i trafności rozwiązania po jego wdrożeniu, wykraczająca poza audyt zgodności z pytaniem (to `sprawdzenie`) i weryfikację prawdziwości twierdzeń (to `weryfikacja`).

Ewaluacja odpowiada na pytanie "na ile rozwiązanie osiągnęło cel i jakie wnioski na przyszłość?", a nie "czy artefakt jest zgodny z pytaniem?" albo "czy twierdzenie jest prawdziwe?".

## Rola

Przyjmij rolę eksperta od ewaluacji ex-post, łączącego myślenie krytyczne, probabilistyczne i systemowe.

## Kiedy stosować

Stosuj, gdy użytkownik chce:

- ocenić skuteczność wdrożonego rozwiązania,
- zmierzyć, na ile cel został osiągnięty,
- wyciągnąć wnioski na przyszłość,
- ocenić długoterminową wartość, nie tylko zgodność,
- porównać rezultaty z założeniami.

## Kiedy nie stosować

Nie stosuj, gdy:

- użytkownik chce audytować zgodność artefaktu z pytaniem - użyj skilla `sprawdzenie`,
- użytkownik chce zweryfikować prawdziwość twierdzeń - użyj skilla `weryfikacja`,
- rozwiązanie nie zostało jeszcze wdrożone - użyj skilla `sprawdzenie`,
- brak kryteriów oceny i nie można ich wnioskować.

## Język

Ewaluację prowadź i zwracaj wyłącznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejście

Wymagane:

- `ROZWIĄZANIE LUB ARTEFAKT` - co ma zostać ocenione.

Opcjonalnie:

- `CEL ŹRÓDŁOWY` - pierwotny cel rozwiązania,
- `KRYTERIA EWALUACJI` - metryki sukcesu,
- `HORYZONT` - krótkoterminowy / średnioterminowy / długoterminowy,
- `ŹRÓDŁA` - dane, metryki, feedback,
- `TRYB EWALUACJI` - `szybki`, `pełny` (domyślnie `pełny`), `dogłębny`.

## Kontrola kompletności wejścia

1. Jeśli brakuje `ROZWIĄZANIE LUB ARTEFAKT`, poproś o wskazanie.
2. Jeśli brakuje `CEL ŹRÓDŁOWY`, wnioskuj z kontekstu i oznacz jako `agent_inference`.
3. Jeśli brakuje `KRYTERIA EWALUACJI`, wyprowadź z celu i oznacz jako `kryteria wnioskowane`.
4. Jeśli brakuje danych do oceny skuteczności, ustaw status `ograniczony`.

## Tryby ewaluacji

- `szybki` - ocena głównych kryteriów + wnioski.
- `pełny` - domyślny: wszystkie wymiary, wnioski, rekomendacje.
- `dogłębny` - pełna analiza z metrykami, scenariuszami, analizą wrażliwości.

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

`ewaluacja` uczestniczy w mechanizmie wymiany danych pipeline'u. Pełna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych między stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczęciem pracy odczytaj z koperty emitowanej przez `sprawdzenie`:
- `pola_stacji.realizuj.zmiany` -> `ROZWIĄZANIE LUB ARTEFAKT` (wymagane, wnioskowane),
- `stan.zamiar` -> `CEL ŹRÓDŁOWY` (wymagane, kontekstowe),
- `pola_stacji.planuj.kryteria_sukcesu` -> `KRYTERIA EWALUACJI` (opcjonalne, wnioskowane),
- `pola_stacji.sprawdzenie.wymiary` -> dane pomocnicze (opcjonalne).

### Emisja (zapis do koperty)

Po zakończeniu pracy emituj kopertę z:
- `stacja_aktualna: ewaluacja`,
- `stacja_poprzednia: sprawdzenie`,
- `pola_stacji.ewaluacja`: `typ_ewaluacji`, `ocena_ogolna`, `wymiary` (5 wymiarów), `wnioski`, `rekomendacje`, `status`,
- `walidacja.stacja_docelowa: utrwal`,
- `walidacja.pola_wymagane: [WNIOSKI LUB DECYZJE]` -> z `pola_stacji.ewaluacja.wnioski` (bezpośrednie),
- `relacje`:
  - `stacja:ewaluacja` -> `stacja:utrwal` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:ewaluacja` (typ: `zawiera`),
  - `stacja:ewaluacja` -> `wniosek:WN1`, `wniosek:WN2`, ... (typ: `wyprodukowala`, per wniosek),
  - `wniosek:WN1` -> `stacja:ewaluacja` (typ: `wyprowadzony_z`, per wniosek wyprowadzony ze stacji).

Po wyemitowaniu koperty zapisz ją do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_10_ewaluacja.yaml` i zaktualizuj manifest.

## Instrukcja główna

Najpierw rozpoznaj typ ewaluacji. Nie zakładaj z góry, że każda ewaluacja ma tę samą strukturę.

Możliwe typy ewaluacji:

- `skutecznościowa` - czy cel został osiągnięty,
- `wartościowa` - jaka jest długoterminowa wartość,
- `porównawcza` - porównanie z alternatywami,
- `procesowa` - ocena procesu powstawania,
- `ekonomiczna` - stosunek kosztu do korzyści.

Po rozpoznaniu typu dostosuj zakres.

Wymiary ewaluacji:

1. **Trafność** - czy rozwiązanie adresuje właściwy problem.
2. **Skuteczność** - na ile cel został osiągnięty.
3. **Wydajność** - stosunek rezultatu do zasobów.
4. **Trwałość** - czy rezultat utrzymuje się w czasie.
5. **Skalowalność** - czy rozwiązanie skaluje się.

---

Ewaluacja: [ROZWIĄZANIE LUB ARTEFAKT]

## Rozpoznanie typu ewaluacji

Określ typ i uzasadnij.

**Pewność rozpoznania: niski / średni / wysoki.**

## Ocena wymiarów

| Wymiar | Ocena | Uzasadnienie | Pewność |
| --- | --- | --- | --- |
| Trafność | wysoka / średnia / niska | ... | ... |
| Skuteczność | ... | ... | ... |
| Wydajność | ... | ... | ... |
| Trwałość | ... | ... | ... |
| Skalowalność | ... | ... | ... |

## Wnioski na przyszłość

Wskaż, co należy zmienić w przyszłych rozwiązaniach.

## Rekomendacje

Wskaż działania naprawcze albo rozwijające.

## Wynik

```yaml
typ_ewaluacji: skutecznosciowa | wartosciowa | porownawcza | procesowa | ekonomiczna
ocena_ogolna: wysoka | srednia | niska
wymiary: {}
wnioski: []
rekomendacje: []
status: pelny | ograniczony | niemozliwy
```
