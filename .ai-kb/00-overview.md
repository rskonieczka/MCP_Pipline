# Pipeline MCP Server - Przeglad

## Cel projektu

Samodzielny serwer MCP orkiestrujacy dzialanie agentow AI w petli pipeline. Serwer jest w pelni self-contained - zawiera wbudowane skille 13 stacji, kontrakty I/O i specyfikacje pipeline'u.

## Kontekst

- **Lokalizacja**: `/home/swami/Projekty/EVILLAGE/AI_MCP/Pipline/`
- **Jezyk**: Python 3.11+ z FastMCP
- **Dystrybucja**: uvx lub python -m
- **Srodowisko**: lokalne w VSCode (Devin/Windsurf), polaczenie stdio
- **Persystencja**: pliki YAML w `.ai-kb/pipeline-runs/`
- **Graf**: opcjonalnie Memgraph przez bolt://localhost:7687

## Zrodlo pochodzenia

Serwer zmaterializuje pipeline umiejetnosci z `/etc/windsurf/skills/`. Skille zostaly skopiowane do `src/pipeline_mcp/skills/` jako wbudowane zasoby pakietu. Serwer nie zalezy od zewnetrznego katalogu skilli.

## Decyzje architektoniczne

1. **Jezyk**: Python (FastMCP/uvx) - spojnosc z Serena, Memgraph, codebase-memory-mcp
2. **Orkiestracja**: hybrydowa - aktywny sterownik z mozliwoscia recznego nadpisania
3. **Persystencja**: pliki YAML (jak w specyfikacji pipeline'u)
4. **Zakres logiki**: stan + opcjonalne LLM (tryb manual + auto-pilot)
5. **Samodzielnosc**: skille, kontrakty i specyfikacja wbudowane w pakiet

## Stany pipeline'u

13 stacji: inicjuj, zmienne, analiza, dekompozycja, dobierz, routing, planuj, realizuj, weryfikacja, sprawdzenie, ewaluacja, utrwal, monitoruj, audyt_runu.

3 sciezki: szybki (5 stacji), pelny (9 stacji), doglebny (13 stacji).

Bramka jakosci po `sprawdzenie` z max 2 iteracjami i eskalacja.

RTM (Requirements Traceability Matrix): automatyczne sledzenie wymagan przez pipeline. Ekstrakcja po stacji `zmienne`, aktualizacja statusow po `realizuj`/`weryfikacja`/`sprawdzenie`. 4 narzedzia MCP: `get_rtm`, `update_rtm`, `add_rtm_entry`, `validate_rtm_coverage`. Integracja z Memgraph (wezly :Wymaganie, relacje :ADRESUJE, :WERYFIKUJE).

## Status

- Faza: implementacja ukonczona, weryfikacja pozytywna, AUDYT CELU 2026-06-29: cel realizowany w pelni
- Audyt celu (run 2026-06-29-sprawdzenie-celu-projektu, sciezka doglebny): 14 werdyktow weryfikacji potwierdzonych, 0 obalonych, 2 braki dowodowe (auto-pilot z realnym LLM, Memgraph z realna baza - integracje opcjonalne). Ocena ogolna: wysoka. Wszystkie deklarowane komponenty celu potwierdzone w kodzie i testach funkcjonalnych.
- Implementacja kodu: 17 modulow Python, 26 narzedzi MCP
- Skille: 14 wbudowanych (13 stacji + audyt_runu), weryfikacja integralnosci OK
- Testy: start_run, execute_station, get_run_status, get_next_station, get_envelope, list_checkpoints, close_run, quality_gate (3 iteracje + eskalacja), get_gate_iterations, get_station_contract, list_stations, verify_integrity, stdio protocol - wszystkie PASS. Testy RTM: test_rtm (38 testow: model RTMEntry, ekstrakcja, auto-aktualizacja, walidacja pokrycia, narzedzia MCP, E2E, kompatybilnosc wsteczna) - wszystkie PASS. Total: 55 testow PASS.
- Zaleznosci: fastmcp 3.4.2, pydantic 2.13.4, pyyaml 6.0.3, neo4j 6.2.0, openai 2.44.0, anthropic 0.113.0
- Venv: .venv/ z instalacja -e ".[all]"
- Uruchomienie: .venv/bin/python -m pipeline_mcp.server (stdio MCP)
