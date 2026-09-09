# Referencja narzedzi MCP

Serwer wystawia 26 narzedzi MCP podzielonych na 7 grup. Wszystkie narzedzia przyjmuja i zwracaja struktury JSON zgodne z modelem Pydantic.

## 1. Run management

### 1.1. start_run

Tworzy nowy run pipeline'u. Generuje `run_id`, tworzy katalog `.ai-kb/pipeline-runs/<run_id>/`, inicjalizuje `manifest.yaml` i pusta koperte.

```python
start_run(
    zamiar: str,           # wymagany: zamiar uzytkownika
    kontekst: str = "",    # opcjonalny: kontekst zadania
    zrodla: list[str] = [],# opcjonalne: zrodla bazowe
    tryb_inicjacji: str = "pelny"  # "szybki" | "pelny"
) -> {
    run_id: str,
    first_station: str,    # zawsze "inicjuj"
    manifest_path: str,
    envelope: dict         # pusta koperta
}
```

### 1.2. get_run_status

Zwraca status run'u na podstawie manifestu.

```python
get_run_status(run_id: str) -> {
    run_id: str,
    zamiar: str,
    sciezka: str,          # "szybki" | "pelny" | "doglebny" | null
    iteracja_bramki: int,
    stacja_aktualna: str,
    stacja_poprzednia: str | null,
    stacje: [
        {stacja, status, timestamp, checkpoint}
    ],
    status_runu: str       # "w_trakcie" | "zakonczony" | "zablokowany"
}
```

### 1.3. list_runs

Lista wszystkich run'ow w katalogu persystencji.

```python
list_runs(
    status_filter: str = "",  # "" | "w_trakcie" | "zakonczony" | "zablokowany"
    limit: int = 50
) -> [
    {run_id, zamiar, sciezka, status, stacja_aktualna, timestamp}
]
```

### 1.4. resume_run

Wznawia run od ostatniej zakonczonej stacji. Odczytuje manifest, identyfikuje ostatni checkpoint, zwraca nastepna stacje.

```python
resume_run(run_id: str) -> {
    run_id: str,
    stacja_wznowienia: str,
    envelope: dict,        # zaladowana z ostatniego checkpointu
    walidacja: dict        # czy wejscie stacji wznowienia jest kompletne
}
```

### 1.5. close_run

Zamyka run. Zapisuje ostateczna koperte, oznacza run jako zakonczony w manifeście, zapisuje wezel Run do Memgraph.

```python
close_run(run_id: str) -> {
    run_id: str,
    status: "zakonczony",
    envelope_final_path: str,
    stacje_wykonane: int,
    iteracje_bramki: int
}
```

## 2. Station execution

### 2.1. execute_station

Rejestruje wynik wykonania stacji przez agenta (tryb manual). Aktualizuje koperte, zapisuje checkpoint, wyznacza nastepna stacje.

```python
execute_station(
    run_id: str,
    station: str,          # nazwa stacji, np. "inicjuj"
    output: dict,          # wyjscie stacji (pola kontraktu wyjsciowego)
    skip_validation: bool = False
) -> {
    run_id: str,
    station: str,
    status: "zakonczona" | "zablokowana",
    next_station: str | null,
    envelope_summary: dict,  # skrot zaktualizowanej koperty
    validation: {
        stacja_docelowa: str,
        pola_wymagane: list[str],
        pola_obecne: list[str],
        pola_brakujace: list[str],
        status: "gotowy" | "wnioskowane" | "niekompletne",
        akcja_naprawcza: str
    },
    checkpoint_path: str,
    memgraph_written: bool
}
```

### 2.2. get_next_station

Zwraca nastepna stacje na podstawie aktualnego stanu run'u, sciezki i statusu bramki. Nie wykonuje stacji.

```python
get_next_station(run_id: str) -> {
    run_id: str,
    next_station: str | null,
    sciezka: str,
    reason: str,           # dlaczego ta stacja jest nastepna
    gate_iteration: int,
    is_last_station: bool
}
```

### 2.3. skip_station

Ręczne pominiecie stacji (tryb hybrydowy). Oznacza stacje jako `pominieta` w manifeście. Dziala tylko dla stacji opcjonalnych w danej sciezce.

```python
skip_station(
    run_id: str,
    station: str,
    reason: str = ""
) -> {
    run_id: str,
    station: str,
    status: "pominieta",
    next_station: str | null
}
```

### 2.4. get_station_contract

Zwraca kontrakt I/O dla stacji: wymagane i opcjonalne pola wejsciowe, pola wyjsciowe, mappowanie z stacji poprzedniej.

