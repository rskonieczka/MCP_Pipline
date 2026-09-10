# Referencja narzedzi MCP

Serwer wystawia ~49 narzedzi MCP podzielonych na 11 grup oraz 2 narzedzia pomocnicze. Wszystkie narzedzia przyjmuja i zwracaja struktury JSON zgodne z modelem Pydantic.

**Parametr `client_id`**: Wszystkie narzedzia zarzadzania run'ami, checkpointami, manifestami, RTM i pamiecia przyjmuja opcjonalny `client_id`. Hierarchia rozwiazywania: jawny parametr -> aktywny klient sesji (`set_active_client`) -> `PIPELINE_DEFAULT_CLIENT_ID` -> tryb legacy (`""`). Narzedzia wieloklientowe (grupy 8-11) zawsze wymagaja `client_id` (oprocz wiedzy i RAG wspoldzielonego).

**Parametr `workspace`**: Wszystkie narzedzia przyjmuja opcjonalny `workspace`. Jesli pusty, serwer uzywa autodetekcji z polozenia pakietu (`_detect_workspace()` w `config.py`) lub `os.getcwd()`.

## 1. Run management

### 1.1. start_run

Tworzy nowy run pipeline'u. Generuje `run_id`, tworzy katalog `.ai-kb/clients/<client_id>/pipeline-runs/<run_id>/` (tryb legacy bez `client_id`: `.ai-kb/pipeline-runs/<run_id>/`), inicjalizuje `manifest.yaml` i pusta koperte. Gdy `client_id` niepuste, wymaga istnienia klienta w rejestrze.

```python
start_run(
    zamiar: str,           # wymagany: zamiar uzytkownika
    kontekst: str = "",    # opcjonalny: kontekst zadania
    zrodla: list[str] = [],# opcjonalne: zrodla bazowe
    tryb_inicjacji: str = "pelny",  # "szybki" | "pelny"
    workspace: str = "",   # opcjonalny: sciezka workspace'a
    client_id: str = ""    # opcjonalny: identyfikator klienta
) -> {
    run_id: str,
    first_station: str,    # zawsze "inicjuj"
    manifest_path: str,
    client_id: str,        # rozwiazany client_id (pusty = legacy)
    wejscie: dict,         # {kontekst, zrodla, tryb_inicjacji}
    envelope: dict         # pusta koperta
}
```

### 1.2. get_run_status

Zwraca status run'u na podstawie manifestu.

```python
get_run_status(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    zamiar: str,
    sciezka: str,          # "szybki" | "pelny" | "doglebny"
    iteracja_bramki: int,
    status_runu: str,      # "w_trakcie" | "zakonczony" | "zablokowany"
    stacja_aktualna: str,
    stacje: [
        {stacja, status, timestamp, checkpoint}
    ],
    timestamp_start: str,
    timestamp_end: str | null,
    client_id: str
}
```

### 1.3. list_runs

Lista wszystkich run'ow w katalogu persystencji. Gdy `client_id` podany, zwraca tylko run'y tego klienta.

```python
list_runs(
    status_filter: str = "",  # "" | "w_trakcie" | "zakonczony" | "zablokowany"
    limit: int = 50,
    workspace: str = "",
    client_id: str = ""
) -> [
    {run_id, zamiar, sciezka, status, stacja_aktualna, timestamp_start, client_id}
]
```

### 1.4. resume_run

Wznawia run od ostatniej zakonczonej stacji. Odczytuje manifest, identyfikuje ostatni checkpoint, zwraca nastepna stacje.

```python
resume_run(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    stacja_wznowienia: str,
    envelope: dict,        # zaladowana z ostatniego checkpointu
    walidacja: dict | null # czy wejscie stacji wznowienia jest kompletne
}
```

### 1.5. close_run

Zamyka run. Zapisuje ostateczna koperte, oznacza run jako zakonczony w manifeście, zapisuje wezel Run do Memgraph.

