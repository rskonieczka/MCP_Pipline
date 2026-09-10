# Architektura Pipeline MCP Server

## 1. Przeglad

Pipeline MCP Server jest w pelni samodzielnym serwerem MCP (Model Context Protocol) napisanym w Pythonie z uzyciem FastMCP. Jego zadaniem jest orkiestracja agentow AI w petli pipeline.

Serwer jest self-contained: zawiera wbudowane skille wszystkich 13 stacji (prompty SKILL.md), kontrakty I/O miedzy stacjami i specyfikacje pipeline'u. Nie zalezy od zewnetrznych katalogow skilli (`/etc/windsurf/skills/`). Uruchamiany lokalnie, agent (Devin/Windsurf w VSCode) laczy sie przez stdio.

Serwer nie zastepuje skilli (promptow stacji) - materializuje je jako wbudowane zasoby pakietu. Serwer dostarcza infrastrukture operacyjna: zarzadza stanem run'u, waliduje kontrakty miedzy stacjami, prowadzi przez sciezki pipeline'u, obsluguje bramke jakosci, checkpointuje stan i integruje sie z Memgraph.

## 2. Zasady projektowe

### 2.1. Minimalna ingerencja w logike stacji

Serwer nie implementuje logiki merytorycznej stacji. Logike wykonuje agent AI (tryb manual) lub LLM wywolany przez serwer (tryb auto-pilot). Serwer odpowiada za:

- zarzadzanie cyklem zycia run'u,
- utrzymanie i walidacje koperty,
- checkpointowanie,
- routing sciezek,
- bramke jakosci,
- integracje z Memgraph.

### 2.2. Koperta jako jedyny nośnik danych

Zgodnie z `pipeline_sklills.md`, jedynym formalnym kanalem przekazu pol kontraktowych miedzy stacjami jest koperta (blok YAML). Serwer materializuje te zasade: kazde wywolanie `execute_station` przyjmuje wyjscie stacji, serwer aktualizuje koperte i zwraca zaktualizowany stan.

### 2.3. Restartowalnosc

Kazda stacja merytoryczna po zakonczeniu zapisuje checkpoint do pliku YAML. Restart od dowolnej stacji polega na odczycie manifestu, zaladowaniu ostatniego checkpointu i kontynuacji od stacji nastepnej.

### 2.4. Audytowalnosc

Stan run'u jest zapisany w plikach YAML (czytelnych dla czlowieka i diff-friendly) oraz w Memgraph (graf relacji miedzy encjami). Umozliwia to audyt ex-post przez skilla `audyt_runu`.

## 3. Komponenty

```
src/pipeline_mcp/
  __init__.py
  server.py              # FastMCP server, rejestracja narzedzi
  config.py              # Konfiguracja (env vars)
  models.py              # Pydantic modele: Run, Envelope, Stan, Manifest, RTMEntry, GateHistoryEntry, ClientContext, ClientMemoryEntry, SharedKnowledgeEntry (patrz 3.2)
  envelope.py            # Logika koperty: tworzenie, aktualizacja, walidacja
  checkpoint.py          # Checkpointowanie plikowe YAML
  manifest.py            # Zarzadzanie manifestem run'u
  routing.py             # Logika sciezek: szybki, pelny, doglebny
  quality_gate.py        # Bramka jakosci, petla zwrotna, eskalacja
  stations.py            # Definicje stacji, kontrakty I/O, kolejnosc (wbudowane)
  contracts.py           # Walidacja kontraktow miedzy stacjami (wbudowane)
  memgraph.py            # Integracja z Memgraph MCP (zapis relacji)
  auto_pilot.py          # Tryb auto-pilot: wywolywanie LLM per stacja
  llm.py                 # Abstrakcja dostawcy LLM (OpenAI, Anthropic, lokalny)
  skills_loader.py       # Ladowanie wbudowanych skilli z pakietu (src/pipeline_mcp/skills/)
  rtm.py                 # Requirements Traceability Matrix - sledzenie wymagan
  client_registry.py     # Rejestr klientow (multi-tenant): CRUD, dopasowanie L1-L6
  client_memory.py       # Pamiec AI per-klient i wspoldzielona
  knowledge.py           # Wiedza wspoldzielona (decisions, patterns, pitfalls)
  rag.py                 # RAG per-klient i wspoldzielony (indeks keyword-based)
  skills/                # Wbudowane skille stacji (self-contained)
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
    pipeline_sklills.md   # Wbudowana specyfikacja pipeline'u
    kontrakty_pipelines.md # Wbudowane kontrakty I/O
    _shared/              # Wbudowane zasoby wspoldzielone
      zrodla-i-narzedzia.md
      graf-pipeline.md
```

