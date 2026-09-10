# Integracja z Memgraph

Memgraph stanowi warstwe grafowa uzupełniajaca checkpointy plikowe. Serena memory pozostaje glownym zrodlem wiedzy deklaratywnej (decyzje, preferencje, status), a Memgraph przechowuje relacje miedzy encjami w run'ie pipeline'u.

## 1. Cel integracji

- Audytowalnosc relacyjna - sledzenie pochodzenia decyzji
- Weryfikacja spojnosci run'u - ciaglosc stacji, brak osieroconych wezlow
- Zapytania o zaleznosci - ktore zmienne wplynely na decyzje
- Analiza ex-post przez skilla `audyt_runu`

## 2. Wymagania

- Memgraph uruchomiony lokalnie (`docker compose up -d` w `~/.local/share/memgraph/`)
- Polaczenie bolt://localhost:7687
- Memgraph MCP skonfigurowany w `mcp_config.json`

Memgraph jest opcjonalny. Jesli niedostepny, serwer kontynuuje bez zapisu grafu (ostrzezenie w statusie).

## 3. Schemat grafu

### 3.1. Wezly

| Wezel | Klucz (ID wezla) | Wlasciwosci |
|---|---|---|
| `Run` | `run:<client_id>:<run_id>` (legacy: `run:<run_id>`) | run_id, zamiar, sciezka, status, client_id, timestamp_start, timestamp_end |
| `Stacja` | `stacja:<client_id>:<run_id>:<station>` (legacy: `stacja:<run_id>:<station>`) | run_id, stacja, status, client_id, timestamp, checkpoint |
| `Zmienna` | `zmienna:<run_id>:<id>` | run_id, variable_id, name, type, source_type |
| `Decyzja` | `decyzja:<run_id>:<id>` | run_id, decision_id, opis, stacja_zrodlowa |
| `Podproblem` | `podproblem:<run_id>:<id>` | run_id, podproblem_id, opis, krytyczne |
| `Twierdzenie` | `twierdzenie:<run_id>:<id>` | run_id, twierdzenie_id, tresc, stacja_zrodlowa |
| `Werdykt` | `werdykt:<run_id>:<id>` | run_id, werdykt_id, status, twierdzenie_id |
| `Wniosek` | `wniosek:<run_id>:<id>` | run_id, wniosek_id, tresc, stacja_zrodlowa |
| `KrokPlanu` | `krok:<run_id>:<id>` | run_id, krok_id, opis, kolejnosc |
| `Zmiana` | `zmiana:<run_id>:<id>` | run_id, zmiana_id, plik, opis |
| `WymiarAudytu` | `wymiar:<run_id>:<id>` | run_id, wymiar, ocena, status |
| `Checkpoint` | `checkpoint:<run_id>:<id>` | run_id, stacja, sciezka, timestamp |
| `Wymaganie` | `wymaganie:<client_id>:<run_id>:<req_id>` (legacy: `wymaganie:<run_id>:<req_id>`) | run_id, req_id, opis, status, zrodlo, client_id |
| `Wiedza` | `wiedza:<knowledge_id>` | knowledge_id, category, title, content, client_id="shared" |
| `Pamiec` | `pamiec:<client_id>:<memory_id>` (shared: `pamiec:shared:<memory_id>`) | memory_id, client_id, topic, content, scope |

**Izolacja wieloklientowa**: `client_id` jest wbudowane w ID wezlow `Run`, `Stacja`, `Wymaganie`, `Pamiec` - zapobiega kolizjom miedzy klientami przy tym samym `run_id` lub `memory_id`. Wezly `Wiedza` sa wspoldzielone (`client_id="shared"`). Tryb legacy (brak `client_id`) zachowuje stare konwencje ID dla kompatybilnosci wstecz.

### 3.2. Krawedzie

| Krawedz | Od | Do | Wlasciwosci |
|---|---|---|---|
| `ZAWIERA` | Run | Stacja | - |
| `NASTAPILA_PO` | Stacja (aktualna) | Stacja (poprzednia) | iteracja_bramki |
| `WYPRODUKOWALA` | Stacja | Zmienna/Decyzja/Werdykt/Wniosek | - |
| `ZALEZY_OD` | Zmienna | Zmienna | - |
| `OPARTA_NA` | Decyzja | Zmienna | - |
| `DOTYCZY` | Werdykt | Twierdzenie | - |
| `WYPROWADZONY_Z` | Wniosek | Stacja | - |
| `ROZWIAZUJE` | Podproblem | Podproblem | - |
| `REALIZUJE` | KrokPlanu | Podproblem | - |
| `WERYFIKUJE` | Werdykt | Twierdzenie | - |
| `ZAPISANA_W` | Stacja | Checkpoint | - |
| `KONTYNUACJA` | Run | Run | - |
| `NAPRAWIA` | Run | Run | - |
| `PONOWNE_URUCHOMIENIE` | Run | Run | - |
| `ADRESUJE` | Stacja | Wymaganie | - |
| `WERYFIKUJE` | Stacja | Wymaganie | - |

## 4. Zapis do Memgraph

Po kazdej stacji serwer zapisuje wezly i krawedzie na podstawie sekcji `relacje` w kopercie.

`memgraph.py` (funkcje modulowe, nie klasa - lazy init sterownika):