```python
get_station_contract(
    run_id: str,
    station: str
) -> {
    station: str,
    phase: str,
    required_input: list[str],
    optional_input: list[str],
    output: list[str],
    mapping_from_previous: [
        {pole_wyjscia, pole_wejscia, status, uwagi}
    ],
    skill_prompt: str      # wbudowany prompt SKILL.md stacji
}
```

## 3. Envelope management

### 3.1. get_envelope

Zwraca aktualna koperte run'u (z ostatniego checkpointu lub z pamieci).

```python
get_envelope(run_id: str) -> {
    run_id: str,
    sciezka: str,
    stacja_aktualna: str,
    stacja_poprzednia: str | null,
    stan: dict,
    pola_stacji: dict,
    walidacja: dict,
    relacje: list[dict]
}
```

### 3.2. update_envelope

Ręczna aktualizacja koperty (tryb hybrydowy). Pozwala agentowi nadpisac konkretne pola bez wykonywania pelnej stacji.

```python
update_envelope(
    run_id: str,
    section: str,          # "stan" | "pola_stacji.<stacja>" | "walidacja" | "relacje"
    fields: dict,          # pola do aktualizacji
    merge: bool = True     # True = scal z istniejacymi, False = zastap
) -> {
    run_id: str,
    updated_fields: list[str],
    envelope_summary: dict
}
```

### 3.3. validate_contract

Waliduje czy wejscie stacji docelowej jest kompletne na podstawie aktualnej koperty.

```python
validate_contract(
    run_id: str,
    target_station: str
) -> {
    stacja_docelowa: str,
    pola_wymagane: list[str],
    pola_obecne: list[str],
    pola_brakujace: list[str],
    pola_wnioskowane: list[str],
    status: "gotowy" | "wnioskowane" | "niekompletne",
    akcja_naprawcza: str   # "" | "pytanie_do_uzytkownika" | "agent_inference" | "powrot"
}
```

## 4. Quality gate

### 4.1. quality_gate

Ocenia bramke jakosci po stacji `sprawdzenie`. Decyduje o przejsciu do `ewaluacja`/`utrwal` lub powrocie do `dobierz`/`planuj`.

```python
quality_gate(
    run_id: str,
    audit_status: str,     # "zgodny" | "niezgodny"
    audit_wymiary: dict = {},  # opcjonalne: wymiary audytu
    loop_target: str = ""  # opcjonalne: "dobierz" | "planuj" (gdzie wrocic)
) -> {
    run_id: str,
    gate_decision: "przejdz" | "powrot" | "eskalacja",
    iteracja_bramki: int,
    next_station: str | null,
    loop_target: str | null,
    max_iteracje: 2,
    komunikat: str
}
```

### 4.2. get_gate_iterations

Zwraca historie iteracji bramki dla run'u.

```python
get_gate_iterations(run_id: str) -> {
    run_id: str,
    iteracja_aktualna: int,
    max_iteracje: 2,
    historia: [
        {iteracja, timestamp, audit_status, loop_target, checkpoint}
    ],
    pozostale_iteracje: int
}
```

## 5. Checkpointing

### 5.1. save_checkpoint

Ręczny zapis checkpointu (normalnie wywolywane automatycznie przez `execute_station`).

```python
save_checkpoint(
    run_id: str,
    station: str,
    envelope: dict,
    suffix: str = ""       # np. "_iter1" dla checkpointow po iteracji bramki
) -> {
    run_id: str,
    station: str,
    checkpoint_path: str,
    timestamp: str
}
```

### 5.2. load_checkpoint

Odczyt checkpointu stacji.

```python
load_checkpoint(
    run_id: str,
    station: str,
    suffix: str = ""
) -> {
    run_id: str,
    station: str,
    envelope: dict,
    timestamp: str
}
```

### 5.3. list_checkpoints

Lista wszystkich checkpointow dla run'u.

```python
list_checkpoints(run_id: str) -> [
    {station, checkpoint_path, timestamp, suffix, size_bytes}
]
```

## 6. Auto-pilot

### 6.1. auto_pilot_start

Uruchamia tryb auto-pilot. Serwer sekwencyjnie wywoluje LLM dla kazdej stacji, zapisuje checkpointy, obsluguje bramke jakosci.

```python
auto_pilot_start(
    run_id: str,
    from_station: str = "",  # puste = od nastepnej stacji
    to_station: str = "",    # puste = do konca pipeline'u
    max_gate_iterations: int = 2
) -> {
    run_id: str,
    status: "uruchomiony",
    from_station: str,
    to_station: str | null,
    auto_pilot_id: str
}
```