### 3.1. server.py

Glowny punkt wejscia. Rejestruje wszystkie narzedzia MCP przez dekoratory FastMCP (`@mcp.tool()`). Kazde narzedzie deleguje do odpowiedniego modulu.

### 3.2. models.py

Modele Pydantic dla struktur danych:

- `Run` - identyfikator run'u, zamiar, sciezka, status, iteracja bramki, client_id
- `Envelope` (Koperta) - run_id, sciezka, stacja_aktualna, stacja_poprzednia, stan, pola_stacji, walidacja, relacje, rtm, wejscie, client_id, timestamp
- `Stan` - skumulowane pola kluczowe (zamiar, klasyfikacja, punkt_wejscia, client_id)
- `RTMEntry` - wpis Requirements Traceability Matrix (req_id, opis, zrodlo, stacje_adresujace, stacja_weryfikujaca, stacja_niespelnienia, status, artefakty, checkpoint_weryfikacji)
- `Manifest` - indeks stacji, statusy, timestampy, checkpointy, iteracja_bramki, historia_bramki, client_id
- `GateHistoryEntry` - wpis historii iteracji bramki (iteracja, timestamp, audit_status, loop_target, gate_decision)
- `StationOutput` - wyjscie stacji przekazywane przez agenta
- `ContractValidation` - wynik walidacji kontraktu wejscia stacji docelowej
- `ClientContext` - kontekst zarejestrowanego klienta (client_id, display_name, status, aliases, external_ids, id_fragments, metadata)
- `ClientMatch` - pojedyncze dopasowanie klienta (client_id, display_name, confidence, matched_on)
- `ResolveResult` - wynik resolve_client (query, normalized, matches, auto_resolved, needs_confirmation, suggested_action)
- `ClientMemoryEntry` - wpis pamieci AI per-klient (memory_id, topic, content, scope, client_id, timestamp, tags)
- `SharedKnowledgeEntry` - wpis wiedzy wspoldzielonej (knowledge_id, category, title, content, source, timestamp, tags)

### 3.3. envelope.py

Operacje na kopercie:

- `create_envelope(run_id, zamiar, sciezka, client_id)` - inicjalna koperta po `start_run`
- `update_station_fields(envelope, station, output)` - aktualizacja `pola_stacji.<station>`
- `accumulate_state(envelope, station, output)` - kumulacja pol kluczowych w `stan`
- `add_station_relations(envelope, station, run_id)` - dodanie relacji `zawiera` i `nastapila_po` (z `client_id` w node IDs)
- `compress_envelope(envelope, keep_last_n=3)` - kompresja w sciezce doglebny
- `get_envelope_summary(envelope)` - skrot koperty do wynikow narzedzi
- `serialize_envelope(envelope)` - serializacja do YAML
- `deserialize_envelope(yaml_str)` - deserializacja z YAML

### 3.4. checkpoint.py

- `save_checkpoint(run_id, station, envelope, suffix, workspace, client_id)` - zapis do `stan_<station><suffix>.yaml`
- `load_checkpoint(run_id, station, suffix, workspace, client_id)` - odczyt checkpointu
- `list_checkpoints(run_id, workspace, client_id)` - lista dostepnych checkpointow
- `get_latest_checkpoint(run_id, workspace, client_id)` - ostatni zakonczony checkpoint (z manifestu, fallback po mtime)
- `save_envelope_final(run_id, envelope, workspace, client_id)` - ostateczna koperta po close_run

### 3.5. routing.py

Logika wyboru sciezki i kolejnosci stacji:

- `determine_path(klasyfikacja, stawka="", ryzyko="")` - wybor sciezki (stawka/ryzyko opcjonalne)
- `get_station_sequence(path)` - kolejnosc stacji dla sciezki
- `get_next_station(current, path, gate_status)` - nastepna stacja
- `get_skipped_stations(path)` - stacje pomijane w sciezce

### 3.6. quality_gate.py

