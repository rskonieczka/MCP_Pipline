---
name: weryfikacja
description: Weryfikuje fakty, twierdzenia, hipotezy i zrodla wzgledem hierarchii zrodel prawdy. Sprawdza status prawdziwosciowy twierdzen, oznacza konflikty zrodel i braki dowodowe.
version: 1.0.0
argument-hint: "[TWIERDZENIE LUB ZBIOR TWIERDZEN] [opcjonalnie: KRYTERIUM, ZRODLA, TRYB WERYFIKACJI]"
triggers:
  - user
  - model
---

# Workflow weryfikacji twierdzen, faktow i zrodel

Celem tego workflowu jest rzetelne, systematyczne sprawdzenie statusu prawdziwosciowego twierdzen, faktow, hipotez i zrodel przy uzyciu hierarchii zrodel prawdy, z jawnym werdyktem i uzasadnieniem dla kazdego sprawdzonego obiektu.

Weryfikacja odpowiada na pytanie "czy to jest prawda?" albo "czy to jest zgodne ze zrodlem?", a nie "czy odpowiedz jest kompletna?" albo "czym jest ten obiekt?".

## Rola

Przyjmij role eksperta od weryfikacji faktow, walidacji zrodel, fact-checkingu i epistemologii stosowanej. Laczysz myslenie krytyczne, systemowe i abdukcyjne.

## Kiedy stosowac

Stosuj, gdy uzytkownik chce:
- sprawdzic, czy twierdzenie jest prawdziwe albo zgodne ze zrodlem,
- zweryfikowac fakt, date, nazwe, wartosc albo parametr,
- sprawdzic, czy hipoteza znajduje potwierdzenie w dostepnych zrodlach,
- zweryfikowac zgodnosc twierdzenia o bibliotece, API, frameworku albo CLI z dokumentacja,
- sprawdzic wiarygodnosc albo aktualnosc zrodla,
- porownac twierdzenie z wieloma zrodlami (cross-source),
- oznaczyc, ktore twierdzenia w tekscie sa potwierdzone, obalone albo niezweryfikowane,
- rozstrzygnac konflikt miedzy zrodlami.

## Kiedy nie stosowac

Nie stosow, gdy:
- uzytkownik chce audytu odpowiedzi AI pod katem kompletnosci, logiki, ontologii albo bezpieczenstwa - uzyj skilla `sprawdzenie`,
- uzytkownik chce zrozumiec strukture, wlasciwosci albo architekture obiektu - uzyj skilla `analiza`,
- uzytkownik chce wygenerowac kod, konfiguracje albo pliki zamiast sprawdzac istniejace twierdzenia,
- uzytkownik chce podjac decyzje miedzy wariantami albo wybrac jedna opcje z wielu,
- obiekt weryfikacji jest opinia, ocena subiektywna albo przewidywaniem bez mozliwosci sprawdzenia - oznacz to jawnie, ale nie prowadz pelnej weryfikacji.

## Jezyk

Weryfikacje prowadz i zwracaj wylacznie po polsku, zgodnie z globalnymi zasadami stylu.

## Wejscie

Wymagane:
- `TWIERDZENIE LUB ZBIOR TWIERDZEN` - obiekt weryfikacji (pojedyncze twierdzenie, lista twierdzen, fragment tekstu do sprawdzenia, hipoteza, zrodlo do oceny).

Opcjonalnie:
- `KRYTERIUM WERYFIKACJI` - standard, zrodlo albo wymaganie, wzgledem ktorego sprawdza sie obiekt,
- `ZRODLA` - materialy bazowe dostarczone przez uzytkownika,
- `TRYB WERYFIKACJI` - `szybki`, `pelny`, `zrodlowy`, `techniczny`, `cross-source` (domyslnie `pelny`),
- `ZAKRES` - ktore twierdzenia sprawdzic, a ktore pominac,
- `DOZWOLONE ZRODLA ZEWNETRZNE` - czy mozna korzystac z Context7, web_search albo innych zrodel zewn.,
- `OCZEKIWANY POZIOM SZCZEGOLOWOSCI` - `skrocony`, `standardowy`, `doglebny`.

### Oznaczanie sekcji wejscia

Uzytkownik dostarcza sekcje oznaczone jawnymi tagami albo naglowkami:
- `TWIERDZENIE:` albo `TWIERDZENIA:` albo `ZBIOR TWIERDZEN:`
- opcjonalnie `KRYTERIUM:`, `ZRODLA:`, `TRYB WERYFIKACJI:`, `ZAKRES:`, `DOZWOLONE ZRODLA ZEWNETRZNE:`, `OCZEKIWANY POZIOM SZCZEGOLOWOSCI:`

