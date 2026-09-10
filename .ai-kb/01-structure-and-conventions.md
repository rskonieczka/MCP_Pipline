# Struktura i konwencje

## Struktura katalogow

```
Pipline/
  README.md                    # Przeglad, instalacja, szybki start
  docs/                        # Dokumentacja architektoniczna
    01-architecture.md         # Architektura, komponenty, przeplyw danych
    02-tools-reference.md      # Referencja ~49 narzedzi MCP (11 grup)
    03-envelope-spec.md        # Specyfikacja koperty (YAML envelope)
    04-paths-and-routing.md    # Sciezki pipeline'u i routing
    05-quality-gate.md         # Bramka jakosci i petla zwrotna
    06-checkpointing.md        # Mechanizm checkpointow i restart
    07-auto-pilot.md           # Tryb auto-pilot z LLM
    08-memgraph-integration.md # Integracja z Memgraph
    09-configuration.md        # Konfiguracja i instalacja
    10-stations-builtin.md     # Wbudowane skille stacji
  .ai-kb/                      # Baza wiedzy projektu
    00-overview.md
    01-structure-and-conventions.md  (ten plik)
    02-decisions-and-pitfalls.md
  src/
    pipeline_mcp/              # Pakiet Python
      server.py                # FastMCP server, rejestracja narzedzi
      config.py                # Konfiguracja (env vars, sciezki per-klient)
      models.py                # Pydantic modele: Run, Envelope, Manifest, RTMEntry, ClientContext, ClientMemoryEntry, SharedKnowledgeEntry
      envelope.py              # Logika koperty: tworzenie, aktualizacja, relacje (z client_id)
      checkpoint.py            # Checkpointowanie plikowe YAML (per-klient)
      manifest.py              # Zarzadzanie manifestem run'u (per-klient)
      routing.py               # Logika sciezek: szybki, pelny, doglebny
      quality_gate.py          # Bramka jakosci, petla zwrotna, eskalacja
      stations.py              # Definicje stacji, kontrakty I/O, kolejnosc (wbudowane)
      contracts.py             # Walidacja kontraktow miedzy stacjami (wbudowane)
      memgraph.py              # Integracja z Memgraph (node IDs z client_id, Wiedza, Pamiec, delete_client_nodes)
      auto_pilot.py            # Tryb auto-pilot: wywolywanie LLM per stacja
      llm.py                   # Abstrakcja dostawcy LLM (OpenAI, Anthropic, lokalny)
      skills_loader.py         # Ladowanie wbudowanych skilli z pakietu
      rtm.py                   # Requirements Traceability Matrix
      client_registry.py       # Rejestr klientow (CRUD, dopasowanie L1-L6, walidacja slug)
      client_memory.py         # Pamiec AI per-klient i wspoldzielona (atomowy zapis, unikalnosc ID)
      knowledge.py             # Wiedza wspoldzielona (decisions, patterns, pitfalls)
      rag.py                   # RAG per-klient i wspoldzielony (blokady per-sciezka, atomowy indeks)
      skills/                  # Wbudowane skille (self-contained)
        inicjuj-run/SKILL.md
        zmienne/SKILL.md
        analiza/SKILL.md
        dekompozycja/SKILL.md
        dobierz/SKILL.md
        routing/SKILL.md
        planuj/SKILL.md
        realizuj/SKILL.md
        weryfikacja/SKILL.md
        sprawdzenie/SKILL.md
        ewaluacja/SKILL.md
        utrwal/SKILL.md
        monitoruj/SKILL.md
        audyt-runu/SKILL.md
        pipeline_sklills.md
        kontrakty_pipelines.md
        _shared/
          zrodla-i-narzedzia.md
          graf-pipeline.md
  tests/
    conftest.py                # Fixtures: isolated_runs, two_clients (reset _active_client_id)
    test_pipeline.py           # Testy bazowe (start_run, execute_station, bramka, auto-pilot)
    test_rtm.py                # Testy RTM (38 testow)
    test_client_isolation.py   # Testy izolacji wieloklientowej (runy, pamiec, RAG, kolizje, walidacja)
    test_client_registry.py    # Testy rejestru klientow (CRUD, aliasy, path traversal, node IDs)
```

## Konwencje

- Jezyk dokumentacji: polski (zgodnie z globalnymi zasadami stylu)
- Jezyk kodu: angielski (nazwy funkcji, zmiennych, klas)
- Jezyk komentarzy: polski
- Format persystencji: YAML (czytelny, diff-friendly)
- Format wymiany MCP: JSON (Pydantic modele)
- Nazewnictwo stacji: zgodne z oryginalnymi skillami (`inicjuj`, `zmienne`, ...)
- Nazewnictwo narzedzi MCP: snake_case (`start_run`, `execute_station`, ...)
- Nazewnictwo plikow checkpointow: `stan_NN_<stacja>.yaml`

## Konwencje wieloklientowe (multi-tenant)

- Walidacja `client_id`: regex `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (min 2 znaki, male litery ASCII, cyfry, myślniki, bez separatorow sciezki)
- Hierarchia rozwiazywania `client_id`: jawny parametr -> aktywny klient sesji (`set_active_client`) -> `PIPELINE_DEFAULT_CLIENT_ID` -> tryb legacy (`""`)
- Sciezki per-klient:
  - Runy: `<workspace>/.ai-kb/clients/<client_id>/pipeline-runs/<run_id>/`
  - Pamiec: `<workspace>/.ai-kb/clients/<client_id>/memory/<memory_id>.yaml`
  - RAG: `<workspace>/.ai-kb/clients/<client_id>/rag/`
  - Kontekst: `<workspace>/.ai-kb/clients/<client_id>/context.yaml`
- Sciezki wspoldzielone:
  - Pamiec: `<workspace>/.ai-kb/shared-knowledge/memory/`
  - RAG: `<workspace>/.ai-kb/shared-knowledge/rag/`
  - Wiedza: `<workspace>/.ai-kb/shared-knowledge/{decisions,patterns,pitfalls}/`
- Tryb legacy (brak `client_id`): runy w `<workspace>/.ai-kb/pipeline-runs/` (kompatybilnosc wstecz)
- Node IDs Memgraph z `client_id`: `run:<client_id>:<run_id>`, `stacja:<client_id>:<run_id>:<station>`, `wymaganie:<client_id>:<run_id>:<req_id>`, `pamiec:<client_id>:<memory_id>` (legacy bez `client_id` w prefiksie)
- Wezly wspoldzielone: `client_id="shared"` (`wiedza:<knowledge_id>`, `pamiec:shared:<memory_id>`)
- Zapisy plikow YAML: atomowe (`tempfile.mkstemp` + `os.replace`) we wszystkich modulach
- Auto-generowany `memory_id`: unikalny przy kolizji (dodatek timestamp), jawny `memory_id` zachowuje semantyke upsert
- Blokady RAG: `weakref.WeakValueDictionary` per-sciezka-indeksu (zapobiega wyciekowi pamieci)

## Zaleznosci

- `fastmcp` - framework serwera MCP
- `pydantic` - modele danych
- `pyyaml` - persystencja YAML
- Opcjonalnie: `neo4j` (sterownik Memgraph)
- Opcjonalnie: `openai` / `anthropic` (dostawcy LLM dla auto-pilota)