- `evaluate_gate(run_id, manifest, audit_status, audit_wymiary, loop_target)` - ocena bramki (przyjmuje obiekt `Manifest`, waliduje `audit_status`)
- `reset_stations_for_loop(manifest, loop_target)` - reset statusow stacji od celu powrotu na `w_trakcie`
- `infer_loop_target(wymiary, sciezka)` - wnioskuje cel powrotu na podstawie wymiarow audytu i sciezki
- `get_gate_history(run_id, manifest)` - zwraca historie iteracji bramki z manifestu

### 3.7. stations.py

Definicje 13 stacji z ich kontraktami I/O:

```python
STATIONS = {
    "inicjuj": StationDef(
        name="inicjuj",
        phase="Inicjacja",
        required_input=["ZAMIAR_UZYTKOWNIKA"],
        optional_input=["KONTEKST", "ZRODLA", "TRYB_INICJACJI"],
        output=["klasyfikacja", "punkt_wejscia", "uzasadnienie", "ryzyka"],
        next_station_resolver="inicjuj_next",  # logika wyboru nastepnej
    ),
    "zmienne": StationDef(...),
    # ... pozostale stacje
}
```

Kolejnosc stacji i zaleznosci miedzy nimi sa zdefiniowane na podstawie `kontrakty_pipelines.md`.

### 3.8. contracts.py

Walidacja kontraktow miedzy stacjami na podstawie mapowania pole-po-polu z `kontrakty_pipelines.md`:

- `validate_input(target_station, envelope)` - sprawdzenie pol wymaganych
- `map_fields(source_station, target_station, envelope)` - mapowanie pol z wyjscia na wejscie
- `infer_field(field_name, envelope)` - wnioskowanie pol `agent_inference`
- `check_completeness(target_station, envelope)` - status: gotowy/wnioskowane/niekompletne

### 3.9. memgraph.py

Integracja z Memgraph przez sterownik bolt. Node IDs zawieraja `client_id` dla izolacji wieloklientowej (legacy gdy puste):

- `write_run_node(run_id, zamiar, sciezka, client_id)` - wezel Run (`run:<client_id>:<run_id>`)
- `write_station_node(run_id, station, status, checkpoint, client_id)` - wezel Stacja (`stacja:<client_id>:<run_id>:<station>`)
- `write_relation(source, target, rel_type, fields)` - krawedzie
- `write_rtm_nodes(run_id, envelope)` - wezly Wymaganie i relacje ADRESUJE/WERYFIKUJE (`wymaganie:<client_id>:<run_id>:<req_id>`)
- `close_run_node(run_id, timestamp_end, client_id)` - zamkniecie wezla Run
- `validate_graph_continuity(run_id, client_id)` - walidacja ciaglosci grafu (filtr po client_id)
- `write_shared_knowledge_node(knowledge_id, category, title, content)` - wezel Wiedza (`wiedza:<knowledge_id>`, client_id="shared")
- `write_client_memory_node(memory_id, client_id, topic, content, scope)` - wezel Pamiec (`pamiec:<client_id>:<memory_id>`)
- `delete_client_nodes(client_id)` - usuniecie wezlow klienta z Memgraph (GDPR)

### 3.10. auto_pilot.py

Tryb auto-pilot:

- `start_auto_pilot(run_id, from_station)` - uruchomienie sekwencyjnego wykonania
- `execute_station_with_llm(run_id, station)` - wywolanie LLM z promptem skilla
- `handle_gate_in_auto(run_id)` - obsluga bramki w trybie auto
- `stop_auto_pilot(run_id)` - zatrzymanie
- `get_auto_pilot_status(run_id)` - status wykonania

### 3.11. llm.py

Abstrakcja dostawcy LLM:

- `LLMProvider` (protokol) - `complete(prompt, system?) -> str`
- `OpenAIProvider` - przez openai SDK
- `AnthropicProvider` - przez anthropic SDK
- `LocalProvider` - przez Ollama/OpenAI-compatible endpoint

Konfiguracja przez env vars: `PIPELINE_LLM_PROVIDER`, `PIPELINE_LLM_MODEL`, `PIPELINE_LLM_API_KEY`.

### 3.12. skills_loader.py

Ladowanie wbudowanych skilli z pakietu (`src/pipeline_mcp/skills/`). Skille sa kopia oryginalow z `/etc/windsurf/skills/` wbudowana w pakiet - serwer nie odczytuje skilli z systemu plikow uzytkownika.

