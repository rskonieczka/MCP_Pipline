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

### D9: Requirements Traceability Matrix (RTM) jako modul + narzedzia MCP

**Dlaczego**: Pipeline orkiestrowal 13 stacji bez formalnego sledzenia wymagan uzytkownika. RTM mapuje wymagania (ekstrahowane z `variables` typu `requirement` po stacji `zmienne`) na stacje adresujace, weryfikujace i artefakty. Automatyczna aktualizacja statusow po `realizuj`/`weryfikacja`/`sprawdzenie` zapewnia traceability bez dodatkowego obciazenia agenta. 4 narzedzia MCP (`get_rtm`, `update_rtm`, `add_rtm_entry`, `validate_rtm_coverage`) pozwalaja na reczna interwencje. Integracja z Memgraph (wezly `:Wymaganie`, relacje `:ADRESUJE`, `:WERYFIKUJE`) zapewnia audytowalnosc grafowa.

**Alternatywy odrzucone**: Nowa stacja `rtm` (lamie definicje 3 sciezek, wszystkie kontrakty, zbyt inwazyjne), tylko pole w Envelope bez narzedzi (pasywne, brak walidacji pokrycia, brak integracji z Memgraph).

### D10: Wieloklientowosc (multi-tenant) przez izolacje katalogowa + client_id w node IDs

**Dlaczego**: Serwer mial obslugiwac wielu klientow w jednym workspace bez mieszania danych. Izolacja katalogowa (`.ai-kb/clients/<client_id>/pipeline-runs/`) jest prostsza niz izolacja w bazie i zachowuje kompatybilnosc wstecz (tryb legacy gdy `client_id=""`). Kazde narzedzie MCP przyjmuje opcjonalny `client_id`; hierarchia rozwiazywania: jawny parametr -> aktywny klient sesji (`set_active_client`) -> `PIPELINE_DEFAULT_CLIENT_ID` -> tryb legacy. W Memgraph `client_id` jest wbudowane w ID wezlow (`run:<client_id>:<run_id>`, `stacja:<client_id>:<run_id>:<station>`, `wymaganie:<client_id>:<run_id>:<req_id>`, `pamiec:<client_id>:<memory_id>`) - zapobiega kolizjom miedzy klientami przy tym samym `run_id`. Wiedza wspoldzielona (`shared-knowledge/`) i pamiec wspoldzielona sa oznaczone `client_id="shared"`.

**Zakres**: 4 nowe moduly (`client_registry.py`, `client_memory.py`, `knowledge.py`, `rag.py`), 23 nowe narzedzia MCP w 4 grupach (klienci, wiedza wspoldzielona, pamiec per-klient, RAG per-klient), nowe modele (`ClientContext`, `ClientMatch`, `ResolveResult`, `ClientMemoryEntry`, `SharedKnowledgeEntry`), nowe env vars (`PIPELINE_DEFAULT_CLIENT_ID`, `PIPELINE_WORKSPACE`), `client_id` we wszystkich istniejacych narzedziach. Rejestr klientow z 6-warstwowym dopasowaniem (L1-L6: client_id, external_id, alias, id_fragment, fuzzy_name, brak). `delete_client` usuwa pliki i wezly Memgraph (GDPR).

**Alternatywy odrzucone**: Izolacja przez osobne workspace'y (wymaga restartu serwera przy zmianie klienta), izolacja w SQLite zamiast plikow (lamie zasade D3 - YAML jako format persystencji), brak izolacji w Memgraph (kolizje node IDs przy tym samym run_id miedzy klientami - wykryte w audycie jako F1).

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

`_label_for_id` w `memgraph.py` obsluguje 13 prefiksow id (run, stacja, zmienna, podproblem, decyzja, krok, zmiana, twierdzenie, werdykt, wymiar, wniosek, checkpoint, wymaganie). Bez tego wezly encji tworzone byly bez labela, uniemozliwiajac zapytania audytowe.

### P10: Sciezka i timestamp_end w wezle Run

`write_run_node` wywolywane po stacji `inicjuj` aktualizuje `sciezka` z manifestu (nie hardcoded 'pelny'). `close_run_node` przyjmuje `timestamp_end` z manifestu.

### P11: RTM false-positive przy pustym opisie (U1, naprawione 2026-09-09)

`_update_after_realizuj` i `_update_after_weryfikacja` w `rtm.py` dopasowywaly wymagania przez `entry.opis.lower() in tekst`. Pusty opis (`""`) powoduje, ze `"" in dowolny_tekst` zwraca `True` - wszystkie wymagania z pustym opisem byly false-positive oznaczane jako `zrealizowane`/`weryfikowane`. Naprawa: dodano warunek `and entry.opis` przed dopasowaniem.