### 6.2. auto_pilot_status

Zwraca status wykonania auto-pilota.

```python
auto_pilot_status(run_id: str) -> {
    run_id: str,
    status: "uruchomiony" | "zakonczony" | "zatrzymany" | "zablokowany",
    stacja_aktualna: str,
    stacje_wykonane: list[str],
    stacje_pozostale: list[str],
    iteracja_bramki: int,
    bledy: list[str],
    ostatni_llm_koszt: dict | null  # tokeny, koszt
}
```

### 6.3. auto_pilot_stop

Zatrzymuje auto-pilot. Zapisuje stan, pozwala na reczna kontynuacje.

```python
auto_pilot_stop(run_id: str) -> {
    run_id: str,
    status: "zatrzymany",
    stacja_zatrzymania: str,
    checkpoint_path: str
}
```

## 6b. Requirements Traceability Matrix (RTM)

### 6b.1. get_rtm

Zwraca macierz Requirements Traceability Matrix dla run'u. RTM mapuje wymagania uzytkownika na stacje adresujace, weryfikujace i artefakty.

```python
get_rtm(run_id: str) -> {
    run_id: str,
    rtm: [
        {req_id, opis, zrodlo, stacje_adresujace, stacja_weryfikujaca, status, artefakty, checkpoint_weryfikacji}
    ],
    coverage: {
        total, nieadresowane, adresowane, zrealizowane, weryfikowane, niespelnione,
        pokrycie_procent, nieadresowane_ids, niespelnione_ids, status
    }
}
```

### 6b.2. update_rtm

Reczna aktualizacja wpisu RTM. Pozwala agentowi nadpisac status wymagania, dodac stacje adresujace lub artefakty.

```python
update_rtm(
    run_id: str,
    req_id: str,          # identyfikator wymagania
    updates: dict         # pola do aktualizacji (status, stacje_adresujace, artefakty, ...)
) -> {
    run_id: str,
    entry: dict,           # zaktualizowany wpis
    coverage: dict        # raport pokrycia
}
```

### 6b.3. add_rtm_entry

Dodaje nowy wpis do RTM. Uzyj gdy wymaganie nie zostalo automatycznie wyekstrahowane przez stacje zmienne.

```python
add_rtm_entry(
    run_id: str,
    req_id: str,                      # identyfikator wymagania
    opis: str,                        # opis wymagania
    zrodlo: str = "zamiar",           # zrodlo ("zamiar", "kontekst", "zrodla", "agent_inference")
    stacje_adresujace: list = [],     # stacje adresujace
    status: str = "nieadresowane"     # status poczatkowy
) -> {
    run_id: str,
    entry: dict,                      # dodany wpis
    coverage: dict                   # raport pokrycia
}
```

### 6b.4. validate_rtm_coverage

Waliduje pokrycie wymagan w RTM. Zwraca raport z lista nieadresowanych i niespelnionych wymagan.

```python
validate_rtm_coverage(run_id: str) -> {
    run_id: str,
    coverage: {
        total: int,
        nieadresowane: int,
        adresowane: int,
        zrealizowane: int,
        weryfikowane: int,
        niespelnione: int,
        pokrycie_procent: float,
        nieadresowane_ids: list[str],
        niespelnione_ids: list[str],
        status: "brak_wymagan" | "w_trakcie" | "kompletne" | "niekompletne"
    }
}
```

## Kody bledow

Wszystkie narzedzia zwracaja bledy przez mechanizm MCP error response:

| Kod | Znaczenie |
|---|---|
| `RUN_NOT_FOUND` | Run o podanym `run_id` nie istnieje |
| `STATION_NOT_FOUND` | Stacja o podanej nazwie nie istnieje |
| `STATION_ALREADY_DONE` | Stacja juz zakonczona, nie mozna wykonac ponownie |
| `CONTRACT_INCOMPLETE` | Wejscie stacji niekompletne, brak wymaganych pol |
| `GATE_MAX_ITERATIONS` | Osiagnieto max 2 iteracje bramki, wymagana eskalacja |
| `CHECKPOINT_NOT_FOUND` | Checkpoint nie istnieje |
| `MEMGRAPH_UNAVAILABLE` | Memgraph niedostepny (opcjonalny, nie blokuje) |
| `LLM_NOT_CONFIGURED` | Tryb auto-pilot wymaga klucza API LLM |
| `INVALID_PATH` | Sciezka pipeline'u niezgodna z definicja |
| `RUN_CLOSED` | Run zakonczony, nie mozna wykonywac operacji |