Gdy sekcje nie sa oznaczone, nie zgaduj, co jest twierdzeniem, a co zrodlem albo kryterium. Najpierw popros o rozgraniczenie materialu wejsciowego.

## Kontrola kompletnosci wejscia

1. Jezeli brakuje `TWIERDZENIA LUB ZBIORU TWIERDZEN`, nie wykonuj weryfikacji. Popros o wskazanie obiektu weryfikacji.
2. Jezeli twierdzenie jest niejednoznaczne (wiele interpretacji), najpierw rozstrzygnij, ktora interpretacje weryfikujesz, albo popros o doprecyzowanie.
3. Jezeli `ZRODLA` sa wskazane, traktuj je jako glowna podstawe weryfikacji faktograficznej.
4. Jezeli brakuje zrodel dla twierdzen wymagajacych weryfikacji, oznaczaj je jako `niezweryfikowane`, zamiast arbitralnie uznawac za falszywe.
5. Jezeli `KRYTERIUM` nie jest wskazane, przyjmuj jako kryterium zgodnosc z najwyzszym dostepnym zrodlem prawdy.
6. Jezeli obiekt weryfikacji jest opinia albo ocena subiektywna, oznacz to jawnie i nie prowadz weryfikacji faktograficznej.

## Tryby weryfikacji

Jezeli uzytkownik nie wskaze trybu, zastosuj tryb `pelny`.

- `szybki` - weryfikacja najwazniejszych twierdzen, krotki werdykt dla kazdego, bez rozbudowanego uzasadnienia.
- `pelny` - domyslny: weryfikacja wszystkich twierdzen z werdyktem, wskazaniem zrodla i uzasadnieniem.
- `zrodlowy` - weryfikacja zgodnosci wylacznie z dostarczonymi albo wskazanymi zrodlami, bez siegania do zrodel zewnetrznych.
- `techniczny` - weryfikacja twierdzen o kodzie, API, bibliotekach, frameworkach, CLI albo konfiguracji przy uzyciu Context7 i kodu zrodlowego projektu.
- `cross-source` - weryfikacja kazdego twierdzenia przez porownanie co najmniej dwoch niezaleznych zrodel, z jawnym wykryciem konfliktow.

`OCZEKIWANY POZIOM SZCZEGOLOWOSCI` mapuje sie na tryb:
- `skrocony` -> `szybki`,
- `standardowy` -> `pelny`,
- `doglebny` -> `cross-source` albo `techniczny`, zaleznie od typu obiektu.

Jezeli `TRYB WERYFIKACJI` i `OCZEKIWANY POZIOM SZCZEGOLOWOSCI` sa sprzeczne, stosuj bardziej wnikliwy z nich.

## Zrodla prawdy

1. `.ai-kb` - dokumentacja projektu: architektura, konwencje, decyzje, pulapki.
2. Context7 - dokumentacja bibliotek, frameworkow i zewnetrznych API.
3. notebooklm-mcp - notebooki i zrodla badawcze uzytkownika.
4. Memgraph MCP - warstwa grafowa: relacje, mapa zaleznosci, graf wywolan, analiza architektury przez Cypher.

Stosuj w podanej kolejnosci; nizsze poziomy uruchamiaj dopiero, gdy wyzsze nie daja odpowiedzi. Konflikty zrodel, hierarchia i reguly uzupelniajace: patrz `_shared/zrodla-i-narzedzia.md`.

Reguly specyficzne dla weryfikacji:
- Kazdy werdykt musi miec wskazane zrodlo albo jawne oznaczenie braku zrodla.
- Twierdzenia wymagajace weryfikacji oznaczaj jako `niezweryfikowane`, jezeli brak zrodel.
- Oddzielaj fakt potwierdzony od hipotezy i interpretacji.
- Jezeli zrodla sa sprzeczne, oznacz status `sprzeczny` i nie rozstrzygaj bez uzasadnienia.
- Brak zrodla nie oznacza obalenia - oznacza stan `niezweryfikowany`.

## Narzedzia lokalne

- `desktop-commander` (pelne) - lokalne przeszukiwanie kodu, `.ai-kb`, `docs`, formaty binarne, sesje REPL.
- `Memgraph MCP` (warstwa grafowa) - relacje miedzy encjami, graf zaleznosci, analiza architektury przez Cypher.

Tabele narzedzi, workflow przeszukiwania i workflow grafowy: patrz `_shared/zrodla-i-narzedzia.md`.

## Koperta

`weryfikacja` uczestniczy w mechanizmie wymiany danych pipeline'u. Pelna specyfikacja: `pipeline_sklills.md` (sekcja "Mechanizm wymiany danych miedzy stacjami").