### P12: compress_envelope byl martwym kodem (U2, naprawione 2026-09-09)

`compress_envelope` w `envelope.py` byl zdefiniowany ale nigdy niewywolywany. Dokumentacja deklarowala kompresje w sciezce doglebny po stacjach `analiza`, `dobierz`, `sprawdzenie`. Naprawa: dodano wywolanie w `execute_station` w `server.py` po zapisie checkpointu. Kompresja dotyczy koperty w kontekscie konwersacji (zwracanej w `envelope_summary`), pelne dane zostaja w checkpointach.

### P13: routing ignorowany (U3, naprawione 2026-09-09)

Stacja `routing` w sciezce doglebny byla dekoracyjna - jej wyjscie `sciezka` nie nadpisywalo sciezki wybranej przez `inicjuj`. `determine_path` w `execute_station` przekazywal tylko `klasyfikacja`, ignorujac `stawka` i `ryzyko`. Naprawa: po stacji `routing` w `execute_station` nadpisujemy `envelope.sciezka` i `manifest.sciezka` z `output["sciezka"]` jesli obecnosc i jest poprawna.

### P14: Podwojny limit bramki w auto-pilocie (U5, naprawione 2026-09-09)

`auto_pilot_start` w `server.py` mial wlasny licznik `gate_returns` sprawdzajacy `gate_returns > max_gate_iterations`, niezaleznie od `quality_gate`/`evaluate_gate` zarzadzajacego `iteracja_bramki` w manifeście. To tworzylo dwie mechaniki limitu, ktore mogly sie rozminac. Naprawa: usunieto `gate_returns`, polegamy wylacznie na `quality_gate` (gate_decision == "eskalacja").

### P15: get_gate_history zwracal pusta historie (U4, naprawione 2026-09-09)

`get_gate_history` w `quality_gate.py` zwracal `historia: []` z komentarzem `TODO: sledzenie historii w przyszlosci`. Naprawa: dodano `GateHistoryEntry` do `models.py`, `historia_bramki` do `Manifest`, zapis historii w `evaluate_gate` dla kazdej decyzji (przejdz/powrot/eskalacja).

### P16: stacja_weryfikujaca nadpisywane przy niespelnieniu (U6, naprawione 2026-09-09)

`_update_after_sprawdzenie` w `rtm.py` przy wymiarze `Zgodnosc=niezgodny` ustawial `entry.stacja_weryfikujaca = "sprawdzenie"`, nadpisujac wczesniejsza wartosc `"weryfikacja"`. Tracilismy informacje o pierwotnej weryfikacji. Naprawa: dodano pole `stacja_niespelnienia` do `RTMEntry`, nie nadpisujemy `stacja_weryfikujaca`.

### P17: Brak walidacji audit_status (U7, naprawione 2026-09-09)

`quality_gate` przyjmowal dowolny string jako `audit_status`. Tylko `"zgodny"` wyzwalal przejscie; wszystko inne (literowka, `None`, pusty string) bylo traktowane jako niezgodny. Naprawa: dodano walidacje `audit_status in ("zgodny", "niezgodny")` w `evaluate_gate`, rzucanie `PipelineError` przy nieprawidlowej wartosci.

### P18: _wejscie w pola_stacji (U8, naprawione 2026-09-09)

`start_run` zapisywal wejscie uzytkownika jako `pola_stacji["_wejscie"]`. To nie jest nazwa stacji - `compress_envelope` moglby je usunac jako najstarszy. Naprawa: dodano pole `wejscie` do `Envelope` w `models.py`, przeniesiono zapis z `pola_stacji["_wejscie"]` do `envelope.wejscie`.

### P19: Parser KOPERTA wymagal indentacji kazdej linii (U9, naprawione 2026-09-09)

`parse_llm_output` w `auto_pilot.py` uzywal regex `r"KOPERTA:\s*\n((?:[ \t].*\n)*)"` wymagajacego indentacji kazdej linii po `KOPERTA:`. Pusta linia bez indentacji przerywala parsowanie, powodujac fallback do `_raw_output` i blokowanie auto-pilota. Naprawa: zmieniono na tolerancyjny regex z `re.DOTALL` i automatyczna indentacja linii.

### P20: Kolizja ID wezlow Memgraph miedzy klientami (F1, naprawione 2026-09-10)