- `load_skill(station_name)` - odczyt `SKILL.md` z wbudowanego katalogu pakietu, parsowanie frontmatter i tresci
- `get_skill_prompt(station_name, envelope)` - budowanie promptu dla stacji z wstrzyknieciem koperty
- `list_available_skills()` - lista dostepnych wbudowanych skilli
- `get_pipeline_spec()` - odczyt wbudowanej specyfikacji `pipeline_sklills.md`
- `get_contracts_spec()` - odczyt wbudowanych kontraktow `kontrakty_pipelines.md`

Skille sa ladowane przez `importlib.resources` (Python 3.9+), co umozliwia dostep do zasobow pakietu niezaleznie od miejsca instalacji.

### 3.13. rtm.py

Requirements Traceability Matrix - sledzenie wymagan uzytkownika przez caly pipeline. Ekstrahuje wymagania z `variables` typu `requirement` po stacji `zmienne`, automatycznie aktualizuje statusy po `realizuj`/`weryfikacja`/`sprawdzenie`, waliduje pokrycie wymagan.

- `extract_requirements_from_zmienne(output)` - ekstrakcja wymagan z wyjscia stacji zmienne
- `auto_update_rtm(envelope, station, output)` - automatyczna aktualizacja RTM po stacjach
- `validate_coverage(envelope)` - raport pokrycia wymagan (total, nieadresowane, zrealizowane, weryfikowane, niespelnione, pokrycie_procent)
- `update_entry(envelope, req_id, updates)` - reczna aktualizacja wpisu RTM
- `add_entry(envelope, entry_data)` - dodanie nowego wpisu RTM

Statusy wymagan: `nieadresowane` -> `adresowane` -> `zrealizowane` -> `weryfikowane` / `niespelnione`.

Integracja z Memgraph: wezly `:Wymaganie`, relacje `:ADRESUJE` (Stacja -> Wymaganie), `:WERYFIKUJE` (Stacja -> Wymaganie). Zapis przez `write_rtm_nodes` w `memgraph.py`.

### 3.14. client_registry.py

Rejestr klientow (multi-tenant). Zarzadza kontekstem klienta w `<workspace>/.ai-kb/clients/<client_id>/context.yaml`.

- `register_client(client_id, display_name, ...)` - rejestracja nowego klienta
- `load_client(client_id, workspace)` - odczyt kontekstu (None gdy nie istnieje)
- `update_client(client_id, updates, ...)` - aktualizacja metadanych, aliasow, NIP
- `archive_client(client_id, ...)` - archiwizacja (zmiana statusu na `zarchiwizowany`)
- `delete_client(client_id, ...)` - usuniecie plikow + wezlow Memgraph (GDPR)
- `resolve_client(query, ...)` - dopasowanie 6-warstwowe (L1-L6: client_id, external_id, alias, id_fragment, fuzzy_name, brak)

Walidacja `client_id`: regex `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (ochrona przed path traversal). Zapisy atomowe (`tempfile` + `os.replace`).

### 3.15. client_memory.py

Pamiec AI per-klient i wspoldzielona. Zapis w formacie YAML.

- `save_client_memory(topic, content, client_id, tags, memory_id)` - pamiec per-klient
- `save_shared_memory(topic, content, tags, memory_id)` - pamiec wspoldzielona
- `get_client_memory(memory_id, client_id)` / `list_client_memories(client_id)` / `search_client_memories(query, client_id, include_shared)`

Auto-generowany `memory_id` jest unikalny przy kolizji tematu (dodatek timestamp). Jawny `memory_id` zachowuje semantyke upsert. Zapisy atomowe. Integracja z Memgraph przez `write_client_memory_node`.

### 3.16. knowledge.py

Wiedza wspoldzielona (cross-client) w 3 kategoriach: `decision`, `pattern`, `pitfall` (wartosci pola `category`; katalogi na dysku sa mnogie: `decisions/`, `patterns/`, `pitfalls/`).

- `save_shared_knowledge(knowledge_id, category, title, content, source, tags)` - zapis wezla wiedzy
- `get_shared_knowledge(knowledge_id, category)` / `search_shared_knowledge(query, category)` / `list_shared_knowledge(category)`

Sanityzacja `knowledge_id` (slug). Zapisy atomowe. Integracja z Memgraph przez `write_shared_knowledge_node` (client_id="shared").

### 3.17. rag.py

RAG (Retrieval-Augmented Generation) per-klient i wspoldzielony. Indeks keyword-based w formacie YAML.

- `index_client_document(doc_id, content, client_id, metadata)` - indeksowanie dokumentu per-klient
- `search_client_rag(query, client_id, include_shared, limit)` - przeszukiwanie RAG klienta + wspoldzielonego
- `list_rag_documents(client_id)` - lista zaindeksowanych dokumentow

Blokady per-sciezka-indeksu (`weakref.WeakValueDictionary`) chronia przed lost update w rownoleglym indeksowaniu. Atomowy zapis indeksu (`tempfile.mkstemp` + `os.replace`).

## 4. Przeplyw danych

### 4.1. Tryb manual - pelny cykl

```
1. Agent: start_run(zamiar="...")
   Serwer: tworzy run_id, manifest, pusta koperte
   Serwer: zwraca run_id, first_station="inicjuj"