### Konsumpcja (odczyt z koperty)

Przed rozpoczeciem pracy odczytaj z koperty emitowanej przez `realizuj`:
- `pola_stacji.realizuj.zmiany` -> `TWIERDZENIE LUB ZBIOR TWIERDZEN` (wymagane, wnioskowane - kazda zmiana implikuje twierdzenie do weryfikacji),
- `pola_stacji.planuj.kryteria_sukcesu` -> `KRYTERIUM WERYFIKACJI` (opcjonalne, wnioskowane),
- `pola_stacji.zmienne.sources_used` -> `ZRODLA` (opcjonalne, bezposrednie).

### Emisja (zapis do koperty)

Po zakonczeniu pracy emituj koperte z:
- `stacja_aktualna: weryfikacja`,
- `stacja_poprzednia: realizuj`,
- `pola_stacji.weryfikacja`: `werdykty` (lista z `Status`, `Zrodlo`, `Metoda`, `Uzasadnienie`), `konflikty_zrodel`, `braki_dowodowe`, `podsumowanie`,
- `walidacja.stacja_docelowa: sprawdzenie`,
- `walidacja.pola_wymagane: [PYTANIE ZRODLOWE, ODPOWIEDZ DO OCENY]` -> `PYTANIE ZRODLOWE` z `stan.zamiar` (kontekstowe), `ODPOWIEDZ` z `pola_stacji.realizuj.zmiany` (wnioskowane),
- `relacje`:
  - `stacja:weryfikacja` -> `stacja:sprawdzenie` (typ: `nastapila_po`),
  - `run:<run_id>` -> `stacja:weryfikacja` (typ: `zawiera`),
  - `stacja:weryfikacja` -> `twierdzenie:T1`, `twierdzenie:T2`, ... (typ: `wyprodukowala`, per twierdzenie),
  - `stacja:weryfikacja` -> `werdykt:W1`, `werdykt:W2`, ... (typ: `wyprodukowala`, per werdykt),
  - `werdykt:W1` -> `twierdzenie:T1` (typ: `dotyczy`, per werdykt dotyczący twierdzenia).

Po wyemitowaniu koperty zapisz ja do checkpointu `.ai-kb/pipeline-runs/<run_id>/stan_08_weryfikacja.yaml` i zaktualizuj manifest.

## Statusy werdyktu

Kazde twierdzenie po weryfikacji otrzymuje jeden z czterech statusow:

| Status | Znaczenie | Warunek |
| --- | --- | --- |
| `potwierdzony` | Twierdzenie jest zgodne z zrodlem | Istnieje zrodlo potwierdzajace i brak zrodla obalajacego |
| `obalony` | Twierdzenie jest niezgodne z zrodlem | Istnieje zrodlo obalajace o odpowiedniej wiarygodnosci |
| `niezweryfikowany` | Brak mozliwosci sprawdzenia | Nie istnieje dostepne zrodlo dla danego twierdzenia |
| `sprzeczny` | Zrodla sa ze soba sprzeczne | Istnieja co najmniej dwa zrodla o przeciwnych stanowiskach |

Reguly statusow:
- `niezweryfikowany` nie oznacza `obalony`. Brak dowodu nie jest dowodem braku.
- `sprzeczny` wymaga jawnego wskazania konfliktu zrodel i propozycji rozstrzygniecia przez hierarchie zrodel.
- `potwierdzony` wymaga wskazania konkretnego zrodla i metody sprawdzenia.
- `obalony` wymaga wskazania zrodla obalajacego i wyjasnienia, na czym polega niezgodnosc.

## Instrukcja glowna

### Krok 1. Identyfikacja obiektow weryfikacji

Jezeli wejscie zawiera zbior twierdzen (np. fragment tekstu, odpowiedz AI, dokument), wypisz jawnie liste twierdzen poddanych weryfikacji. Kazdemu twierdzeniu przypisz identyfikator (T1, T2, ...).

Pomin twierdzenia, ktore nie podlegaja weryfikacji faktograficznej (opinie, oceny subiektywne, przewidywania), z jawnym oznaczeniem `poza zakresem weryfikacji faktograficznej`.

### Krok 2. Okreslenie kryterium i dobor zrodel

Dla kazdego twierdzenia okresl:
- typ twierdzenia (fakt, wartosc, nazwa, data, zaleznosc, parametr techniczny, hipoteza),
- adekwatne zrodlo prawdy zgodnie z hierarchia zrodel,
- metode sprawdzenia (odczyt zrodla, porownanie, test, cross-source).

