# Pipeline MCP Server

Każda praca z agentem AI niesie odrobinę niepewności: raz zadanie wychodzi wzorowo, innym razem ta sama prośba prowadzi w nieznanym kierunku. Gdy korzysta się z takiego wsparcia codziennie, zaczyna brakować jednego: ścieżki, którą agent przejdzie zawsze tak samo, krok po kroku, z możliwością zajrzenia w każde miejsce. Właśnie taką ścieżką jest ten serwer.

Pipeline MCP Server to samodzielny serwer MCP orkiestrujący pracę agentów AI w pętli pipeline'u: od zrozumienia zadania, przez analizę i planowanie, aż po realizację, sprawdzenie efektu i utrwalenie wniosków. MCP (Model Context Protocol) to otwarty standard łączenia modeli językowych z zewnętrznymi narzędziami. Agent rozmawia z serwerem właśnie w tym protokole i widzi go jako zestaw narzędzi, po które może sięgać w trakcie pracy. Serwer jest przy tym w pełni samodzielny: prompty wszystkich stacji, kontrakty między nimi i specyfikacja ścieżek są wbudowane w pakiet, więc nie zależy on od żadnych zewnętrznych katalogów umiejętności.

## Cel

Pipeline umiejętności to sprawdzony sposób prowadzenia pracy: trzynaście stacji ułożonych w spójną trasę, z których każda wie, czego oczekiwać od poprzedniej. Kolejno są to: inicjuj, zmienne, analiza, dekompozycja, dobierz, routing, planuj, realizuj, weryfikacja, sprawdzenie, ewaluacja, utrwal i monitoruj. Obok nich funkcjonuje stacja `audyt_runu`, która po zakończeniu pracy weryfikuje spójność całego uruchomienia. Serwer przekształca tę koncepcję w działającą infrastrukturę z:

- trwałym stanem uruchomienia: kopertą YAML przenoszącą dane między stacjami oraz punktami kontrolnymi, które przetrwają przerwę i restart,
- walidacją kontraktów wejścia-wyjścia między stacjami: kolejna stacja nie ruszy dalej, jeśli poprzednia nie dostarczyła uzgodnionych danych,
- bramką jakości z maksymalnie dwiema iteracjami poprawkowymi i eskalacją do człowieka,
- trzema ścieżkami routingu: szybką (5 stacji), pełną (9 stacji) i dogłębną (13 stacji), dobieranymi do złożoności zadania,
- możliwością wznowienia pracy od dowolnej stacji,
- audytowalnością przez bazę grafową Memgraph,
- opcjonalnym trybem autopilota, w którym serwer sam wywołuje model językowy dla każdej stacji.

## Architektura w skrócie

