# Audyt kodu pipeline-mcp (02-07-2026)
Pelny audyt src/pipeline_mcp; hipotezy potwierdzone smoke-testami (izolowany venv, /tmp).

## High
1. Petla bramki nie dziala: po gate=powrot execute_station(loop_target) rzuca StationAlreadyDoneError (server.py ~402); get_next_station/resume_run po powrocie wskazuja 'utrwal' zamiast stacji petli; brak checkpointow _iterN i statusu 'zablokowany' przy eskalacji (rozbieznosc z docs/05).
2. Kolizja run_id (ten sam dzien+3 slowa zamiaru) nadpisuje manifest istniejacego runu; brak sanityzacji '/' w run_id (zagniezdzone katalogi, run niewidoczny w list_runs).
3. Auto-pilot martwy: start_auto_pilot tylko ustawia stan w pamieci; petla z docs/07 niezaimplementowana; execute_station_with_llm nigdy nie wywolywane.

## Medium
4. memgraph.write_relation: galaz else bez f-stringa -> 'MERGE (a {{id...}})' blad Cypher; wezly bez prefiksu z _LABEL_MAP nie zapisuja sie.
5. Cypher injection przez rel_type (f-string, brak whitelisty).
6. Wezly Stacja bez run_id w id - wspoldzielone miedzy runami, graf przeklamany.
7. Eskalacja bramki nie ustawia status_runu='zablokowany'.
8. start_run ignoruje kontekst/zrodla/tryb_inicjacji.
9. get_post_gate_station('szybki')->'utrwal' i infer_loop_target->'planuj' spoza sciezki szybkiej.

## Low
10. Literowka 'eskylacja' (models, quality_gate, docs 02/05/07).
11. contracts.py:141 martwy kod ValidationStatus.WNISKOWANE.
12. skip_validation = re-execute (mylaca nazwa), brak walidacji wejscia stacji.
13. close_run bez _ensure_run_open.
14. Martwy kod: _load_run, compress_envelope, validate_graph_continuity, get_pipeline_spec/contracts_spec.
15. auto_pilot_start ignoruje workspace.
16. int(PIPELINE_LLM_MAX_TOKENS) crash na nie-liczbie.
17. Brak tests/, __pycache__ w git, brak .gitignore.

Naprawy: P1 petla bramki, P2 run_id, P3 auto-pilot, P4 memgraph, P5 reszta.