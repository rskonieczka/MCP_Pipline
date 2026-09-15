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

Wieloklientowosc (multi-tenant): izolacja katalogowa `.ai-kb/clients/<client_id>/` dla run'ow, pamieci i RAG per-klient. Wiedza wspoldzielona w `.ai-kb/shared-knowledge/`. `client_id` propagowane przez wszystkie narzedzia, checkpointy, manifesty, koperte i Memgraph (wbudowane w ID wezlow). Rejestr klientow z 6-warstwowym dopasowaniem (L1-L6). 23 nowe narzedzia MCP w 4 grupach (klienci, wiedza, pamiec, RAG). Tryb legacy (brak `client_id`) zachowany dla kompatybilnosci wstecz.

## Status

- Faza: implementacja ukonczona, weryfikacja pozytywna, AUDYT CELU 2026-06-29: cel realizowany w pelni
- Audyt celu (run 2026-06-29-sprawdzenie-celu-projektu, sciezka doglebny): 14 werdyktow weryfikacji potwierdzonych, 0 obalonych, 2 braki dowodowe (auto-pilot z realnym LLM, Memgraph z realna baza - integracje opcjonalne). Ocena ogolna: wysoka. Wszystkie deklarowane komponenty celu potwierdzone w kodzie i testach funkcjonalnych.
- Audyt kodu wieloklientowego (2026-09-10): 7 usterek wykrytych (F1-F7), wszystkie naprawione. Kolizje node IDs Memgraph, ciche nadpisywanie pamieci, nieatomowe zapisy, brak walidacji klienta, brak czyszczenia Memgraph, wyciek pamieci lockow.
- Audyt dlugu implementacyjnego (2026-09-10, P30): 6 usterek wykrytych (D1-D6), wszystkie naprawione. Stan auto-pilota nieaktualizowany (stacje_pozostale, iteracja_bramki), wejscie tracone w kopercie, prompt pipeline_start bez zrodel, list_rag_documents bez metadanych, wyciek pamieci _auto_pilot_state.
- Audyt bezpieczenstwa i logiki (2026-09-15, P31): 4 bugi (A1-A4) + 9 dlugu (B1-B9) wykryte. Naprawione W1-W8: path traversal w parametrach sciezkotworczych (centralna walidacja segmentow), run'y legacy nieosiagalne przy aktywnym kliencie (resolve_run_dir z fallbackiem), quality_gate bez sprawdzenie, nieprawidlowy status RTM, checkpoint tools bez weryfikacji run'u, martwe mapowanie kontraktu, retry Memgraph z throttlem, stacje_pozostale po powrocie bramki.
- Implementacja kodu: 21 modulow Python, ~49 narzedzi MCP (26 bazowych + 23 wieloklientowych)
- Skille: 14 wbudowanych (13 stacji + audyt_runu), weryfikacja integralnosci OK
- Testy: start_run, execute_station, get_run_status, get_next_station, get_envelope, list_checkpoints, close_run, quality_gate (3 iteracje + eskalacja), get_gate_iterations, get_station_contract, list_stations, verify_integrity, stdio protocol - wszystkie PASS. Testy RTM: test_rtm (38 testow) - wszystkie PASS. Testy wieloklientowe: test_client_isolation (izolacja run'ow, pamieci, RAG, aktywny klient, kontrakt get_run_status, wspolbiezne indeksowanie 20 dokumentow, kolizje pamieci, walidacja klienta, czyszczenie Memgraph), test_client_registry (rejestr, aliasy, path traversal, dopasowanie, node IDs) - wszystkie PASS. Total: 131 testow PASS.
- Zaleznosci: fastmcp 3.4.2, pydantic 2.13.4, pyyaml 6.0.3, neo4j 6.2.0, openai 2.44.0, anthropic 0.113.0
- Venv: .venv/ z instalacja -e ".[all]"
- Uruchomienie: .venv/bin/python -m pipeline_mcp.server (stdio MCP)
