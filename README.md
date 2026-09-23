# Pipeline MCP Server

Samodzielny serwer MCP orkiestrujacy dzialanie agentow AI w petli pipeline. Serwer jest w pelni self-contained - zawiera wbudowane skille wszystkich 13 stacji, kontrakty I/O i specyfikacje pipeline'u. Nie zalezy od zewnetrznych katalogow skilli.

## Cel

Zmaterializowanie pipeline'u umiejetnosci (13 stacji pipeline: inicjuj, zmienne, analiza, dekompozycja, dobierz, routing, planuj, realizuj, weryfikacja, sprawdzenie, ewaluacja, utrwal, monitoruj; dodatkowo stacja `audyt_runu` do weryfikacji ex-post) jako infrastruktury operacyjnej z:

- trwalym stanem run'u (koperta YAML + checkpointy),
- walidacja kontraktow I/O miedzy stacjami,
- bramka jakosci z max 2 iteracjami i eskalacja,
- 3 sciezkami routing'u (szybki, pelny, doglebny),
- restartowalnoscia od dowolnej stacji,
- audytowalnoscia przez Memgraph,
- opcjonalnym trybem auto-pilot (serwer wywoluje LLM per stacja).

## Architektura w skrocie

```
[Agent AI] <--MCP--> [Pipeline MCP Server]
                         |
           +-------------+-------------+
           |             |             |
     [Zarzadzanie    [Koperta +    [Bramka
      run'em]        checkpointy]  jakosci]
           |             |             |
           +-------------+-------------+
                         |
                    [Persystencja]
                    .ai-kb/clients/<client_id>/pipeline-runs/
                    (legacy: .ai-kb/pipeline-runs/)
                         |
              +----------+----------+
              |                     |
         [Pliki YAML]          [Memgraph MCP]
         (manifest +            (graf relacji)
          checkpointy)
```

Serwer wystawia narzedzia MCP podzielone na 11 grup:

1. **Run management** - `start_run`, `get_run_status`, `list_runs`, `resume_run`, `close_run`
2. **Station execution** - `execute_station`, `get_next_station`, `skip_station`, `get_station_contract`
3. **Envelope management** - `get_envelope`, `update_envelope`, `validate_contract`
4. **Quality gate** - `quality_gate`, `get_gate_iterations`
5. **Checkpointing** - `save_checkpoint_tool`, `load_checkpoint_tool`, `list_checkpoints_tool`
6. **Auto-pilot** - `auto_pilot_start`, `auto_pilot_status`, `auto_pilot_stop`
7. **RTM (Requirements Traceability Matrix)** - `get_rtm`, `update_rtm`, `add_rtm_entry`, `validate_rtm_coverage`
8. **Zarzadzanie klientami (multi-tenant)** - `register_client`, `resolve_client`, `set_active_client`, `get_active_client`, `get_client_info`, `list_clients`, `update_client`, `archive_client`, `delete_client`
9. **Wiedza wspoldzielona** - `save_shared_knowledge`, `get_shared_knowledge`, `search_shared_knowledge`, `list_shared_knowledge`
10. **Pamiec AI per-klient** - `save_client_memory`, `get_client_memory`, `list_client_memories`, `save_shared_memory`, `get_shared_memory`, `search_client_memories`
11. **RAG per-klient** - `index_client_document`, `search_client_rag`, `search_shared_rag`, `list_rag_documents`

Dodatkowo narzedzia pomocnicze: `list_stations`, `verify_integrity`.

Szczegolowy opis narzedzi: `docs/02-tools-reference.md`.

## Dwa tryby pracy

### Tryb manual (domyślny)

Agent AI steruje wykonaniem. Serwer zaradza stanem, waliduje kontrakty, prowadzi przez stacje zwracajac `next_station`, ale nie wywoluje LLM. Agent wywoluje skille (prompty) samodzielnie i zwraca wynik przez `execute_station`.

```python
# Agent wywoluje:
run = start_run(zamiar="Wdroz Filament 5.6.7", kontekst="BIP/Wymagania")
# -> run_id, first_station="inicjuj"

# Agent wykonuje skilla inicjuj, zwraca wynik:
execute_station(run_id, station="inicjuj", output={...})
# -> next_station="zmienne", envelope_updated

# Agent wykonuje skilla zmienne...
execute_station(run_id, station="zmienne", output={...})
# -> next_station="analiza"
# ... itd.
```

### Tryb auto-pilot (opcjonalny)

Serwer sam wywoluje LLM per stacja z odpowiednim promptem skilla. Agent inicjuje i monitoruje. Obslugiwani dostawcy: `openai`, `anthropic`, `local` (Ollama lub endpoint zgodny z OpenAI API - patrz `PIPELINE_LLM_PROVIDER`).

```python
auto_pilot_start(run_id, from_station="inicjuj")
# Serwer sekwencyjnie wywoluje LLM dla kazdej stacji,
# zapisuje checkpointy, obsluguje bramke jakosci.
# Agent moze sprawdzac status:
auto_pilot_status(run_id)
# Lub zatrzymac:
auto_pilot_stop(run_id)
```

Szczegoly: `docs/07-auto-pilot.md`.

## Samodzielnosc

Serwer jest w pelni self-contained:

- **Skille wbudowane** - wszystkie 13 stacji (prompty SKILL.md) wbudowane w pakiet, w `src/pipeline_mcp/skills/`. Nie czytane z `/etc/windsurf/skills/`.
- **Kontrakty wbudowane** - mapowania I/O miedzy stacjami wbudowane w kod (`contracts.py`), nie czytane z zewnetrznego `kontrakty_pipelines.md`.
- **Specyfikacja wbudowana** - definicje sciezek, bramki, checkpointow wbudowane w kod, nie czytane z zewnetrznego `pipeline_sklills.md`.
- **Brak zaleznosci plikowych** - serwer mozna uruchomic na dowolnej maszynie z Python 3.11+ bez kopiowania katalogow skilli.
- **Lokalne dzialanie** - serwer uruchamiany lokalnie przez `uvx` lub `python -m`, agent (Devin/Windsurf w VSCode) laczy sie przez stdio.

Pliki zrodlowe skilli w `src/pipeline_mcp/skills/` sa kopia oryginalow z `/etc/windsurf/skills/` i stanowia czesc pakietu. Aktualizacja skilli wymaga aktualizacji pakietu serwera.

## Instalacja

### Wymagania

- Python >= 3.11
- uvx (dostepne w systemie)
- Opcjonalnie: Memgraph dla warstwy grafowej

### Konfiguracja w Devin (lokalnie w VSCode)

Dodaj do `~/.config/devin/mcp_config.json`:

```json
{
  "mcpServers": {
    "pipeline": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/rskonieczka/MCP_Pipline",
        "pipeline-mcp"
      ],
      "env": {
        "PIPELINE_RUNS_DIR": "${HOME}/Projekty/EVILLAGE/AI_MCP/Pipline/.ai-kb/pipeline-runs",
        "PIPELINE_AUTO_PILOT": "false",
        "PIPELINE_LLM_PROVIDER": "openai",
        "PIPELINE_LLM_MODEL": "gpt-4o",
        "MEMGRAPH_URL": "bolt://localhost:7687"
      }
    }
  }
}
```

Alternatywnie, uruchomienie lokalne z katalogu projektu (development):

```json
{
  "mcpServers": {
    "pipeline": {
      "command": "python",
      "args": ["-m", "pipeline_mcp"],
      "cwd": "/home/swami/Projekty/EVILLAGE/AI_MCP/Pipline",
      "env": {
        "PIPELINE_RUNS_DIR": "./.ai-kb/pipeline-runs",
        "PIPELINE_AUTO_PILOT": "false"
      }
    }
  }
}
```

Szczegoly konfiguracji: `docs/09-configuration.md`.

## Prompty MCP

Oprocz narzedzi serwer wystawia dwa prompty ulatwiajace start pracy agenta:

- `pipeline_start(zamiar, kontekst, zrodla, workspace, client_id)` - rozpoczyna nowy run (wywoluje `start_run`) i zwraca instrukcje do pierwszej stacji,
- `pipeline_continue(run_id, workspace, client_id)` - wznawia istniejacy run i zwraca kontekst wraz z nastepna stacja.

## Wieloklientowosc (multi-tenant)

Runy, pamiec AI, RAG i wiedza moga byc izolowane per klient:

- `register_client` / `resolve_client` / `set_active_client` - rejestracja i aktywacja klienta,
- runy klienta zapisywane w `.ai-kb/clients/<client_id>/pipeline-runs/`,
- bez aktywnego klienta serwer dziala w trybie legacy (`.ai-kb/pipeline-runs/`).

## Szybki start

1. Utworz run: `start_run(zamiar="Twoj cel")` (lub prompt `pipeline_start`)
2. Sprawdz pierwsza stacje: `get_next_station(run_id)`
3. Wykonaj stacje (manual) lub uruchom auto-pilot
4. Po `sprawdzenie` sprawdz bramke jakosci: `quality_gate(run_id, audit_status)`
5. Kontynuuj do zamkniecia: `close_run(run_id)`

## Development

```bash
# Instalacja developerska (z zaleznosciami testowymi)
pip install -e ".[dev]"

# Testy
pytest
```

## Dokumentacja

| Plik | Temat |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | Architektura, komponenty, przeplyw danych |
| [docs/02-tools-reference.md](docs/02-tools-reference.md) | Referencja wszystkich narzedzi MCP |
| [docs/03-envelope-spec.md](docs/03-envelope-spec.md) | Specyfikacja koperty (YAML envelope) |
| [docs/04-paths-and-routing.md](docs/04-paths-and-routing.md) | Sciezki pipeline'u i routing |
| [docs/05-quality-gate.md](docs/05-quality-gate.md) | Bramka jakosci i petla zwrotna |
| [docs/06-checkpointing.md](docs/06-checkpointing.md) | Mechanizm checkpointow i restart |
| [docs/07-auto-pilot.md](docs/07-auto-pilot.md) | Tryb auto-pilot z LLM |
| [docs/08-memgraph-integration.md](docs/08-memgraph-integration.md) | Integracja z Memgraph |
| [docs/09-configuration.md](docs/09-configuration.md) | Konfiguracja i instalacja |
| [docs/10-stations-builtin.md](docs/10-stations-builtin.md) | Wbudowane skille stacji |

## Zrodla prawdy (wbudowane)

Serwer zawiera wbudowane kopie nastepujacych plikow w `src/pipeline_mcp/skills/`:

- `pipeline_sklills.md` - specyfikacja pipeline'u umiejetnosci
- `kontrakty_pipelines.md` - kontrakty I/O miedzy stacjami
- `<stacja>/SKILL.md` - specyfikacja kazdej z 13 stacji
- `_shared/zrodla-i-narzedzia.md` - wspoldzielone zasady zrodel
- `_shared/graf-pipeline.md` - schemat grafu Memgraph

Pliki te sa kopia oryginalow z `/etc/windsurf/skills/` i stanowia czesc pakietu. Serwer nie odczytuje skilli z systemu - wszystkie sa wbudowane.

## Licencja

MIT (zgodnie z `pyproject.toml`). Autor: EVILLAGE.