```python
close_run(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    status: "zakonczony",
    envelope_final_path: str,
    stacje_wykonane: int,
    iteracje_bramki: int,
    already_closed: bool   # True jesli run byl juz zakonczony
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
    skip_validation: bool = False,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    station: str,
    status: "zakonczona" | "zablokowana",
    next_station: str | null,
    envelope_summary: dict,  # skrot zaktualizowanej koperty
    validation: dict | null, # null gdy brak nastepnej stacji
    checkpoint_path: str,
    memgraph_written: bool
}
```

### 2.2. get_next_station

Zwraca nastepna stacje na podstawie aktualnego stanu run'u, sciezki i statusu bramki. Nie wykonuje stacji.

```python
get_next_station(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
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
    reason: str = "",
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    station: str,
    status: "pominieta",
    reason: str,
    next_station: str | null
}
```

### 2.4. get_station_contract

Zwraca kontrakt I/O dla stacji: wymagane i opcjonalne pola wejsciowe, pola wyjsciowe, mappowanie z stacji poprzedniej.

```python
get_station_contract(
    run_id: str,
    station: str,
    workspace: str = "",
    client_id: str = ""
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
get_envelope(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    sciezka: str,
    stacja_aktualna: str,
    stacja_poprzednia: str | null,
    stan: dict,
    pola_stacji: dict,
    walidacja: dict,
    relacje: list[dict],
    rtm: list[dict],
    wejscie: dict,
    client_id: str,
    timestamp: str
}
```

### 3.2. update_envelope

Ręczna aktualizacja koperty (tryb hybrydowy). Pozwala agentowi nadpisac konkretne pola bez wykonywania pelnej stacji.

