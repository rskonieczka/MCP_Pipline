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