```python
def _run_node_id(run_id: str, client_id: str = "") -> str:
    """ID wezla Run z izolacja client_id (legacy gdy client_id puste)."""
    return f"run:{client_id}:{run_id}" if client_id else f"run:{run_id}"

def _station_node_id(run_id: str, station: str, client_id: str = "") -> str:
    return f"stacja:{client_id}:{run_id}:{station}" if client_id else f"stacja:{run_id}:{station}"

def _req_node_id(run_id: str, req_id: str, client_id: str = "") -> str:
    return f"wymaganie:{client_id}:{run_id}:{req_id}" if client_id else f"wymaganie:{run_id}:{req_id}"


def write_run_node(run_id: str, zamiar: str, sciezka: str, client_id: str = "") -> bool:
    run_node_id = _run_node_id(run_id, client_id)
    with driver.session() as session:
        session.run(
            "MERGE (r:Run {id: $run_node_id}) "
            "SET r.run_id = $run_id, r.zamiar = $zamiar, "
            "r.sciezka = $sciezka, r.status = 'w_trakcie', "
            "r.client_id = $client_id",
            run_node_id=run_node_id, run_id=run_id,
            zamiar=zamiar, sciezka=sciezka, client_id=client_id,
        )

def write_station_node(run_id: str, station: str, status: str,
                       checkpoint: str = "", client_id: str = "") -> bool:
    station_id = _station_node_id(run_id, station, client_id)
    # ... MERGE + SET z client_id

def close_run_node(run_id: str, timestamp_end: str = "", client_id: str = "") -> bool:
    run_node_id = _run_node_id(run_id, client_id)
    # ... MERGE + SET status='zakonczony'

def write_client_memory_node(memory_id: str, client_id: str, topic: str,
                             content: str, scope: str = "client") -> bool:
    effective_client_id = client_id if scope == "client" else "shared"
    node_id = f"pamiec:{effective_client_id}:{memory_id}"
    # ... MERGE + SET z client_id, topic, content, scope

def write_shared_knowledge_node(knowledge_id: str, category: str,
                                title: str, content: str) -> bool:
    node_id = f"wiedza:{knowledge_id}"
    # ... MERGE + SET z client_id='shared'

def delete_client_nodes(client_id: str) -> bool:
    """GDPR right to be forgotten - usuniecie wezlow klienta z grafu."""
    with driver.session() as session:
        session.run(
            "MATCH (n) WHERE n.client_id = $client_id "
            "AND n.client_id <> 'shared' "
            "DETACH DELETE n",
            client_id=client_id,
        )

def validate_graph_continuity(run_id: str, client_id: str = "") -> list[str]:
    # Filtr po client_id jesli podany
    ...
```

## 5. Walidacja po checkpoincie

Po zapisie checkpointu serwer wykonuje zapytanie Cypher weryfikujace ciaglosc grafu (czy stacja biezaca nastapila po stacji zakonczonej). Naruszenie jest zgłaszane jako anomalia.

## 6. Weryfikacja ex-post (audyt_runu)

Skill `audyt_runu` weryfikuje spojnosc calego run'u przez zapytania Cypher:

- Osierocone wezly (Stacja bez Run)
- Stacje bez poprzednika (brak NASTAPILA_PO)
- Brakujace krawedzie (ZAWIERA)
- Niespojnosc run_id

Przykladowe zapytania:

```cypher
// Osierocone stacje
MATCH (s:Stacja) WHERE NOT (s)<-[:ZAWIERA]-(:Run)
RETURN s.run_id, s.stacja

// Stacje bez poprzednika (oprocz inicjuj)
// Kierunek NASTAPILA_PO: aktualna -> poprzednia
MATCH (s:Stacja {stacja: 'zmienne', run_id: $run_id})
WHERE NOT (s)-[:NASTAPILA_PO]->(:Stacja {stacja: 'inicjuj', run_id: $run_id})
RETURN s.run_id

// Brakujace krawedzie ZAWIERA
MATCH (r:Run), (s:Stacja)
WHERE r.run_id = s.run_id AND NOT (r)-[:ZAWIERA]->(s)
RETURN r.run_id, s.stacja
```

## 7. Relacje miedzy run'ami

Po zakonczeniu run'u serwer zapisuje wezel `Run` jako zakonczony i relacje miedzy runami:

- `KONTYNUACJA` - run B jest kontynuacja run'u A (ten sam cel, kolejna sesja)
- `NAPRAWIA` - run B naprawia run A (po eskalacji bramki)
- `PONOWNE_URUCHOMIENIE` - run B jest ponownym uruchomieniem run'u A (restart)

## 8. Konfiguracja

| Zmienna | Wartosc domyslna | Opis |
|---|---|---|
| `MEMGRAPH_URL` | `bolt://localhost:7687` | URL polaczenia Memgraph |
| `MEMGRAPH_USER` | - | Uzytkownik (pusty dla lokalnego) |
| `MEMGRAPH_PASSWORD` | - | Haslo (puste dla lokalnego) |
| `PIPELINE_MEMGRAPH_ENABLED` | `true` | Czy zapis do Memgraph wlaczony |

Jesli `MEMGRAPH_URL` niedostepny, serwer ustawia `PIPELINE_MEMGRAPH_ENABLED=false` i kontynuuje bez zapisu grafu.