```python
update_envelope(
    run_id: str,
    section: str,          # "stan" | "pola_stacji.<stacja>" | "walidacja" | "relacje" | "rtm"
    fields: dict,          # pola do aktualizacji
    merge: bool = True,    # True = scal z istniejacymi, False = zastap
    workspace: str = "",
    client_id: str = ""
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
    target_station: str,
    workspace: str = "",
    client_id: str = ""
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

Ocenia bramke jakosci po stacji `sprawdzenie`. Decyduje o przejsciu do `ewaluacja`/`utrwal` lub powrocie do `dobierz`/`planuj`. Waliduje `audit_status` (musi byc `"zgodny"` lub `"niezgodny"`).

```python
quality_gate(
    run_id: str,
    audit_status: str,     # "zgodny" | "niezgodny" (walidowane)
    audit_wymiary: dict = {},  # opcjonalne: wymiary audytu
    loop_target: str = "", # opcjonalne: "dobierz" | "planuj" (gdzie wrocic)
    workspace: str = "",
    client_id: str = ""
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
get_gate_iterations(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    iteracja_aktualna: int,
    max_iteracje: 2,
    pozostale_iteracje: int,
    historia: [
        {iteracja, timestamp, audit_status, loop_target, gate_decision}
    ]
}
```

## 5. Checkpointing

### 5.1. save_checkpoint_tool

Ręczny zapis checkpointu (normalnie wywolywane automatycznie przez `execute_station`).

```python
save_checkpoint_tool(
    run_id: str,
    station: str,
    envelope: dict,
    suffix: str = "",      # np. "_iter1" dla checkpointow po iteracji bramki
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    station: str,
    checkpoint_path: str,
    timestamp: str
}
```

### 5.2. load_checkpoint_tool

Odczyt checkpointu stacji.

```python
load_checkpoint_tool(
    run_id: str,
    station: str,
    suffix: str = "",
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    station: str,
    envelope: dict,
    timestamp: str
}
```

### 5.3. list_checkpoints_tool

Lista wszystkich checkpointow dla run'u.

```python
list_checkpoints_tool(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> [
    {station, checkpoint_path, timestamp, suffix, size_bytes}
]
```

## 6. Auto-pilot

### 6.1. auto_pilot_start

Uruchamia tryb auto-pilot. Serwer synchronicznie wywoluje LLM dla kazdej stacji, zapisuje checkpointy, obsluguje bramke jakosci. Limit 40 krokow (`_AUTO_PILOT_MAX_STEPS`).

```python
auto_pilot_start(
    run_id: str,
    from_station: str = "",  # puste = od nastepnej stacji
    to_station: str = "",    # puste = do konca pipeline'u
    max_gate_iterations: int = 2,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    status: "uruchomiony" | "zakonczony" | "zatrzymany" | "zablokowany",
    stacje_wykonane: list[str],
    bledy: list[str],
    iteracja_bramki: int
}
```

### 6.2. auto_pilot_status

Zwraca status wykonania auto-pilota.

```python
auto_pilot_status(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    status: "uruchomiony" | "zakonczony" | "zatrzymany" | "zablokowany",
    stacja_aktualna: str,
    stacje_wykonane: list[str],
    stacje_pozostale: list[str],
    iteracja_bramki: int,
    bledy: list[str],
    ostatni_llm_koszt: dict | null,  # {tokens_wejscie, tokens_wyjscie, koszt_usd, model}
    laczny_koszt: dict | null        # {tokens_wejscie, tokens_wyjscie, koszt_usd}
}
```

### 6.3. auto_pilot_stop

Zatrzymuje auto-pilot. Zapisuje stan, pozwala na reczna kontynuacje.

```python
auto_pilot_stop(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    status: "zatrzymany",
    stacja_zatrzymania: str
}
```

## 7. Requirements Traceability Matrix (RTM)

### 7.1. get_rtm

Zwraca macierz Requirements Traceability Matrix dla run'u. RTM mapuje wymagania uzytkownika na stacje adresujace, weryfikujace i artefakty.

```python
get_rtm(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    rtm: [
        {req_id, opis, zrodlo, stacje_adresujace, stacja_weryfikujaca,
         stacja_niespelnienia, status, artefakty, checkpoint_weryfikacji}
    ],
    coverage: {
        total, nieadresowane, adresowane, zrealizowane, weryfikowane, niespelnione,
        pokrycie_procent, nieadresowane_ids, niespelnione_ids, status
    }
}
```

### 7.2. update_rtm

Reczna aktualizacja wpisu RTM. Pozwala agentowi nadpisac status wymagania, dodac stacje adresujace lub artefakty.

```python
update_rtm(
    run_id: str,
    req_id: str,          # identyfikator wymagania
    updates: dict,        # pola do aktualizacji (status, stacje_adresujace, artefakty, ...)
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    entry: dict,           # zaktualizowany wpis
    coverage: dict         # raport pokrycia
}
```

### 7.3. add_rtm_entry

Dodaje nowy wpis do RTM. Uzyj gdy wymaganie nie zostalo automatycznie wyekstrahowane przez stacje zmienne.

```python
add_rtm_entry(
    run_id: str,
    req_id: str,                      # identyfikator wymagania
    opis: str,                        # opis wymagania
    zrodlo: str = "zamiar",           # zrodlo ("zamiar", "kontekst", "zrodla", "agent_inference")
    stacje_adresujace: list = [],     # stacje adresujace
    status: str = "nieadresowane",    # status poczatkowy
    workspace: str = "",
    client_id: str = ""
) -> {
    run_id: str,
    entry: dict,                      # dodany wpis
    coverage: dict                    # raport pokrycia
}
```

### 7.4. validate_rtm_coverage

Waliduje pokrycie wymagan w RTM. Zwraca raport z lista nieadresowanych i niespelnionych wymagan.

```python
validate_rtm_coverage(
    run_id: str,
    workspace: str = "",
    client_id: str = ""
) -> {
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
| `LLM_OUTPUT_PARSE_ERROR` | Wyjscie LLM nie zawiera bloku KOPERTA (auto-pilot) |
| `INVALID_PATH` | Sciezka pipeline'u niezgodna z definicja |
| `RUN_CLOSED` | Run zakonczony, nie mozna wykonywac operacji |
| `SKILL_NOT_FOUND` | Plik skilla nie istnieje w wbudowanym katalogu pakietu |
| `CLIENT_NOT_FOUND` | Klient o podanym `client_id` nie istnieje w rejestrze |
| `CLIENT_ALREADY_EXISTS` | Klient o podanym `client_id` juz zarejestrowany |
| `AMBIGUOUS_CLIENT` | Zapytanie dopasowuje wiecej niz jednego klienta |
| `CLIENT_ID_MISMATCH` | Run nalezy do innego klienta niz podany w wywolaniu |
| `INVALID_CLIENT_ID` | `client_id` niezgodny z regex `^[a-z0-9][a-z0-9-]*[a-z0-9]$` |

## 8. Zarzadzanie klientami (multi-tenant)

### 8.1. register_client

Rejestruje nowego klienta w `<workspace>/.ai-kb/clients/<client_id>/context.yaml`.

```python
register_client(
    client_id: str,            # wymagany: slug (regex ^[a-z0-9][a-z0-9-]*[a-z0-9]$)
    display_name: str,         # wymagany: nazwa wyswietlana
    aliases: list[str] = [],   # opcjonalne: aliasy dla dopasowania (skroty, literowki)
    external_ids: dict = {},   # opcjonalne: {"nip": "...", "phone": "...", "krs": "..."}
    id_fragments: list = [],   # opcjonalne: fragmenty ID (np. ostatnie 4 cyfry NIP)
    metadata: dict = {},       # opcjonalne: metadane (branza, osoba kontaktowa)
    workspace: str = ""
) -> { client_id, display_name, status, registered, aliases, external_ids, id_fragments, metadata }
```

### 8.2. resolve_client

Rozpoznaje klienta na podstawie niejednoznacznego identyfikatora. Przeszukuje rejestr: client_id, aliasy, external_ids (NIP, telefon, KRS), id_fragments. Zwraca liste kandydatow z poziomem pewnosci.

```python
resolve_client(
    query: str,              # wymagany: tekst do dopasowania (nazwa, alias, NIP, telefon, fragment)
    workspace: str = ""
) -> {
    query: str,
    normalized: str,
    matches: [
        {client_id, display_name, confidence, matched_on}
    ],
    auto_resolved: bool,     # True przy 100% pewnosci
    needs_confirmation: bool, # True ponizej 100%
    suggested_action: str
}
```

### 8.3. set_active_client / get_active_client

Ustawia/pobiera aktywnego klienta dla sesji procesu MCP.

```python
set_active_client(
    client_id: str,
    workspace: str = ""
) -> { client_id, display_name, status: "aktywny" }

get_active_client() -> { client_id: str, is_set: bool }
```

### 8.4. get_client_info / list_clients

```python
get_client_info(
    client_id: str,
    workspace: str = ""
) -> { client_id, display_name, status, registered, aliases, external_ids, id_fragments, metadata }

list_clients(
    workspace: str = ""
) -> [{ client_id, display_name, status, aliases_count, external_ids_count }]
```

### 8.5. update_client / archive_client / delete_client

```python
update_client(
    client_id: str,
    updates: dict,        # pola do aktualizacji (aliases, external_ids, id_fragments, metadata, status)
    workspace: str = ""
) -> { client_id, display_name, status, ... }

archive_client(
    client_id: str,
    workspace: str = ""
) -> { client_id, display_name, status: "zarchiwizowany" }

delete_client(
    client_id: str,
    workspace: str = ""
) -> { client_id, deleted: True, runs_deleted: int, rag_deleted: bool, memory_deleted: bool, memgraph_deleted: bool }
```

`delete_client` usuwa pliki (`shutil.rmtree`) i wezly Memgraph (`delete_client_nodes` - GDPR).

## 9. Wiedza wspoldzielona

### 9.1. save_shared_knowledge

Zapisuje wpis wiedzy w kategorii `decision`, `pattern` lub `pitfall`.

```python
save_shared_knowledge(
    knowledge_id: str,     # wymagany: identyfikator wpisu (slug)
    category: str,         # "decision" | "pattern" | "pitfall"
    title: str,            # wymagany
    content: str,          # wymagany
    source: str = "",      # opcjonalny: zrodlo wiedzy
    tags: list[str] = [],  # opcjonalne: tagi
    workspace: str = ""
) -> { knowledge_id, category, title, content, source, timestamp, tags }
```

### 9.2. get_shared_knowledge / search_shared_knowledge / list_shared_knowledge

```python
get_shared_knowledge(
    knowledge_id: str,
    category: str,         # wymagany: "decision" | "pattern" | "pitfall"
    workspace: str = ""
) -> { knowledge_id, category, title, content, source, timestamp, tags }

search_shared_knowledge(
    query: str,
    category: str = "",
    workspace: str = ""
) -> [{ knowledge_id, category, title, content, ... }]

list_shared_knowledge(
    category: str = "",
    workspace: str = ""
) -> [{ knowledge_id, category, title, ... }]
```

## 10. Pamiec AI per-klient

### 10.1. save_client_memory

Zapisuje wpis pamieci AI dla klienta. Auto-generowany `memory_id` jest unikalny przy kolizji tematu (dodatek timestamp).

```python
save_client_memory(
    topic: str,              # wymagany
    content: str,            # wymagany
    client_id: str = "",     # opcjonalny (hierarchia rozwiazywania)
    memory_id: str = "",     # opcjonalny (jawny = upsert)
    tags: list[str] = [],    # opcjonalne
    workspace: str = ""
) -> { memory_id, topic, content, scope: "client", client_id, timestamp, tags }
```

### 10.2. save_shared_memory / get_shared_memory

Zapisuje/odczytuje wpis pamieci wspoldzielonej (cross-client).

```python
save_shared_memory(
    topic: str,
    content: str,
    memory_id: str = "",
    tags: list[str] = [],
    workspace: str = ""
) -> { memory_id, topic, content, scope: "shared", timestamp, tags }

get_shared_memory(
    memory_id: str,
    workspace: str = ""
) -> { memory_id, topic, content, scope: "shared", timestamp, tags }
```

### 10.3. get_client_memory / list_client_memories / search_client_memories

```python
get_client_memory(
    memory_id: str,
    client_id: str = "",
    workspace: str = ""
) -> { memory_id, topic, content, scope, client_id, timestamp, tags }

list_client_memories(
    client_id: str = "",
    workspace: str = ""
) -> [{ memory_id, topic, content, scope, client_id, timestamp, tags }]

search_client_memories(
    query: str,
    client_id: str = "",
    include_shared: bool = True,
    workspace: str = ""
) -> [{ memory_id, topic, scope, client_id, timestamp, tags }]
```

## 11. RAG per-klient

### 11.1. index_client_document

Indeksuje dokument w RAG klienta (indeks keyword-based, atomowy zapis). Gdy `client_id` puste, indeksuje w RAG wspoldzielonym.

```python
index_client_document(
    doc_id: str,             # wymagany
    content: str,            # wymagany
    title: str = "",         # opcjonalny: tytul dokumentu
    metadata: dict = {},     # opcjonalne: metadane dokumentu
    client_id: str = "",     # opcjonalny (pusty = RAG wspoldzielony)
    workspace: str = ""
) -> { doc_id, indexed: True }
```

### 11.2. search_client_rag / search_shared_rag / list_rag_documents

```python
search_client_rag(
    query: str,
    client_id: str = "",
    limit: int = 10,
    workspace: str = ""
) -> [{ doc_id, score, snippet }]

search_shared_rag(
    query: str,
    limit: int = 10,
    workspace: str = ""
) -> [{ doc_id, score, snippet }]

list_rag_documents(
    client_id: str = "",
    workspace: str = ""
) -> [{ doc_id, metadata }]
```

## Narzedzia pomocnicze

### list_stations

Lista wszystkich dostepnych stacji pipeline'u.

```python
list_stations() -> list[str]
# ["inicjuj", "zmienne", "analiza", "dekompozycja", "dobierz", "routing",
#  "planuj", "realizuj", "weryfikacja", "sprawdzenie", "ewaluacja",
#  "utrwal", "monitoruj", "audyt_runu"]
```

### verify_integrity

Weryfikuje integralnosc wbudowanych skilli. Zwraca liste bledow.

```python
verify_integrity() -> {
    errors: list[str],
    status: "ok" | "bledy",
    skills_count: int
}
```