```
[Agent AI] <--MCP--> [Pipeline MCP Server]
                         |
           +-------------+-------------+
           |             |             |
     [Zarządzanie    [Koperta +    [Bramka
      run'em]        checkpointy]  jakości]
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

Diagram czyta się od góry. Agent AI (na przykład Devin albo Windsurf) rozmawia z serwerem przez MCP. Serwer dba jednocześnie o trzy rzeczy: prowadzi uruchomienia, opiekuje się kopertą danych wraz z punktami kontrolnymi i pilnuje bramki jakości. Wszystko, co zapisze, trafia do plików YAML na dysku, a gdy w systemie działa Memgraph, dodatkowo do grafu relacji. Dzięki temu po przerwaniu pracy zawsze można wrócić dokładnie tam, gdzie się skończyło.

Pojedyncze przejście przez pipeline nazywamy uruchomieniem (w skrócie: run). Narzędzia serwera układają się w 11 grup, a ich kolejność odzwierciedla drogę zadania: najpierw powstaje uruchomienie, potem wykonuje się stacje, w końcu pilnuje się jakości i zamyka pracę.

1. **Zarządzanie uruchomieniami** - `start_run`, `get_run_status`, `list_runs`, `resume_run`, `close_run`
2. **Wykonywanie stacji** - `execute_station`, `get_next_station`, `skip_station`, `get_station_contract`
3. **Prowadzenie koperty** - `get_envelope`, `update_envelope`, `validate_contract`
4. **Bramka jakości** - `quality_gate`, `get_gate_iterations`
5. **Punkty kontrolne** - `save_checkpoint_tool`, `load_checkpoint_tool`, `list_checkpoints_tool`
6. **Autopilot** - `auto_pilot_start`, `auto_pilot_status`, `auto_pilot_stop`
7. **RTM, czyli macierz powiązania wymagań z realizacją** - `get_rtm`, `update_rtm`, `add_rtm_entry`, `validate_rtm_coverage`
8. **Zarządzanie klientami (wieloklientowość)** - `register_client`, `resolve_client`, `set_active_client`, `get_active_client`, `get_client_info`, `list_clients`, `update_client`, `archive_client`, `delete_client`
9. **Wiedza współdzielona** - `save_shared_knowledge`, `get_shared_knowledge`, `search_shared_knowledge`, `list_shared_knowledge`
10. **Pamięć AI per klient** - `save_client_memory`, `get_client_memory`, `list_client_memories`, `save_shared_memory`, `get_shared_memory`, `search_client_memories`
11. **RAG per klient, czyli przeszukiwanie zaindeksowanych dokumentów** - `index_client_document`, `search_client_rag`, `search_shared_rag`, `list_rag_documents`

Dodatkowo narzędzia pomocnicze: `list_stations`, `verify_integrity`.

Szczegółowy opis narzędzi: `docs/02-tools-reference.md`.

## Dwa tryby pracy

Wybór trybu sprowadza się do jednego pytania: ile uwagi chcesz poświęcić prowadzeniu pracy?

### Tryb ręczny (domyślny)

Agent sam prowadzi wykonanie: wypełnia prompty stacji i zwraca wyniki, a serwer pilnuje stanu, waliduje kontrakty i po każdej stacji wskazuje następny krok (`next_station`). Serwer nie wywołuje przy tym żadnego modelu. Ten tryb sprawdza się, gdy chcesz widzieć i kształtować każdy etap.

```python
# Agent tworzy uruchomienie:
run = start_run(zamiar="Wdróż Filament 5.6.7", kontekst="BIP/Wymagania")
# -> run_id, first_station="inicjuj"

# Agent wykonuje stację inicjuj i zwraca wynik:
execute_station(run_id, station="inicjuj", output={...})
# -> next_station="zmienne", envelope_updated