ID wezlow grafu (`run:<run_id>`, `stacja:<run_id>:<station>`, `wymaganie:<run_id>:<req_id>`, `pamiec:<memory_id>`) nie zawieraly `client_id`. Poniewaz `_unique_run_id` sprawdza unikalnosc tylko wewnatrz katalogu klienta, dwaj klienci mogli miec ten sam `run_id`. MERGE dopasowywalo wezel drugiego klienta i nadpisywalo jego `client_id`, `zamiar`, `status`. `close_run_node` nie przyjmowalo `client_id` - zamykalo wezel innego klienta. Naprawa: helpery `_run_node_id`, `_station_node_id`, `_req_node_id` dolaczaja `client_id` do ID (legacy gdy puste). `pamiec:{effective_client_id}:{memory_id}` zawsze izolowane. `close_run_node` przyjmuje `client_id`. `add_station_relations` w `envelope.py` uzywa helperow.

### P21: Ciche nadpisywanie pamieci przy kolizji tematu (F2, naprawione 2026-09-10)

`save_client_memory` i `save_shared_memory` auto-generowaly `memory_id` z tematu (`re.sub(...)[:50]`). Dwa zapisy z tym samym tematem (ale rozna tresc) generowaly ten sam `memory_id` - drugi nadpisywal plik pierwszego bez ostrzezenia. Naprawa: `_unique_memory_id(base, path)` przy auto-generowanym ID i istniejacym pliku dolacza timestamp. Jawny `memory_id` zachowuje semantyke upsert.

### P22: Nieatomowe zapisy plikow YAML (F3, naprawione 2026-09-10)

`client_memory.py`, `knowledge.py`, `client_registry.py` zapisywaly pliki przez `open(path, "w")` + `yaml.dump` - nieatomowo. Przerwanie procesu (kill, crash) pozostawialo skrocony/uszkodzony plik YAML. `rag.py` mial juz atomowy wzorzec (`tempfile.mkstemp` + `os.replace`). Naprawa: dodano `_atomic_yaml_dump(path, data)` w `client_memory.py` i `knowledge.py`, przepisano `client_registry._save_client` na atomowy wzorzec.

### P23: start_run bez walidacji istnienia klienta (F4, naprawione 2026-09-10)

`start_run` przyjmowal `client_id` i tworzyl katalog `clients/<client_id>/pipeline-runs/` bez sprawdzania czy klient jest zarejestrowany. Powstawaly osierocone katalogi dla niezarejestrowanych klientow - niewidoczne w `list_clients`, niezarzadzalne przez `update_client`/`archive_client`/`delete_client`. Naprawa: gdy `cid` niepuste, `start_run` sprawdza `client_registry.load_client(cid, ws)` i rzuca `ClientNotFoundError` gdy nie istnieje. Tryb legacy (cid puste) nie wymaga rejestracji.

### P24: delete_client nie czyscil wezlow Memgraph (F5, naprawione 2026-09-10)

`delete_client` usuwal pliki z dysku (`shutil.rmtree`) ale nie usuwal wezlow Run, Stacja, Wymaganie, Pamiec z Memgraph. Docstring deklarowal "GDPR right to be forgotten" ale dane grafu pozostawaly. Naprawa: dodano `memgraph.delete_client_nodes(client_id)` wykonujace `MATCH (n) WHERE n.client_id = $client_id AND n.client_id <> 'shared' DETACH DELETE n`. Wywolywane w `delete_client` przed `shutil.rmtree`. Wynik zwracany w polu `memgraph_deleted`. Poprawiono tez liczenie `run_count` - tylko katalogi (`d.is_dir()`), nie pliki.

### P25: Nieograniczony wzrost _index_locks w rag.py (F6, naprawione 2026-09-10)

`_index_locks` w `rag.py` byl slownikiem modulowym, do ktorego dodawano nowy `threading.Lock` dla kazdej unikalnej sciezki indeksu. Locki nigdy nie byly usuwane - wyciek pamieci w dlugiej sesji z wieloma klientami/workspace'ami. Naprawa: zmieniono na `weakref.WeakValueDictionary` - locki automatycznie zwalniane gdy nie sa uzywane (GC zbiera obiekty bez silnych referencji).

### P26: close_run_node i write_relations_from_envelope bez client_id (F7, naprawione 2026-09-10)

`close_run_node` nie przyjmowalo `client_id` - MERGE dopasowywalo wezel niezaleznie od klienta. `write_relations_from_envelope` przekazywalo `rel.zrodlo`/`rel.cel` z koperty, ktore nie zawieraly `client_id`. Powiazane z P20 - po dodaniu `client_id` do ID wezlow, te funkcje musialy tez go przekazywac. Naprawa: `close_run_node` przyjmuje `client_id` (wywolanie w `server.py` przekazuje `manifest.client_id`), `add_station_relations` w `envelope.py` konstruuje node IDs z `envelope.client_id` przez helpery.