2. Agent: get_station_contract(run_id, "inicjuj")
   Serwer: zwraca wymagane/polowe wejsciowe dla inicjuj

3. Agent: [wykonuje skilla inicjuj jako prompt, zwraca wynik]

4. Agent: execute_station(run_id, "inicjuj", output={klasyfikacja, punkt_wejscia, ...})
   Serwer: waliduje wyjscie inicjuj
   Serwer: aktualizuje koperte (pola_stacji.inicjuj, stan)
   Serwer: zapisuje checkpoint stan_inicjuj.yaml
   Serwer: aktualizuje manifest (inicjuj: zakonczona)
   Serwer: zapisuje relacje do Memgraph
   Serwer: wyznacza nastepna stacje na podstawie klasyfikacji
   Serwer: zwraca {next_station, envelope_summary, validation}

5. Agent: [wykonuje nastepna stacje...]

6. Po sprawdzenie:
   Agent: quality_gate(run_id, audit_status="zgodny"|"niezgodny")
   Serwer: jezeli zgodny -> next_station=ewaluacja|utrwal
   Serwer: jezeli niezgodny -> loop_back do dobierz|planuj (iteracja++)
   Serwer: jezeli iteracja > 2 -> escalate (zatrzymanie, powiadomienie uzytkownika)

7. Po ostatniej stacji:
   Agent: close_run(run_id)
   Serwer: zamyka manifest, zapisuje wezel Run jako zakonczony
```

### 4.2. Tryb auto-pilot

```
1. Agent: start_run(zamiar="...")
2. Agent: auto_pilot_start(run_id, from_station="inicjuj")
   Serwer: petla:
     a. zaladuj prompt skilla stacji
     b. wstrzyknij koperte do promptu
     c. wywolaj LLM
     d. parsuj wyjscie (KOPERTA block)
     e. execute_station(run_id, station, output)
     f. jezeli bramka -> obsluz (loop_back lub kontynuuj)
     g. jezeli ostatnia stacja -> zakoncz
     h. jezeli blokada -> zatrzymaj auto-pilot, zwroc status
3. Agent: auto_pilot_status(run_id) -> monitoruje postep
4. Agent: auto_pilot_stop(run_id) -> opcjonalne zatrzymanie
```

## 5. Struktura persystencji

### 5.1. Tryb legacy (brak client_id)

```
.ai-kb/pipeline-runs/
  <run_id>/
    manifest.yaml
    stan_inicjuj.yaml
    ...
    envelope_final.yaml
```

### 5.2. Tryb wieloklientowy (z client_id)

```
.ai-kb/
  clients/
    <client_id>/
      context.yaml              # metadane klienta, aliasy, NIP, status
      pipeline-runs/
        <run_id>/
          manifest.yaml
          stan_inicjuj.yaml
          ...
          envelope_final.yaml
      memory/
        <memory_id>.yaml        # pamiec AI per-klient
      rag/
        index.yaml              # indeks keyword-based
        documents/
          <doc_id>.yaml         # zaindeksowane dokumenty
  shared-knowledge/
    memory/
      <memory_id>.yaml          # pamiec wspoldzielona
    rag/
      index.yaml
      documents/
        <doc_id>.yaml
    decisions/
      <knowledge_id>.yaml       # decyzje architektoniczne
    patterns/
      <knowledge_id>.yaml       # wzorce projektowe
    pitfalls/
      <knowledge_id>.yaml       # pulapki i leki
