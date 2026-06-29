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
  models.py              # Pydantic modele: Run, Envelope, Station, Manifest
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

- `Run` - identyfikator run'u, zamiar, sciezka, status, iteracja bramki
- `Envelope` (Koperta) - run_id, sciezka, stacja_aktualna, stacja_poprzednia, stan, pola_stacji, walidacja, relacje
- `Manifest` - indeks stacji, statusy, timestampy, checkpointy
- `StationOutput` - wyjscie stacji przekazywane przez agenta
- `ContractValidation` - wynik walidacji kontraktu wejscia stacji docelowej

### 3.3. envelope.py

Operacje na kopercie:

- `create_envelope(run_id, zamiar, sciezka)` - inicjalna koperta po `inicjuj`
- `update_station_fields(envelope, station, output)` - aktualizacja `pola_stacji.<station>`
- `accumulate_state(envelope, station, output)` - kumulacja pol kluczowych w `stan`
- `validate_transition(envelope, target_station)` - walidacja przed przejsciem
- `compress_envelope(envelope, keep_last_n=3)` - kompresja w sciezce doglebny

### 3.4. checkpoint.py

- `save_checkpoint(run_id, station, envelope)` - zapis do `stan_NN_<station>.yaml`
- `load_checkpoint(run_id, station)` - odczyt checkpointu
- `list_checkpoints(run_id)` - lista dostepnych checkpointow
- `get_latest_checkpoint(run_id)` - ostatni zakonczony checkpoint

### 3.5. routing.py

Logika wyboru sciezki i kolejnosci stacji:

- `determine_path(klasyfikacja, stawka, ryzyko)` - wybor sciezki
- `get_station_sequence(path)` - kolejnosc stacji dla sciezki
- `get_next_station(current, path, gate_status)` - nastepna stacja
- `get_skipped_stations(path)` - stacje pomijane w sciezce

### 3.6. quality_gate.py

- `evaluate_gate(run_id, audit_status)` - ocena bramki
- `can_loop(iteration)` - czy mozna iterowac (max 2)
- `escalate(run_id, reason)` - eskalacja do uzytkownika
- `loop_back(run_id, target_station)` - powrot do dobierz/planuj

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

Integracja z Memgraph przez sterownik bolt:

- `write_run_node(run_id, zamiar)` - wezel Run
- `write_station_node(run_id, station, status)` - wezel Stacja
- `write_relation(source, target, rel_type, fields)` - krawedzie
- `validate_graph_continuity(run_id)` - walidacja ciaglosci grafu
- `audit_run_graph(run_id)` - zapytania audytowe (osierocone wezly, brakujace krawedzie)

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
   Serwer: zapisuje checkpoint stan_00_inicjuj.yaml
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

```
.ai-kb/pipeline-runs/
  <run_id>/
    manifest.yaml              # indeks stacji, statusy, sciezka, iteracja bramki
    stan_00_inicjuj.yaml       # checkpoint po inicjuj
    stan_01_zmienne.yaml       # checkpoint po zmienne
    stan_02_analiza.yaml
    stan_03_dekompozycja.yaml  # tylko sciezka doglebny
    stan_04_dobierz.yaml
    stan_04_dobierz_iter1.yaml # checkpoint po 1. iteracji bramki
    stan_05_routing.yaml       # tylko sciezka doglebny
    stan_06_planuj.yaml
    stan_07_realizuj.yaml
    stan_08_weryfikacja.yaml
    stan_09_sprawdzenie.yaml
    stan_10_ewaluacja.yaml     # tylko sciezka doglebny
    stan_11_utrwal.yaml
    stan_12_monitoruj.yaml     # tylko sciezka doglebny
    envelope_final.yaml        # ostateczna koperta po zamknieciu
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
