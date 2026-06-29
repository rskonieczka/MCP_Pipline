# Konfiguracja i instalacja

## 1. Wymagania

- Python >= 3.11
- `uvx` (dostepne w systemie, czesto przez `uv`)
- Opcjonalnie: Memgraph dla warstwy grafowej
- Opcjonalnie: klucz API LLM dla trybu auto-pilot

## 2. Instalacja

### 2.1. Przez uvx (rekomendowane)

```json
{
  "mcpServers": {
    "pipeline": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/EVILLAGE/pipeline-mcp",
        "pipeline-mcp"
      ],
      "env": {
        "PIPELINE_RUNS_DIR": "${HOME}/.local/share/pipeline-mcp/runs",
        "PIPELINE_AUTO_PILOT": "false"
      }
    }
  }
}
```

### 2.2. Lokalnie z katalogu projektu (development)

```json
{
  "mcpServers": {
    "pipeline": {
      "command": "python",
      "args": ["-m", "pipeline_mcp"],
      "cwd": "/home/swami/Projekty/EVILLAGE/AI_MCP/Pipline",
      "env": {
        "PIPELINE_RUNS_DIR": "./.ai-kb/pipeline-runs",
        "PIPELINE_AUTO_PILOT": "false"
      }
    }
  }
}
```

### 2.3. Przez pip (lokalna instalacja)

```bash
cd /home/swami/Projekty/EVILLAGE/AI_MCP/Pipline
pip install -e .
```

```json
{
  "mcpServers": {
    "pipeline": {
      "command": "pipeline-mcp",
      "env": {
        "PIPELINE_RUNS_DIR": "${HOME}/.local/share/pipeline-mcp/runs"
      }
    }
  }
}
```

## 3. Konfiguracja w Devin

Plik konfiguracyjny Devina: `~/.config/devin/mcp_config.json`.

Dodaj serwer `pipeline` do sekcji `mcpServers`:

```json
{
  "mcpServers": {
    "pipeline": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/EVILLAGE/pipeline-mcp", "pipeline-mcp"],
      "env": {
        "PIPELINE_RUNS_DIR": "/home/swami/Projekty/EVILLAGE/AI_MCP/Pipline/.ai-kb/pipeline-runs",
        "PIPELINE_AUTO_PILOT": "false",
        "PIPELINE_LLM_PROVIDER": "openai",
        "PIPELINE_LLM_MODEL": "gpt-4o",
        "PIPELINE_LLM_API_KEY": "${OPENAI_API_KEY}",
        "MEMGRAPH_URL": "bolt://localhost:7687"
      }
    }
  }
}
```

Po dodaniu restart Devina/Windsurf.

## 4. Zmienne srodowiskowe

### 4.1. Podstawowe

| Zmienna | Wartosc domyslna | Opis |
|---|---|---|
| `PIPELINE_RUNS_DIR` | `./.ai-kb/pipeline-runs` | Katalog persystencji run'ow |
| `PIPELINE_AUTO_PILOT` | `false` | Czy auto-pilot domyslnie wlaczony |
| `PIPELINE_LOG_LEVEL` | `INFO` | Poziom logowania (`DEBUG` \| `INFO` \| `WARNING` \| `ERROR`) |

### 4.2. LLM (auto-pilot)

| Zmienna | Wartosc domyslna | Opis |
|---|---|---|
| `PIPELINE_LLM_PROVIDER` | `openai` | `openai` \| `anthropic` \| `local` |
| `PIPELINE_LLM_MODEL` | `gpt-4o` | Model LLM |
| `PIPELINE_LLM_API_KEY` | - | Klucz API (z env lub pliku) |
| `PIPELINE_LLM_BASE_URL` | - | URL dla dostawcy lokalnego (np. `http://localhost:11434/v1`) |
| `PIPELINE_LLM_MAX_TOKENS` | `4096` | Max tokenow wyjscia |
| `PIPELINE_LLM_SYSTEM_PROMPT` | wbudowany | System prompt |

### 4.3. Memgraph (opcjonalne)

| Zmienna | Wartosc domyslna | Opis |
|---|---|---|
| `MEMGRAPH_URL` | `bolt://localhost:7687` | URL polaczenia Memgraph |
| `MEMGRAPH_USER` | - | Uzytkownik |
| `MEMGRAPH_PASSWORD` | - | Haslo |
| `PIPELINE_MEMGRAPH_ENABLED` | `true` | Czy zapis do Memgraph wlaczony |

## 5. Uruchomienie Memgraph (opcjonalne)

```bash
cd ~/.local/share/memgraph/
docker compose up -d
```

Sprawdzenie polaczenia:

```bash
echo "RETURN 1;" | cypher-shell -a bolt://localhost:7687
```

Jesli Memgraph niedostepny, serwer kontynuuje bez zapisu grafu (ostrzezenie w statusie).

## 6. Konfiguracja LLM (auto-pilot)

### 6.1. OpenAI

```bash
export PIPELINE_LLM_PROVIDER=openai
export PIPELINE_LLM_MODEL=gpt-4o
export PIPELINE_LLM_API_KEY=sk-...
```

### 6.2. Anthropic

```bash
export PIPELINE_LLM_PROVIDER=anthropic
export PIPELINE_LLM_MODEL=claude-sonnet-4-20250514
export PIPELINE_LLM_API_KEY=sk-ant-...
```

### 6.3. Lokalny (Ollama)

```bash
# Uruchom Ollama
ollama serve

# Skonfiguruj
export PIPELINE_LLM_PROVIDER=local
export PIPELINE_LLM_MODEL=llama3
export PIPELINE_LLM_BASE_URL=http://localhost:11434/v1
```

## 7. Weryfikacja instalacji

Po konfiguracji restart Devina/Windsurf i sprawdz dostepnosc narzedzi:

```
Agent powinien widziec narzedzia:
- start_run
- get_run_status
- list_runs
- execute_station
- get_next_station
- get_station_contract
- get_envelope
- quality_gate
- save_checkpoint
- auto_pilot_start
- ...
```

Testowy run:

```python
# W konwersacji z agentem:
start_run(zamiar="Test instalacji")
# -> powinno zwrocic run_id i first_station="inicjuj"
```

## 8. Struktura katalogow po instalacji

```
<PIPELINE_RUNS_DIR>/
  2026-06-29-test-instalacji/
    manifest.yaml
    stan_00_inicjuj.yaml
    ...
```

## 9. Rozwiazywanie problemow

### 9.1. Serwer nie widoczny w Devin

- Sprawdz skladnie JSON w `mcp_config.json`
- Restart Devina/Windsurf po zmianie konfiguracji
- Sprawdz logi: `~/.config/devin/logs/`

### 9.2. Blad `uvx: command not found`

```bash
# Zainstaluj uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 9.3. Blad `LLM_NOT_CONFIGURED`

- Ustaw `PIPELINE_LLM_API_KEY` w env
- Lub ustaw `PIPELINE_AUTO_PILOT=false` i uzywanie trybu manual

### 9.4. Blad `MEMGRAPH_UNAVAILABLE`

- Uruchom Memgraph: `docker compose up -d` w `~/.local/share/memgraph/`
- Lub ustaw `PIPELINE_MEMGRAPH_ENABLED=false`

### 9.5. Blad `CONTRACT_INCOMPLETE`

- Sprawdz `get_station_contract` dla stacji docelowej
- Uzupelnij brakujace pola przez `update_envelope`
- Lub wywolaj `execute_station` z kompletnym wyjsciem
