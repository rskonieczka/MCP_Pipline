# Współdzielone: Źródła prawdy i narzędzia lokalne

Kanoniczna wersja sekcji `Źródła prawdy` i `Narzędzia lokalne` dla wszystkich skilli w `/etc/windsurf/skills/`. Pliki SKILL.md zawierają kompaktową listę z referencją do tego pliku.

Aktualizacja tabel i workflow w tym pliku wystarczy do zsynchronizowania wszystkich skilli.

## Źródła prawdy

1. Dokumentacja projektu w `.ai-kb` - architektura, konwencje, decyzje i pułapki projektu.
2. Context7 - oficjalna dokumentacja bibliotek, frameworków i zewnętrznych API.
3. notebooklm-mcp - uzupełnianie braków z notebooków i źródeł badawczych użytkownika.
4. Memgraph MCP - warstwa grafowa: relacje między encjami, mapa zależności, graf wywołań, analiza architektury przez Cypher.

### Hierarchia i konflikty źródeł

Stosuj źródła w podanej kolejności; niższe poziomy uruchamiaj dopiero, gdy wyższe nie dają odpowiedzi.

Gdy źródła się sprzeczają:
- dla faktów projektu (architektura, konwencje, decyzje) pierwszeństwo ma `.ai-kb`,
- dla składni i API bibliotek oraz frameworków pierwszeństwo ma Context7,
- konflikt zgłaszaj użytkownikowi z propozycją aktualizacji starszego źródła.

## Narzędzia lokalne

### desktop-commander (pełne)

Do lokalnego przeszukiwania kodu źródłowego i plików bazy wiedzy (`.ai-kb`, `docs`) używaj `desktop-commander`.

Stosuj gdy:
- szukasz fragmentów kodu, symboli, wzorców lub wartości w plikach lokalnych,
- przeszukujesz katalogi projektu (grep, find, odczyt plików),
- sprawdzasz zawartość `.ai-kb` lub `docs` bez pełnego odczytu katalogu,
- Serena MCP jest niedostępna lub nie obsługuje danego typu pliku,
- parsujesz formaty binarne (PDF, DOCX, Excel, obrazy),
- utrzymujesz interaktywne sesje REPL lub długotrwałe procesy.

Nie używaj `desktop-commander` do dokumentacji zewnętrznych bibliotek - do tego służy Context7.

Narzędzia `desktop-commander` do lokalnego przeszukiwania:

| Narzędzie | Kiedy używać |
| --- | --- |
| `read_file` | odczytaj plik (wspiera offset/length do stronicowania) |
| `read_multiple_files` | odczytaj kilka plików równocześnie |
| `list_directory` | wylistuj zawartość katalogu |
| `get_file_info` | sprawdź metadane pliku (rozmiar, data modyfikacji) |
| `start_search` | wyszukaj pattern w plikach (odpowiednik grep/rg) |
| `get_more_search_results` | pobierz kolejną stronę wyników wyszukiwania |

Narzędzia `desktop-commander` do edycji plików (mutujące):

| Narzędzie | Kiedy używać |
| --- | --- |
| `edit_block` | edytuj fragment pliku przez old_string/new_string |
| `write_file` | zapisz plik (gdy brak dostępu przez standardowy edytor) |

Workflow przeszukiwania:
1. `list_directory` - sprawdź strukturę katalogu projektu lub `.ai-kb`
2. `start_search` - znajdź pattern, nazwę klasy lub fragment kodu
3. `read_file` z `offset`/`length` - odczytaj tylko istotny fragment dużego pliku
4. `get_file_info` - zweryfikuj datę modyfikacji przed edycją

### Memgraph MCP (warstwa grafowa)

Memgraph stanowi warstwę grafową uzupełniającą pamięć tekstową Serena. Służy do analizy relacji między encjami, mapy zależności, grafu wywołań i architektury przez Cypher. W kontekście pipeline'u umiejętności Memgraph przechowuje graf powiązań run'u (stacje, zmienne, decyzje, twierdzenia, werdykty, wnioski). Schemat grafu pipeline'u, mapowanie koperty na węzły/krawędzie, wzorcowe zapytania Cypher i reguły integralności: patrz `graf-pipeline.md`.

Stosuj gdy:
- analizujesz relacje między encjami i zależności między modułami,
- budujesz graf wywołań lub mapę zależności,
- potrzebujesz algorytmów grafowych (PageRank, betweenness centrality, sąsiedztwo węzła),
- weryfikujesz spójność architektury na poziomie powiązań.

Narzędzia Memgraph MCP:

| Narzędzie | Kiedy używać |
| --- | --- |
| `get_configuration` | sprawdź połączenie i konfigurację przed pierwszym użyciem |
| `list_databases` / `use_database` | wybierz aktywną bazę w sesji |
| `get_schema` | sprawdź schemat grafu przed zapytaniem |
| `run_query` | wykonaj zapytanie Cypher (odczyt/zapis) |
| `get_node_neighborhood` | znajdź węzły w zadanej odległości od węzła |
| `get_page_rank` / `get_betweenness_centrality` | analiza centralności węzłów |
| `get_procedures` | listuj dostępne procedury MAGE i moduły zapytań |
| `get_index` / `get_constraint` / `get_storage` / `get_triggers` | metadane grafu |

Workflow grafowy:
1. `get_configuration` - zweryfikuj połączenie z bazą
2. `get_schema` - sprawdź schemat przed zapytaniem
3. `run_query` - wykonaj Cypher dopasowany do pytania
4. W razie błędu połączenia wskaż konieczność uruchomienia bazy przez `docker compose up -d` w katalogu instalacji Memgraph (domyślnie `~/.local/share/memgraph/`, ścieżka zależy od instalacji).

Memgraph nie zastępuje Serena memory (wiedza deklaratywna) ani Context7 (dokumentacja zewnętrzna) - uzupełnia je o relacje i analizę strukturalną.
