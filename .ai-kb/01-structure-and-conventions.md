# Struktura i konwencje

## Struktura katalogow

```
Pipline/
  README.md                    # Przeglad, instalacja, szybki start
  docs/                        # Dokumentacja architektoniczna
    01-architecture.md         # Architektura, komponenty, przeplyw danych
    02-tools-reference.md      # Referencja 26 narzedzi MCP
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

## Zaleznosci

- `fastmcp` - framework serwera MCP
- `pydantic` - modele danych
- `pyyaml` - persystencja YAML
- Opcjonalnie: `neo4j` (sterownik Memgraph)
- Opcjonalnie: `openai` / `anthropic` (dostawcy LLM dla auto-pilota)
