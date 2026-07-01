# Decyzje i pułapki

## Decyzje architektoniczne

### D1: Python z FastMCP zamiast TypeScript

**Dlaczego**: Spojnosc z istniejacym stackiem MCP uzytkownika (Serena, Memgraph, codebase-memory-mcp - wszystkie Python/uvx). FastMCP jest dojrzałym frameworkiem MCP dla Pythona.

**Alternatywy odrzucone**: TypeScript (npx) - mniej spojny z Serena/Memgraph.

### D2: Orkiestracja hybrydowa

**Dlaczego**: Aktywny sterownik (serwer prowadzi agenta przez stacje) z mozliwoscia recznego nadpisania (wywolanie od srodkowej stacji, restart, powrot bramki). Najwieksza elastycznosc dla zarowno automatyzacji jak i interwencji.

**Alternatywy odrzucone**: Pasywny koordynator (agent sam decyduje o kolejnosci - za malo rygoru), pelny sterownik aktywny (zbyt sztywny).

### D3: Pliki YAML zamiast SQLite

**Dlaczego**: Zgodnosc z specyfikacja `pipeline_sklills.md`. Czytelne dla czlowieka, diff-friendly, audytowalne bez narzedzi. Spojnosc z istniejaca specyfikacja.

**Alternatywy odrzucone**: SQLite (szybsze zapytania, ale mniej czytelne), hybryda YAML+SQLite (najwiecej pracy, zlozonosc).

### D4: Stan + opcjonalne LLM

**Dlaczego**: Dwa tryby - manual (agent steruje, serwer zaradza stanem) i auto-pilot (serwer wywoluje LLM per stacja). Umozliwia zarowno interaktywna prace z agentem jak i pelna automatyzacje.

**Alternatywy odrzucone**: Tylko stan (bez auto-pilota - ogranicza automatyzacje), pelne LLM (zbyt duza zaleznosc od API, koszty).

### D5: Serwer w pelni samodzielny (self-contained)

**Dlaczego**: Skille, kontrakty i specyfikacja wbudowane w pakiet. Serwer mozna uruchomic na dowolnej maszynie bez kopiowania katalogow skilli. Brak zaleznosci od `/etc/windsurf/skills/`.

**Alternatywy odrzucone**: Czytanie skilli z systemu plikow uzytkownika (zaleznosc zewnetrzna, brak spojnosci wersji).

### D6: Lokalne dzialanie w VSCode

**Dlaczego**: Agent (Devin/Windsurf) dziala lokalnie w VSCode. Serwer uruchamiany przez uvx lub python -m, polaczenie stdio. Zadnych zdalnych serwisow poza opcjonalnym Memgraph i API LLM.

### D7: PIPELINE_RUNS_DIR wzgledne wzgledem workspace

**Dlaczego**: Serwer ma dzialac dla wielu projektow. `PIPELINE_RUNS_DIR=.ai-kb/pipeline-runs` (wzgledna) rozwiazywana wzgledem workspace wykrytego z położenia editable-install pakietu (`_detect_workspace()` w `config.py`): dla editable install struktura to `<workspace>/src/pipeline_mcp/<plik>`, więc workspace = `Path(__file__).parents[2]` (potwierdzone istnieniem `pyproject.toml`). Fallback do `os.getcwd()` przy instalacji systemowej. Dodatkowo kazde narzedzie MCP ma opcjonalny parametr `workspace` do nadpisania.

**Dlaczego autodetekcja, nie `cwd` w mcp_config.json**: Windsurf i Devin **NIE** ustawiaja cwd na workspace automatycznie - proces MCP dziedziczy cwd po rodzicu (zwykle `~`). Hardcodowane `cwd` w globalnym `mcp_config.json` znaczyloby, że wszystkie projekty pisza do jednego katalogu (łamie wieloprojektowosc). Autodetekcja z `__file__` pozwala jednemu wpisowi MCP obslugiwac wiele workspace'ow, bo workspace jest wnioskowany z położenia kodu pakietu, nie z cwd procesu.

**Wymog**: W kazdym projekcie, w ktorym pipeline ma byc uzywany, pakiet musi byc zainstalowany editable (`pip install -e <sciezka_do_Pipline>`) w `.venv` tego projektu, a wpis MCP musi wskazywac ten `.venv`. Wowczas `_detect_workspace()` poprawnie zwroci ten workspace.

