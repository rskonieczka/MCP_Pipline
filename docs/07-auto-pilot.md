# Tryb auto-pilot z LLM

Tryb auto-pilot umozliwia pelna automatyzacje pipeline'u. Serwer sam wywoluje LLM per stacja z odpowiednim promptem wbudowanego skilla, zapisuje checkpointy, obsluguje bramke jakosci.

## 1. Wymagania

Tryb auto-pilot wymaga:

- Skonfigurowanego dostawcy LLM (`PIPELINE_LLM_PROVIDER`, `PIPELINE_LLM_MODEL`, `PIPELINE_LLM_API_KEY`)
- Wbudowanych skillow stacji (czesc pakietu, zawsze dostepne)
- Dostepu do katalogu persystencji (zapis checkpointow)

Bez klucza API LLM tryb auto-pilot zwraca blad `LLM_NOT_CONFIGURED`. Tryb manual pozostaje dostepny.

## 2. Uruchomienie

```python
# 1. Utworz run
run = start_run(zamiar="Wdroz Filament 5.6.7", kontekst="BIP/Wymagania")

# 2. Uruchom auto-pilot
auto_pilot_start(
    run_id=run["run_id"],
    from_station="inicjuj",   # puste = od nastepnej stacji
    to_station="",            # puste = do konca pipeline'u
    max_gate_iterations=2
)

# 3. Monitoruj status
auto_pilot_status(run["run_id"])

# 4. Opcjonalnie zatrzymaj
auto_pilot_stop(run["run_id"])
```

Uwaga: wykonanie jest synchroniczne - `auto_pilot_start` blokuje do momentu
zakonczenia sciezki, osiagniecia `to_station`, blokady lub eskalacji bramki
i zwraca finalny status wraz z lista wykonanych stacji. `auto_pilot_status`
sluzy do wgladu w stan po zakonczeniu (lub z innego klienta). Parametr
`max_gate_iterations` ogranicza liczbe powrotow bramki tolerowanych przez
auto-pilot, niezaleznie od limitu samej bramki.

## 3. Przeplyw wykonania

```
auto_pilot_start(run_id, from_station)
   |
   v
[Petla auto-pilota]
   |
   +-- 1. Wybierz nastepna stacje (get_next_station)
   |       Jesli null -> zakoncz auto-pilot (status: zakonczony)
   |
   +-- 2. Zaladuj prompt wbudowanego skilla stacji (skills_loader)
   |
   +-- 3. Wstrzyknij koperte do promptu
   |       - stan.zamiar
   |       - pola_stacji (ostatnie 3 stacje)
   |       - walidacja (pola wymagane dla stacji)
   |
   +-- 4. Wywolaj LLM (llm.complete)
   |       - provider: OpenAI | Anthropic | lokalny
   |       - model: z konfiguracji
   |       - system: zasady globalne (jezyk polski, styl)
   |       - prompt: skill + koperta
   |
   +-- 5. Parsuj wyjscie LLM
   |       - wyodrebnij blok KOPERTA (YAML)
   |       - wyodrebnij pola wyjsciowe stacji
   |       - jesli brak KOPERTY -> blad parsowania, zatrzymaj
   |
   +-- 6. execute_station(run_id, station, output)
   |       - aktualizuj koperte
   |       - zapisz checkpoint
   |       - zapisz relacje do Memgraph
   |
   +-- 7. Czy stacja to sprawdzenie?
   |       Tak -> wywolaj quality_gate z wynikiem audytu
   |       Nie -> wroc do kroku 1
   |
   +-- 8. Bramka jakosci
   |       przejdz -> wroc do kroku 1 (nastepna stacja)
   |       powrot -> wroc do kroku 1 (stacja loop_target)
   |       eskalacja -> zatrzymaj auto-pilot (status: zablokowany)
   |
   v
[Zakonczenie auto-pilota]
```

## 4. Budowanie promptu stacji

Serwer buduje prompt dla kazdej stacji z wbudowanego skilla:

```python
def build_station_prompt(station: str, envelope: Envelope) -> str:
    skill = skills_loader.load_skill(station)
    skill_prompt = skill.content  # tresc SKILL.md

    envelope_yaml = yaml.dump(envelope.model_dump(), allow_unicode=True)

    return f"""{skill_prompt}

---

AKTUALNA KOPERTA RUN'U:
{envelope_yaml}

WYKONAJ STACJE '{station}' NA PODSTAWIE POWYZSZEGO SKILLA I KOPIERTY.
ZWROC WYJSCIE STACJI ORAZ ZAKONCZ BLOKIEM KOPERTA ZAKTUALIZOWANYM O TWOJE WYJSCIE.
"""
```

## 5. Parsowanie wyjscia LLM

Serwer parsuje wyjscie LLM, szukajac bloku `KOPERTA:`:

```python
def parse_llm_output(output: str, station: str) -> dict:
    # Szukaj bloku KOPERTA: ... (YAML)
    koperta_match = re.search(
        r'KOPERTA:\s*\n((?:  .*\n)*)',
        output
    )
    if not koperta_match:
        raise LLMOutputParseError("Brak bloku KOPERTA w wyjsciu LLM")

    koperta_yaml = "KOPERTA:\n" + koperta_match.group(1)
    koperta_data = yaml.safe_load(koperta_yaml)

    # Wyodrebnij pola wyjsciowe stacji z pola_stacji.<station>
    station_output = koperta_data["KOPERTA"]["pola_stacji"][station]

    return station_output
```

## 6. Dostawcy LLM

### 6.1. OpenAI

```python
class OpenAIProvider:
    def __init__(self, model: str, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content
```

### 6.2. Anthropic

```python
class AnthropicProvider:
    def __init__(self, model: str, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, prompt: str, system: str = "") -> str:
        response = self.client.messages.create(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        return response.content[0].text
```

### 6.3. Lokalny (Ollama / OpenAI-compatible)

```python
class LocalProvider:
    def __init__(self, model: str, base_url: str = "http://localhost:11434/v1"):
        self.client = openai.OpenAI(base_url=base_url, api_key="local")
        self.model = model

    def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content
```

## 7. Konfiguracja

Zmienne srodowiskowe:

| Zmienna | Wartosc domyslna | Opis |
|---|---|---|
| `PIPELINE_LLM_PROVIDER` | `openai` | `openai` \| `anthropic` \| `local` |
| `PIPELINE_LLM_MODEL` | `gpt-4o` | Model LLM |
| `PIPELINE_LLM_API_KEY` | - | Klucz API (z env lub pliku) |
| `PIPELINE_LLM_BASE_URL` | - | URL dla dostawcy lokalnego |
| `PIPELINE_LLM_SYSTEM_PROMPT` | wbudowany | System prompt (jezyk, styl) |
| `PIPELINE_LLM_MAX_TOKENS` | `4096` | Max tokenow wyjscia |
| `PIPELINE_AUTO_PILOT` | `false` | Czy auto-pilot domyslnie wlaczony |

## 8. Obsluga bledow w auto-pilocie

| Blad | Akcja serwera |
|---|---|
| `LLM_NOT_CONFIGURED` | Zatrzymaj auto-pilot, zwroc status `zablokowany` |
| `LLM_API_ERROR` | Zatrzymaj auto-pilot, zwroc status `zablokowany` z opisem bledu |
| `LLM_OUTPUT_PARSE_ERROR` | Zatrzymaj auto-pilot, zwroc status `zablokowany` z wyjsciem LLM |
| `CONTRACT_INCOMPLETE` | Zatrzymaj auto-pilot, zwroc status `zablokowany` |
| `GATE_MAX_ITERATIONS` | Zatrzymaj auto-pilot, zwrec status `zablokowany` (eskalacja) |
| `MEMGRAPH_UNAVAILABLE` | Kontynuuj bez zapisu do Memgraph (ostrzezenie w statusie) |

## 9. Koszty i monitoring

Auto-pilot sledzi koszty LLM:

```python
auto_pilot_status(run_id) -> {
    status: "uruchomiony" | "zakonczony" | "zatrzymany" | "zablokowany",
    stacja_aktualna: str,
    stacje_wykonane: list[str],
    stacje_pozostale: list[str],
    iteracja_bramki: int,
    bledy: list[str],
    ostatni_llm_koszt: {
        "tokens_wejscie": int,
        "tokens_wyjscie": int,
        "koszt_usd": float,
        "model": str
    } | null,
    laczny_koszt: {
        "tokens_wejscie": int,
        "tokens_wyjscie": int,
        "koszt_usd": float
    }
}
```