# Agent wykonuje stację zmienne...
execute_station(run_id, station="zmienne", output={...})
# -> next_station="analiza"
# ... i tak do końca.
```

### Tryb autopilota (opcjonalny)

Gdy zadanie jest rutynowe, prowadzenie można oddać serwerowi. Serwer sam wywołuje model językowy dla każdej stacji, zapisuje punkty kontrolne i obsługuje bramkę jakości; agent jedynie rozpoczyna pracę i obserwuje jej przebieg. Obsługiwani dostawcy: `openai`, `anthropic` oraz `local` (Ollama albo dowolny lokalny serwer zgodny z API OpenAI; wybór reguluje zmienna `PIPELINE_LLM_PROVIDER`).

```python
auto_pilot_start(run_id, from_station="inicjuj")
# Serwer kolejno wywołuje model dla każdej stacji,
# zapisuje punkty kontrolne, obsługuje bramkę jakości.
# Agent może sprawdzić stan:
auto_pilot_status(run_id)
# Albo zatrzymać:
auto_pilot_stop(run_id)
```

Szczegóły: `docs/07-auto-pilot.md`.

## Samodzielność

Serwer można uruchomić na dowolnej maszynie z Pythonem 3.11+ i niczego do niego nie dokopiować:

- **umiejętności wbudowane** - prompty wszystkich trzynastu stacji są częścią pakietu (`src/pipeline_mcp/skills/`), serwer nie czyta `/etc/windsurf/skills/`,
- **kontrakty wbudowane** - mapowania wejść i wyjść między stacjami są w kodzie (`contracts.py`), a nie w zewnętrznym pliku,
- **specyfikacja wbudowana** - definicje ścieżek, bramki i punktów kontrolnych również żyją w kodzie,
- **brak zależności plikowych** - nie trzeba przenosić katalogów umiejętności,
- **praca lokalna** - serwer uruchamia się przez `uvx` albo `python -m`, a agent (Devin albo Windsurf w VSCode) łączy się z nim przez stdio.

Pliki umiejętności w `src/pipeline_mcp/skills/` są kopią oryginałów z `/etc/windsurf/skills/` i stanowią część pakietu. Wprowadzenie w nich zmian wymaga wydania nowej wersji pakietu.

## Instalacja

### Wymagania

- Python >= 3.11,
- uvx dostępny w systemie,
- opcjonalnie: Memgraph dla warstwy grafowej.

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

Alternatywnie, uruchomienie lokalne z katalogu projektu (na czas pracy nad kodem):

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

Szczegóły konfiguracji: `docs/09-configuration.md`.

## Prompty MCP

Poza narzędziami serwer wystawia dwa prompty, które skracają start pracy:

- `pipeline_start(zamiar, kontekst, zrodla, workspace, client_id)` - rozpoczyna nowe uruchomienie (wywołuje `start_run`) i zwraca instrukcje do pierwszej stacji,
- `pipeline_continue(run_id, workspace, client_id)` - wznawia istniejące uruchomienie i zwraca kontekst wraz z kolejną stacją.

## Wieloklientowość

Przy prowadzeniu projektów dla kilku klientów liczy się jedno: ich dane nie mogą się mieszać. Serwer izoluje uruchomienia, pamięć AI, RAG i wiedzę współdzieloną per klient:

- `register_client`, `resolve_client` i `set_active_client` odpowiadają za rejestrację i aktywację klienta,
- uruchomienia klienta zapisują się w `.ai-kb/clients/<client_id>/pipeline-runs/`,
- bez aktywnego klienta serwer pracuje w trybie starszym (legacy), ze wspólnym katalogiem `.ai-kb/pipeline-runs/` dla wszystkich uruchomień.

## Szybki start

Nie trzeba wierzyć na słowo. Najlepszy dowód to małe zadanie i pięć kroków:

1. Utwórz uruchomienie: `start_run(zamiar="Twój cel")` (albo użyj promptu `pipeline_start`),
2. Sprawdź pierwszą stację: `get_next_station(run_id)`,
3. Wykonuj kolejne stacje sam (tryb ręczny) albo uruchom autopilota,
4. Po stacji `sprawdzenie` przepuść wynik przez bramkę jakości: `quality_gate(run_id, audit_status)`,
5. Zamknij pracę: `close_run(run_id)`.

## Praca nad kodem

```bash
# Instalacja lokalna (z zależnościami testowymi)
pip install -e ".[dev]"

# Testy
pytest
```

## Dokumentacja

| Plik | Temat |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | Architektura, komponenty, przepływ danych |
| [docs/02-tools-reference.md](docs/02-tools-reference.md) | Referencja wszystkich narzędzi MCP |
| [docs/03-envelope-spec.md](docs/03-envelope-spec.md) | Specyfikacja koperty (YAML envelope) |
| [docs/04-paths-and-routing.md](docs/04-paths-and-routing.md) | Ścieżki pipeline'u i routing |
| [docs/05-quality-gate.md](docs/05-quality-gate.md) | Bramka jakości i pętla zwrotna |
| [docs/06-checkpointing.md](docs/06-checkpointing.md) | Mechanizm punktów kontrolnych i restart |
| [docs/07-auto-pilot.md](docs/07-auto-pilot.md) | Tryb autopilota z modelem językowym |
| [docs/08-memgraph-integration.md](docs/08-memgraph-integration.md) | Integracja z Memgraph |
| [docs/09-configuration.md](docs/09-configuration.md) | Konfiguracja i instalacja |
| [docs/10-stations-builtin.md](docs/10-stations-builtin.md) | Wbudowane umiejętności stacji |

## Źródła prawdy (wbudowane)

Serwer zawiera wbudowane kopie następujących plików w `src/pipeline_mcp/skills/`:

- `pipeline_sklills.md` - specyfikacja pipeline'u umiejętności,
- `kontrakty_pipelines.md` - kontrakty wejścia-wyjścia między stacjami,
- `<stacja>/SKILL.md` - specyfikacja każdej z trzynastu stacji,
- `_shared/zrodla-i-narzedzia.md` - wspólne zasady pracy ze źródłami,
- `_shared/graf-pipeline.md` - schemat grafu Memgraph.

Pliki są kopią oryginałów z `/etc/windsurf/skills/` i stanowią część pakietu. Serwer nie odczytuje umiejętności z systemu: wszystkie są wbudowane.

## Licencja

MIT (zgodnie z `pyproject.toml`). Autor: EVILLAGE.
