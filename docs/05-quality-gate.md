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
- Iteracja 3 -> eskalacja do uzytkownika (run oznaczany jako `zablokowany`)

Przy decyzji `powrot` serwer resetuje w manifescie statusy stacji od celu
powrotu do `sprawdzenie` (na `w_trakcie`), dzieki czemu stacje petli mozna
wykonac ponownie przez `execute_station` bez `skip_validation`. Checkpointy
kolejnych iteracji zapisywane sa z sufiksem `_iter<N>` i nie nadpisuja
checkpointow poprzedniej iteracji.

### 2.3. Wybor celu powrotu

Bramka wraca do:
- `dobierz` - gdy niezgodnosc dotyczy wyboru wariantu (wymiary: Zgodnosc, Poprawnosc merytoryczna)
- `planuj` - gdy niezgodnosc dotyczy planu (wymiary: Kompletnosc, Poprawnosc logiczna)

Agent przekazuje `loop_target` w wywolaniu `quality_gate`. Jesli nie przekazuje, serwer wnioskuje na podstawie wymiarow audytu.

## 3. Implementacja w serwerze

`quality_gate.py`:

```python
MAX_GATE_ITERATIONS = 2

# U7: dozwolone wartosci audit_status
_VALID_AUDIT_STATUSES = ("zgodny", "niezgodny")

def evaluate_gate(
    run_id: str,
    manifest: Manifest,
    audit_status: str,
    audit_wymiary: dict = {},
    loop_target: str = ""
) -> QualityGateResult:
    iteration = manifest.iteracja_bramki

    # U7: walidacja audit_status
    if audit_status not in _VALID_AUDIT_STATUSES:
        raise PipelineError(
            f"Nieprawidlowy audit_status '{audit_status}'. "
            f"Dostepne: {list(_VALID_AUDIT_STATUSES)}"
        )

    if audit_status == "zgodny":
        next_station = get_post_gate_station(manifest.sciezka)
        # U4: zapisz historie iteracji
        manifest.historia_bramki.append(GateHistoryEntry(
            iteracja=iteration, audit_status=audit_status,
            gate_decision="przejdz",
        ))
        return QualityGateResult(
            run_id=run_id, gate_decision="przejdz",
            iteracja_bramki=iteration, next_station=next_station,
            komunikat=f"Bramka zgodna. Przejscie do stacji '{next_station}'."
        )

    # niezgodny
    if iteration >= MAX_GATE_ITERATIONS:
        manifest.status_runu = "zablokowany"
        manifest.historia_bramki.append(GateHistoryEntry(
            iteracja=iteration, audit_status=audit_status,
            gate_decision="eskalacja",
        ))
        return QualityGateResult(
            run_id=run_id, gate_decision="eskalacja",
            iteracja_bramki=iteration, next_station=None,
            komunikat="Osiagnieto max 2 iteracje bramki. Wymagana interwencja uzytkownika."
        )

    # powrot
    target = loop_target or infer_loop_target(audit_wymiary, manifest.sciezka)
    if not is_station_in_path(target, manifest.sciezka):
        target = infer_loop_target(audit_wymiary, manifest.sciezka)
    new_iteration = iteration + 1
    manifest = increment_gate_iteration(manifest)
    manifest = reset_stations_for_loop(manifest, target)
    manifest.historia_bramki.append(GateHistoryEntry(
        iteracja=new_iteration, audit_status=audit_status,
        loop_target=target, gate_decision="powrot",
    ))
    return QualityGateResult(
        run_id=run_id, gate_decision="powrot",
        iteracja_bramki=new_iteration, next_station=target,
        loop_target=target, max_iteracje=MAX_GATE_ITERATIONS,
        komunikat=f"Bramka niezgodna (iteracja {new_iteration}/{MAX_GATE_ITERATIONS}). Powrot do stacji '{target}'."
    )

def reset_stations_for_loop(manifest: Manifest, loop_target: str) -> Manifest:
    """Resetuje statusy stacji od loop_target do konca sciezki na 'w_trakcie'."""
    sequence = get_station_sequence(manifest.sciezka)
    if loop_target not in sequence:
        return manifest
    to_reset = set(sequence[sequence.index(loop_target):])
    for s in manifest.stacje:
        if s.stacja in to_reset and s.status == "zakonczona":
            s.status = "w_trakcie"
    return manifest

def get_post_gate_station(sciezka: str) -> str | None:
    if sciezka == "pelny":
        return "utrwal"
    elif sciezka == "doglebny":
        return "ewaluacja"
    return None  # szybki: sprawdzenie konczy sciezke

def infer_loop_target(wymiary: dict, sciezka: str = "pelny") -> str:
    # Jesli niezgodnosc w Zgodnosc/Poprawnosc merytoryczna -> dobierz
    # Jesli niezgodnosc w Kompletnosc/Poprawnosc logiczna -> planuj
    if wymiary.get("Zgodnosc") == "niezgodny" or \
       wymiary.get("Poprawnosc merytoryczna") == "niezgodny":
        return "dobierz"
    # Sciezka szybka nie zawiera 'planuj' - jedynym celem petli jest 'dobierz'
    if not is_station_in_path("planuj", sciezka):
        return "dobierz"
    return "planuj"
```

## 4. Checkpointy po iteracji bramki

Po powrocie bramki serwer zapisuje nowy checkpoint z sufiksem `_iter<N>`:

```
.ai-kb/clients/<client_id>/pipeline-runs/<run_id>/   (tryb legacy bez client_id: .ai-kb/pipeline-runs/<run_id>/)
  stan_dobierz.yaml          # oryginalny checkpoint
  stan_dobierz_iter1.yaml    # checkpoint po 1. iteracji bramki
  stan_planuj.yaml           # oryginalny checkpoint planuj
  stan_planuj_iter1.yaml     # checkpoint po 1. iteracji bramki
```

## 5. Eskalacja

Po 2 nieudanych iteracjach bramka zwraca `gate_decision: eskalacja`. Serwer:

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
    gate_decision: "przejdz" | "powrot" | "eskalacja",
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
    run_id: str,
    iteracja_aktualna: int,
    max_iteracje: 2,
    pozostale_iteracje: int,
    historia: [{iteracja, timestamp, audit_status, loop_target, gate_decision}]
}
```

## 7. Petla bramki w trybie auto-pilot

W trybie auto-pilot serwer obsluguje bramke automatycznie:

1. Po `sprawdzenie` serwer wywoluje `quality_gate` z wynikiem audytu
2. Jesli `powrot` -> serwer wywoluje LLM dla `loop_target` z zaktualizowana koperta
3. Jesli `przejdz` -> serwer kontynuuje do nastepnej stacji
4. Jesli `eskalacja` -> serwer zatrzymuje auto-pilot, zwraca status `zablokowany`

Auto-pilot respektuje `max_gate_iterations` (domyslnie 2).
