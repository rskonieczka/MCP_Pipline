# Bramka jakosci i petla zwrotna

Bramka jakosci jest mechanizmem iteracyjnej korekty wyniku pipeline'u. Po stacji `sprawdzenie` nastepuje ocena bramki. Jesli audyt jest niezgodny, pipeline wraca do `dobierz` lub `planuj`. Maksymalnie 2 iteracje, potem eskalacja do uzytkownika.

## 1. Kiedy bramka

| Sciezka | Bramka | Po stacji |
|---|---|---|
| szybki | nie | `sprawdzenie` konczy pipeline |
| pelny | tak | po `sprawdzenie`, przed `utrwal` |
| doglebny | tak | po `sprawdzenie`, przed `ewaluacja` |

## 2. Decyzje bramki

### 2.1. Status zgodny

Audyt `sprawdzenie` zwraca `status_audytu: zgodny`.

- Sciezka pelny -> przejscie do `utrwal`
- Sciezka doglebny -> przejscie do `ewaluacja`

### 2.2. Status niezgodny

Audyt `sprawdzenie` zwraca `status_audytu: niezgodny`.

- Iteracja 1 lub 2 -> powrot do `dobierz` lub `planuj`
- Iteracja 3 -> eskalacja do uzytkownika

### 2.3. Wybor celu powrotu

Bramka wraca do:
- `dobierz` - gdy niezgodnosc dotyczy wyboru wariantu (wymiary: Zgodnosc, Poprawnosc merytoryczna)
- `planuj` - gdy niezgodnosc dotyczy planu (wymiary: Kompletnosc, Poprawnosc logiczna)

Agent przekazuje `loop_target` w wywolaniu `quality_gate`. Jesli nie przekazuje, serwer wnioskuje na podstawie wymiarow audytu.

## 3. Implementacja w serwerze

`quality_gate.py`:

```python
MAX_GATE_ITERATIONS = 2

def evaluate_gate(run_id: str, audit_status: str,
                  audit_wymiary: dict = {},
                  loop_target: str = "") -> dict:
    manifest = load_manifest(run_id)
    iteration = manifest.iteracja_bramki

    if audit_status == "zgodny":
        return {
            "gate_decision": "przejdz",
            "next_station": get_post_gate_station(manifest.sciezka),
            "iteracja_bramki": iteration
        }

    # niezgodny
    if iteration >= MAX_GATE_ITERATIONS:
        return {
            "gate_decision": "eskylacja",
            "next_station": None,
            "iteracja_bramki": iteration,
            "komunikat": "Osiagnieto max 2 iteracje bramki. Wymagana interwencja uzytkownika."
        }

    # powrot
    target = loop_target or infer_loop_target(audit_wymiary)
    new_iteration = iteration + 1
    update_manifest(run_id, iteracja_bramki=new_iteration)

    return {
        "gate_decision": "powrot",
        "loop_target": target,
        "next_station": target,
        "iteracja_bramki": new_iteration,
        "max_iteracje": MAX_GATE_ITERATIONS,
        "pozostale_iteracje": MAX_GATE_ITERATIONS - new_iteration
    }

def get_post_gate_station(sciezka: str) -> str:
    if sciezka == "pelny":
        return "utrwal"
    elif sciezka == "doglebny":
        return "ewaluacja"
    return "utrwal"  # fallback

def infer_loop_target(wymiary: dict) -> str:
    # Jesli niezgodnosc w Zgodnosc/Poprawnosc merytoryczna -> dobierz
    # Jesli niezgodnosc w Kompletnosc/Poprawnosc logiczna -> planuj
    if wymiary.get("Zgodnosc") == "niezgodny" or \
       wymiary.get("Poprawnosc merytoryczna") == "niezgodny":
        return "dobierz"
    return "planuj"
```

## 4. Checkpointy po iteracji bramki

Po powrocie bramki serwer zapisuje nowy checkpoint z sufiksem `_iter<N>`:

```
.ai-kb/pipeline-runs/<run_id>/
  stan_04_dobierz.yaml          # oryginalny checkpoint
  stan_04_dobierz_iter1.yaml    # checkpoint po 1. iteracji bramki
  stan_06_planuj.yaml           # oryginalny checkpoint planuj
  stan_06_planuj_iter1.yaml     # checkpoint po 1. iteracji bramki
```

## 5. Eskalacja

Po 2 nieudanych iteracjach bramka zwraca `gate_decision: eskylacja`. Serwer:

1. Oznacza run jako `zablokowany` w manifeście
2. Zapisuje checkpoint z sufiksem `_eskalacja`
3. Zwraca komunikat z opisem blokady i wymaganiami dla uzytkownika
4. Auto-pilot (jesli uruchomiony) zostaje zatrzymany

Komunikat eskalacji zawiera:
- ktora iteracja nie przeszla bramki,
- ktore wymiary audytu byly niezgodne,
- do ktorej stacji wracal pipeline,
- czego uzytkownik musi dostarczyz lub zdecydowac.

## 6. Narzedzia MCP

### quality_gate

```python
quality_gate(run_id, audit_status, audit_wymiary={}, loop_target="") -> {
    gate_decision: "przejdz" | "powrot" | "eskylacja",
    iteracja_bramki: int,
    next_station: str | null,
    loop_target: str | null,
    max_iteracje: 2,
    komunikat: str
}
```

### get_gate_iterations

```python
get_gate_iterations(run_id) -> {
    iteracja_aktualna: int,
    max_iteracje: 2,
    historia: [{iteracja, timestamp, audit_status, loop_target, checkpoint}],
    pozostale_iteracje: int
}
```

## 7. Petla bramki w trybie auto-pilot

W trybie auto-pilot serwer obsluguje bramke automatycznie:

1. Po `sprawdzenie` serwer wywoluje `quality_gate` z wynikiem audytu
2. Jesli `powrot` -> serwer wywoluje LLM dla `loop_target` z zaktualizowana koperta
3. Jesli `przejdz` -> serwer kontynuuje do nastepnej stacji
4. Jesli `eskylacja` -> serwer zatrzymuje auto-pilot, zwraca status `zablokowany`

Auto-pilot respektuje `max_gate_iterations` (domyslnie 2).
