# Sciezki pipeline'u i routing

Pipeline posiada 3 sciezki wykonania wybierane na podstawie stawki decyzyjnej i ryzyka. W sciezce `szybki` i `pelny` wyboru dokonuje stacja `inicjuj` (klasyfikacja zamiaru). `routing` jest uruchamiane tylko w sciezce `doglebny`.

## 1. Sciezka szybki (niska stawka, niskie ryzyko)

Klasyfikacja `inicjuj`: `trywialne` z wymaga weryfikacji lub `rutynowe` o niskiej stawce.

```text
[inicjuj] -> [zmienne] -> [analiza] -> [dobierz] -> [sprawdzenie] -> [ROZWIĄZANIE]
```

Stacje pomijane: dekompozycja, routing, planuj, realizuj, weryfikacja, ewaluacja, utrwal, monitoruj.

Bramka jakosci: `sprawdzenie` konczy pipeline i przechodzi bezposrednio do `ROZWIĄZANIE` bez bramki.

| Kryterium | Wartosc |
|---|---|
| Stawka decyzyjna | niska |
| Ryzyko | niskie |
| Liczba podproblemow | 1 |
| Wymaga zrodel zewnetrznych | nie |
| Wymaga weryfikacji | tak |
| Wymaga dekompozycji | nie |
| Wymaga ewaluacji ex-post | nie |

## 2. Sciezka pelny (srednia stawka, srednie ryzyko)

Klasyfikacja `inicjuj`: `rutynowe`.

```text
[inicjuj] -> [zmienne] -> [analiza] -> [dobierz] -> [planuj] -> [realizuj]
-> [weryfikacja] -> [sprawdzenie] -> [utrwal] -> [ROZWIĄZANIE]
```

Stacje pomijane: dekompozycja, routing, ewaluacja, monitoruj.

Bramka jakosci: po `sprawdzenie` nastepuje bramka. `zgodny` -> `utrwal`. `niezgodny` -> powrot do `dobierz` lub `planuj` (max 2 iteracje).

| Kryterium | Wartosc |
|---|---|
| Stawka decyzyjna | srednia |
| Ryzyko | srednie |
| Liczba podproblemow | 1-2 |
| Wymaga zrodel zewnetrznych | tak |
| Wymaga weryfikacji | tak |
| Wymaga dekompozycji | nie |
| Wymaga ewaluacji ex-post | nie |

## 3. Sciezka doglebny (wysoka stawka, wysokie ryzyko)

Klasyfikacja `inicjuj`: `zlozone`.

```text
[inicjuj] -> [zmienne] -> [analiza] -> [dekompozycja] -> [dobierz] -> [routing]
-> [planuj] -> [realizuj] -> [weryfikacja] -> [sprawdzenie]
-> [BRAMKA JAKOSCI] -> [ewaluacja] -> [utrwal] -> [monitoruj] -> [ROZWIĄZANIE ZAMKNIĘTE]
```

Wszystkie stacje uruchomione.

Bramka jakosci: po `sprawdzenie` nastepuje bramka. `zgodny` -> `ewaluacja`. `niezgodny` -> powrot do `dobierz` lub `planuj` (max 2 iteracje).

| Kryterium | Wartosc |
|---|---|
| Stawka decyzyjna | wysoka |
| Ryzyko | wysokie |
| Liczba podproblemow | 3+ |
| Wymaga zrodel zewnetrznych | tak |
| Wymaga weryfikacji | tak |
| Wymaga dekompozycji | tak |
| Wymaga ewaluacji ex-post | tak |

## 4. Tabela zbiorcza sciezek

| Stacja | szybki | pelny | doglebny |
|---|---|---|---|
| inicjuj | tak | tak | tak |
| zmienne | tak | tak | tak |
| analiza | tak | tak | tak |
| dekompozycja | nie | nie | tak |
| dobierz | tak | tak | tak |
| routing | nie | nie | tak |
| planuj | nie | tak | tak |
| realizuj | nie | tak | tak |
| weryfikacja | nie | tak | tak |
| sprawdzenie | tak | tak | tak |
| ewaluacja | nie | nie | tak |
| utrwal | nie | tak | tak |
| monitoruj | nie | nie | tak |
| audyt_runu | nie | nie | opcjonalnie |

## 5. Routing

Stacja `routing` jest uruchamiana tylko w sciezce `doglebny`, gdy stawka i ryzyko sa wysokie i wymagaja jawnej analizy sciezki.

### 5.1. Wejscie

Wymagane:
- `ZAMIAR LUB PROBLEM` - z kontekstu konwersacji (stan.zamiar w kopercie)

Opcjonalne:
- `STAWKA DECYZYJNA` - niska | srednia | wysoka
- `RYZYKO` - niskie | srednie | wysokie
- `ZASOBY` - dostepne zasoby
- `TRYB ROUTINGU` - szybki | pelny | doglebny

### 5.2. Wyjscie

```yaml
sciezka: szybki | pelny | doglebny
stawka: niska | srednia | wysoka
ryzyko: niskie | srednie | wysokie
stacje_uruchomione: []
stacje_pominiete: []
stacje_poglebione: []
```

### 5.3. Implementacja w serwerze

Serwer implementuje logike routing'u w `routing.py`:

```python
def determine_path(klasyfikacja: str, stawka: str, ryzyko: str) -> str:
    if klasyfikacja == "trywialne":
        return "szybki"
    elif klasyfikacja == "rutynowe":
        if stawka == "niska" and ryzyko == "niskie":
            return "szybki"
        return "pelny"
    elif klasyfikacja == "zlozone":
        return "doglebny"

def get_station_sequence(path: str) -> list[str]:
    PATHS = {
        "szybki": ["inicjuj", "zmienne", "analiza", "dobierz", "sprawdzenie"],
        "pelny": ["inicjuj", "zmienne", "analiza", "dobierz", "planuj",
                  "realizuj", "weryfikacja", "sprawdzenie", "utrwal"],
        "doglebny": ["inicjuj", "zmienne", "analiza", "dekompozycja",
                     "dobierz", "routing", "planuj", "realizuj",
                     "weryfikacja", "sprawdzenie", "ewaluacja",
                     "utrwal", "monitoruj"]
    }
    return PATHS[path]

def get_next_station(current: str, path: str, gate_status: str = "") -> str | None:
    sequence = get_station_sequence(path)
    idx = sequence.index(current)
    if idx + 1 >= len(sequence):
        return None  # ostatnia stacja
    return sequence[idx + 1]
```

## 6. Wywolanie od srodkowej stacji

Serwer obsluguje wywolanie pipeline od dowolnej stacji (tryb hybrydowy), jesli agent ma juz wyniki poprzednich stacji. Wymaga:

1. `start_run` z `zamiar` i `kontekst`
2. `update_envelope` z polami poprzednich stacji (reczne wypelnienie koperty)
3. `execute_station` od wybranej stacji

Przyklad - uruchomienie od `realizuj` z gotowym planem:

```python
run = start_run(zamiar="Wdroz fix", kontekst="Mam gotowy plan")
update_envelope(run["run_id"], "pola_stacji.planuj", {
    "kroki": [...], "zasoby": [...], "ryzyka": [...],
    "kryteria_sukcesu": [...], "punkty_kontrolne": [...]
})
execute_station(run["run_id"], "realizuj", output={...})
```

## 7. Restart run'u

Restart od ostatniej zakonczonej stacji:

```python
resume_run(run_id)  # odczytuje manifest, zaladuje ostatni checkpoint
# -> zwraca stacje wznowienia i zaladowana koperte
execute_station(run_id, stacja_wznowienia, output={...})
```