```

Szczegoly: `docs/06-checkpointing.md`.

## 6. Relacja z istniejacymi serwerami MCP

| Serwer MCP | Relacja z Pipeline MCP |
|---|---|
| Serena | Serwer Pipeline nie zastepuje Serena. Serena przechowuje pamiec projektu (decyzje, preferencje). Pipeline MCP przechowuje stan run'u. Skilla `utrwal` zapisuje wnioski do Serena po zakonczeniu run'u. |
| Memgraph | Pipeline MCP zapisuje relacje miedzy encjami run'u do Memgraph. Memgraph jest warstwa grafowa uzupełniajaca checkpointy plikowe. |
| Context7 | Wywolywany przez agenta wewnatrz stacji `realizuj` (skilla `context7`). Pipeline MCP nie integruje Context7 bezposrednio. |
| sequential-thinking | Moze byc wywolywany przez agenta wewnatrz stacji wymagajacych wieloetapowego rozumowania. Pipeline MCP nie integruje go bezposrednio. |
| desktop-commander | Wywolywany przez agenta do operacji na plikach wewnatrz stacji. Pipeline MCP nie integruje go bezposrednio. |

## 7. Granice odpowiedzialnosci

### Serwer robi

- Zarzadza cyklem zycia run'u (tworzenie, status, zamkniecie)
- Utrzymuje koperte i waliduje kontrakty I/O
- Checkpointuje stan do plikow YAML
- Prowadzi przez sciezki pipeline'u (routing)
- Obsluguje bramke jakosci (max 2 iteracje, eskalacja)
- Zapisuje relacje do Memgraph
- W trybie auto-pilot: wywoluje LLM per stacja

### Serwer nie robi

- Nie implementuje logiki merytorycznej stacji (to rola agenta/LLM)
- Nie zastepuje skilli (prompty pozostaja wbudowane w pakiecie jako zasoby)
- Nie zarzadza pamiecia projektu (to Serena)
- Nie wykonuje operacji na plikach kodu (to desktop-commander)
- Nie pobiera dokumentacji bibliotek (to Context7)

## 8. Samodzielnosc (self-contained)

Serwer jest w pelni samodzielny. Oznacza to:

### 8.1. Wbudowane skille

Wszystkie 13 stacji pipeline'u (prompty `SKILL.md`) jest wbudowanych w pakiet w `src/pipeline_mcp/skills/`. Sa to kopie oryginalow z `/etc/windsurf/skills/`. Serwer nie odczytuje skilli z systemu plikow uzytkownika.

### 8.2. Wbudowane kontrakty

Mapowania I/O miedzy stacjami (`kontrakty_pipelines.md`) sa wbudowane w pakiet i zaimplementowane w kodzie (`contracts.py`, `stations.py`). Serwer nie czyta kontraktow z zewnetrznego pliku.

### 8.3. Wbudowana specyfikacja

Definicje sciezek, bramki jakosci, checkpointow (`pipeline_sklills.md`) sa wbudowane w pakiet i zaimplementowane w kodzie (`routing.py`, `quality_gate.py`, `checkpoint.py`).

### 8.4. Brak zaleznosci plikowych

Serwer mozna uruchomic na dowolnej maszynie z Python 3.11+ bez kopiowania katalogow skilli. Jedyne zaleznosci zewnetrzne to:

- Pakiety Python: `fastmcp`, `pydantic`, `pyyaml` (instalowane przez uvx/pip)
- Opcjonalnie: Memgraph dla warstwy grafowej
- Opcjonalnie: klucz API LLM dla trybu auto-pilot

### 8.5. Lokalne dzialanie

Serwer uruchamiany lokalnie przez `uvx` lub `python -m pipeline_mcp`. Agent (Devin/Windsurf w VSCode) laczy sie przez stdio (standard MCP). Zadnych zdalnych serwisow poza opcjonalnym Memgraph i opcjonalnym API LLM.

### 8.6. Aktualizacja skilli

Aktualizacja wbudowanych skilli wymaga aktualizacji pakietu serwera. Pliki w `src/pipeline_mcp/skills/` sa czescia repozytorium i wersjonowane razem z kodem serwera.