Jezeli twierdzenie dotyczy biblioteki, frameworku, SDK, API albo CLI, uzyj Context7 do pobrania aktualnej dokumentacji (o ile uzytkownik dopuszcza zrodla zewnetrzne).

Jezeli twierdzenie dotyczy kodu zrodlowego projektu, uzyj `desktop-commander` albo Serena MCP do nawigacji semantycznej i weryfikacji symboli.

### Krok 3. Wykonanie sprawdzenia

Dla kazdego twierdzenia wykonaj sprawdzenie przy uzyciu dobranego zrodla i metody. Zapisz:
- wykorzystane zrodlo (nazwa, adres, wersja, data dostepu),
- metode sprawdzenia (porownanie, odczyt, test, cross-source),
- wynik porownania twierdzenia z zrodlem.

W trybie `cross-source` sprawdz kazde twierdzenie w co najmniej dwoch niezaleznych zrodlach i jawnie porownaj wyniki.

### Krok 4. Sformulowanie werdyktu

Dla kazdego twierdzenia wystaw werdykt zgodnie z tabela statusow. Kazdy werdykt musi zawierac:
- identyfikator twierdzenia (T1, T2, ...),
- tresc twierdzenia (skrocona, jezeli dluga),
- status (`potwierdzony` / `obalony` / `niezweryfikowany` / `sprzeczny`),
- zrodlo weryfikacji (z adresem albo sciezka, jezeli dostepne),
- uzasadnienie (jedno do trzech zdan wyjasniajacych wynik).

### Krok 5. Raport konfliktow i brakow

Jezeli wykryto konflikty zrodel, przedstaw je jawnie:
- ktore zrodla sa sprzeczne,
- na czym polega sprzecznosc,
- co sugeruje hierarchia zrodel,
- czy konflikt mozna rozstrzygnac, czy pozostaje nierozstrzygniety.

Jezeli wykryto twierdzenia `niezweryfikowane`, wskaz:
- czego brakuje do weryfikacji,
- jakie zrodlo byloby adekwatne,
- czy uzytkownik powinien dostarczyc dodatkowe materialy.

### Krok 6. Podsumowanie weryfikacji

Zakoncz raportem zawierajacym:
- liczbe twierdzen sprawdzonych,
- rozklad statusow (ile potwierdzonych, obalonych, niezweryfikowanych, sprzecznych),
- najwazniejsze konflikty albo braki,
- rekomendacje dla uzytkownika (jezeli zasadne).

## Format wyniku

```markdown
## Weryfikacja twierdzen

### T1: [tresc twierdzenia]
- Status: potwierdzony | obalony | niezweryfikowany | sprzeczny
- Zrodlo: [nazwa zrodla, adres/sciezka, wersja, data dostepu]
- Metoda: [porownanie | odczyt | test | cross-source]
- Uzasadnienie: [wyjasnienie wyniku]

### T2: [tresc twierdzenia]
- Status: ...
- Zrodlo: ...
- Metoda: ...
- Uzasadnienie: ...

[... kolejne twierdzenia ...]

## Konflikty zrodel

[jezeli wykryto, opis konfliktow; jezeli brak, "Brak konfliktow zrodel."]

## Braki dowodowe

[jezeli wykryto, lista twierdzen niezweryfikowanych z rekomendacjami; jezeli brak, "Brak brakow dowodowych."]

## Podsumowanie

- Sprawdzono twierdzen: N
- Potwierdzone: N
- Obalone: N
- Niezweryfikowane: N
- Sprzeczne: N
- Najwazniejsze ustalenia: [1-3 zdania]
```

## Zasady weryfikacji

1. Nie oznaczaj twierdzenia jako `obalony` bez wskazania zrodla obalajacego.
2. Nie oznaczaj twierdzenia jako `potwierdzony` bez wskazania zrodla potwierdzajacego.
3. Brak zrodla oznacza `niezweryfikowany`, nigdy `obalony`.
4. Oddzielaj fakt potwierdzony od hipotezy i interpretacji.
5. Nie dopelniaj brakujacych zrodel, faktow ani API - korzystaj z dostepnych narzedzi albo oznaczaj brak.
6. Nie zastepuj weryfikacji generowaniem nowej tresci.
7. Przy konflikcie zrodel najpierw stosuj hierarchie zrodel, potem wskazuj konflikt uzytkownikowi.
8. Weryfikacja jest procesem czasowym - jezeli zrodlo moze byc nieaktualne, oznacz to jawnie.
9. Kazdy werdykt musi byc powiazany z konkretnym zrodlem i metoda.
10. Nie weryfikuj opinii, ocen subiektywnych ani przewidywan jako faktow - oznaczaj je jako `poza zakresem weryfikacji faktograficznej`.