**Alternatywy odrzucone**: Sztywna sciezka absolutna w `PIPELINE_RUNS_DIR` (jedna per serwer - nie obsluguje wielu projektow), hardcodowane `cwd` w globalnym `mcp_config.json` (lamie wieloprojektowosc - wszystkie runy z kazdego projektu trafilyby do jednego katalogu), zmienna srodowiskowa per workspace (wymaga restartu serwera przy zmianie projektu).

### D8: Auto-inicjalizacja przez prompt MCP

**Dlaczego**: Uzytkownik nie musi jawnie wywolywac `start_run`. Serwer udostepnia prompt MCP `pipeline_start`, ktory automatycznie wywoluje `start_run` i zwraca instrukcje do pierwszej stacji. Drugi prompt `pipeline_continue` wznawia istniejacy run. Dodatkowo serwer wysyla `instructions` do agenta przy polaczeniu, ktore opisuja jak uzywac pipeline'u.

**Alternatywy odrzucone**: Lifespan hook (brak zamiaru przy starcie serwera), auto-run w execute_station (zamiar niejawny, trudny do audytu), instrukcje bez promptu (agent nadal musi jawnie wywolywac start_run).

## Pułapki

### P1: Aktualizacja skilli wymaga aktualizacji pakietu

Wbudowane skille sa kopia oryginalow. Aktualizacja skilli w `/etc/windsurf/skills/` nie aktualizuje automatycznie serwera. Nalezy skopiowac zaktualizowane skille do `src/pipeline_mcp/skills/` i przebudowac pakiet.

### P2: Parsowanie wyjscia LLM w auto-pilocie

Auto-pilot wymaga, by LLM zwracal blok `KOPERTA:` w formacie YAML. Jesli LLM nie zachowa formatu, parsowanie sie nie powiedzie. Serwer zatrzymuje auto-pilot z bledem `LLM_OUTPUT_PARSE_ERROR`. Wymaga uszczelnienia promptu stacji.

### P3: Memgraph opcjonalny ale zalecany

Bez Memgraph serwer kontynuuje bez zapisu grafu, ale traci audytowalnosc relacyjna. Skill `audyt_runu` nie zadziala bez Memgraph.

### P4: Bramka jakosci max 2 iteracje

Po 2 nieudanych iteracjach bramki serwer eskaluje do uzytkownika. Auto-pilot zostaje zatrzymany. Wymaga interwencji ludzkiej.

### P5: Kompresja kontekstu w sciezce doglebny

W dlugich pipeline'ach (13 stacji) serwer kompresuje koperte, usuwajac starsze sekcje `pola_stacji`. Pelne dane pozostaja w checkpointach. Agent musi byc swiadomy, ze nie widzi pelnej historii w kontekscie.

### P6: Konflikty wersji skilli

Jesli skille w `/etc/windsurf/skills/` zostana zaktualizowane, a serwer nie, wbudowane skille serwera beda nieaktualne. Nalezy okresowo synchronizowac.

### P7: Kierunek relacji NASTAPILA_PO

Relacja `NASTAPILA_PO` ma kierunek **(stacja aktualna) -> (stacja poprzednia)**, nie odwrotnie. Blad w kierunku powoduje bledne wyniki zapytan audytowych (stacja `inicjuj` z relacja wychodzaca, `monitoruj` bez relacji). Naprawione w `envelope.py` po audycie run'u `2026-07-01-analiza-projektu-i`.

### P8: Deduplikacja relacji w kopercie

`add_station_relations` w `envelope.py` wywolane wielokrotnie dla tej samej stacji (np. przy powrocie bramki) dodawalo duplikaty relacji `ZAWIERA` i `NASTAPILA_PO`. Dodano sprawdzenie `in envelope.relacje` przed append.

### P9: Etykiety wezlow encji w Memgraph

`_label_for_id` w `memgraph.py` obsluguje 12 prefiksow id (run, stacja, zmienna, podproblem, decyzja, krok, zmiana, twierdzenie, werdykt, wymiar, wniosek, checkpoint). Bez tego wezly encji tworzone byly bez labela, uniemozliwiajac zapytania audytowe.

### P10: Sciezka i timestamp_end w wezle Run

`write_run_node` wywolywane po stacji `inicjuj` aktualizuje `sciezka` z manifestu (nie hardcoded 'pelny'). `close_run_node` przyjmuje `timestamp_end` z manifestu.
