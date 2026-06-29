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

| Wezel | Klucz | Wlasciwosci |
|---|---|---|
| `Run` | run_id | run_id, zamiar, sciezka, status, timestamp_start, timestamp_end |
| `Stacja` | run_id:stacja | run_id, stacja, status, timestamp, checkpoint |
| `Zmienna` | run_id:V001 | run_id, variable_id, name, type, source_type |
| `Decyzja` | run_id:dec001 | run_id, decision_id, opis, stacja_zrodlowa |
| `Podproblem` | run_id:pp001 | run_id, podproblem_id, opis, krytyczne |
| `Twierdzenie` | run_id:t001 | run_id, twierdzenie_id, tresc, stacja_zrodlowa |
| `Werdykt` | run_id:w001 | run_id, werdykt_id, status, twierdzenie_id |
| `Wniosek` | run_id:wn001 | run_id, wniosek_id, tresc, stacja_zrodlowa |
| `KrokPlanu` | run_id:k001 | run_id, krok_id, opis, kolejnosc |
| `Zmiana` | run_id:z001 | run_id, zmiana_id, plik, opis |
| `WymiarAudytu` | run_id:wa001 | run_id, wymiar, ocena, status |
| `Checkpoint` | run_id:cp_NN | run_id, stacja, sciezka, timestamp |

### 3.2. Krawedzie

| Krawedz | Od | Do | Wlasciwosci |
|---|---|---|---|
| `ZAWIERA` | Run | Stacja | - |
| `NASTAPILA_PO` | Stacja | Stacja | iteracja_bramki |
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

## 4. Zapis do Memgraph

Po kazdej stacji serwer zapisuje wezly i krawedzie na podstawie sekcji `relacje` w kopercie.

`memgraph.py`:

```python
from neo4j import GraphDatabase

class MemgraphClient:
    def __init__(self, url: str = "bolt://localhost:7687"):
        self.driver = GraphDatabase.driver(url)

    def write_run_node(self, run_id: str, zamiar: str, sciezka: str):
        with self.driver.session() as session:
            session.run(
                "CREATE (r:Run {run_id: $run_id, zamiar: $zamiar, "
                "sciezka: $sciezka, status: 'w_trakcie', "
                "timestamp_start: datetime()})",
                run_id=run_id, zamiar=zamiar, sciezka=sciezka
            )

    def write_station_node(self, run_id: str, station: str,
                           status: str, checkpoint: str):
        with self.driver.session() as session:
            session.run(
                "CREATE (s:Stacja {run_id: $run_id, stacja: $station, "
                "status: $status, timestamp: datetime(), "
                "checkpoint: $checkpoint})",
                run_id=run_id, station=station,
                status=status, checkpoint=checkpoint
            )

    def write_relation(self, source: str, target: str,
                       rel_type: str, fields: list = None):
        with self.driver.session() as session:
            session.run(
                f"MATCH (a {{id: $source}}), (b {{id: $target}}) "
                f"CREATE (a)-[:{rel_type}]->(b)",
                source=source, target=target
            )

    def write_relations_from_envelope(self, run_id: str, relacje: list):
        for rel in relacje:
            self.write_relation(rel["zrodlo"], rel["cel"],
                               rel["typ"].upper(), rel.get("pola"))

    def validate_graph_continuity(self, run_id: str) -> list:
        """Walidacja ciaglosci grafu - czy stacja biezaca nastapila po stacji zakonczonej."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (s:Stacja {run_id: $run_id}) "
                "WHERE NOT (s)-[:NASTAPILA_PO]->(:Stacja {status: 'zakonczona'}) "
                "AND s.status = 'w_trakcie' "
                "RETURN s.stacja as stacja",
                run_id=run_id
            )
            return [r["stacja"] for r in result]
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
MATCH (s:Stacja {stacja: 'zmienne'})
WHERE NOT (s)-[:NASTAPILA_PO]->(:Stacja {stacja: 'inicjuj'})
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
