# Wbudowane skille stacji (samodzielne)

Serwer zawiera wbudowane skille wszystkich 13 stacji pipeline'u. Skille sa kopia oryginalow z `/etc/windsurf/skills/` i stanowia czesc pakietu w `src/pipeline_mcp/skills/`.

## 1. Zasada samodzielnosci

Serwer jest w pelni self-contained wzgledem skilli:

- Skille wbudowane w pakiet (`src/pipeline_mcp/skills/<stacja>/SKILL.md`)
- Ladowane przez `importlib.resources` (nie z systemu plikow uzytkownika)
- Aktualizacja skilli wymaga aktualizacji pakietu
- Serwer nie zalezy od `/etc/windsurf/skills/` ani zadnego innego katalogu zewnetrznego

## 2. Lista wbudowanych stacji

| # | Stacja | Katalog | Faza |
|---|---|---|---|
| 0 | inicjuj | `skills/inicjuj-run/` | Inicjacja |
| 1 | zmienne | `skills/zmienne/` | Normalizacja |
| 2 | analiza | `skills/analiza/` | Rozpoznanie |
| 3 | dekompozycja | `skills/dekompozycja/` | Podzial |
| 4 | dobierz | `skills/dobierz/` | Wybor |
| 5 | routing | `skills/routing/` | Routing sciezki |
| 6 | planuj | `skills/planuj/` | Planowanie |
| 7 | realizuj | `skills/realizuj/` | Realizacja |
| 8 | weryfikacja | `skills/weryfikacja/` | Weryfikacja |
| 9 | sprawdzenie | `skills/sprawdzenie/` | Audyt |
| 10 | ewaluacja | `skills/ewaluacja/` | Ewaluacja ex-post |
| 11 | utrwal | `skills/utrwal/` | Utrwalenie |
| 12 | monitoruj | `skills/monitoruj/` | Monitorowanie |
| 13 | audyt_runu | `skills/audyt-runu/` | Audyt run'u |

## 3. Pliki wspoldzielone

| Plik | Lokalizacja | Zawartosc |
|---|---|---|
| `pipeline_sklills.md` | `skills/pipeline_sklills.md` | Specyfikacja pipeline'u, sciezki, bramka, koperta |
| `kontrakty_pipelines.md` | `skills/kontrakty_pipelines.md` | Kontrakty I/O miedzy stacjami, mapowanie pole-po-polu |
| `zrodla-i-narzedzia.md` | `skills/_shared/zrodla-i-narzedzia.md` | Hierarchia zrodel, narzedzia, workflow przeszukiwania |
| `graf-pipeline.md` | `skills/_shared/graf-pipeline.md` | Schemat grafu Memgraph, mapowanie koperty na wezly |

## 4. Ladowanie skilli

`skills_loader.py` ladowane sa przez `importlib.resources` (sciezka z `__file__`):

```python
from pathlib import Path
import yaml
from .stations import STATION_TO_SKILL_DIR, STATIONS

def _get_skills_dir() -> Path:
    """Zwraca sciezke katalogu wbudowanych skilli."""
    return Path(__file__).parent / "skills"

def load_skill(station_name: str) -> dict:
    """Ladowanie wbudowanego skilla stacji z pakietu.

    Uzywa mapowania STATION_TO_SKILL_DIR do przeksztalcenia nazwy stacji
    na nazwe katalogu skilla (np. 'inicjuj' -> 'inicjuj-run',
    'audyt_runu' -> 'audyt-runu').
    """
    skill_dir_name = STATION_TO_SKILL_DIR.get(station_name)
    if skill_dir_name is None:
        raise SkillNotFoundError(station_name)

    skill_path = _get_skills_dir() / skill_dir_name / "SKILL.md"
    if not skill_path.exists():
        raise SkillNotFoundError(station_name)

    skill_text = skill_path.read_text(encoding="utf-8")

    # Parsuj frontmatter
    frontmatter = {}
    content = skill_text
    if skill_text.startswith("---"):
        parts = skill_text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()

    return {
        "name": frontmatter.get("name", station_name),
        "description": frontmatter.get("description", ""),
        "version": frontmatter.get("version", ""),
        "content": content,
        "frontmatter": frontmatter
    }

def get_skill_prompt(station_name: str, envelope_dict: dict | None = None) -> str:
    """Budowanie promptu dla stacji z wstrzyknieciem koperty."""
    skill = load_skill(station_name)
    skill_prompt = skill["content"]
    if envelope_dict:
        envelope_yaml = yaml.dump(envelope_dict, allow_unicode=True,
                                   default_flow_style=False, sort_keys=False)
        return f"""{skill_prompt}

---

AKTUALNA KOPERTA RUN'U:
{envelope_yaml}

WYKONAJ STACJE '{station_name}' NA PODSTAWIE POWYZSZEGO SKILLA I KOPERTY.
ZWROC WYJSCIE STACJI ORAZ ZAKONCZ BLOKIEM KOPERTA ZAKTUALIZOWANYM O TWOJE WYJSCIE.
"""
    return skill_prompt

def list_available_skills() -> list[str]:
    """Lista dostepnych wbudowanych skilli (nazwy stacji, nie katalogi)."""
    return list(STATIONS.keys())
    # ["inicjuj", "zmienne", "analiza", "dekompozycja", "dobierz", "routing",
    #  "planuj", "realizuj", "weryfikacja", "sprawdzenie", "ewaluacja",
    #  "utrwal", "monitoruj", "audyt_runu"]
```

## 5. Kontrakty I/O (wbudowane)

Kontrakty miedzy stacjami sa wbudowane w kod (`stations.py`, `contracts.py`) na podstawie `kontrakty_pipelines.md`. Serwer nie czyta kontraktow z zewnetrznego pliku - sa zaimplementowane jako struktury danych.

`stations.py`:

```python
from dataclasses import dataclass

@dataclass
class StationDef:
    name: str
    phase: str
    required_input: list[str]
    optional_input: list[str]
    output: list[str]
    next_station_logic: str  # jak wyznaczyc nastepna stacje

STATIONS = {
    "inicjuj": StationDef(
        name="inicjuj",
        phase="Inicjacja",
        required_input=["ZAMIAR_UZYTKOWNIKA"],
        optional_input=["KONTEKST", "ZRODLA", "TRYB_INICJACJI"],
        output=["klasyfikacja", "punkt_wejscia", "uzasadnienie", "ryzyka"],
        next_station_logic="klasyfikacja_based"
    ),
    "zmienne": StationDef(
        name="zmienne",
        phase="Normalizacja",
        required_input=["task_goal"],
        optional_input=["context", "operation_mode", "ZRODLA"],
        output=["variables", "relations", "sources_used",
                "missing_data_resolution", "analysis_object"],
        next_station_logic="sequential"
    ),
    # ... pozostale stacje
}
```

## 6. Aktualizacja skilli

Aktualizacja wbudowanych skilli wymaga aktualizacji pakietu serwera:

1. Skopiuj zaktualizowane `SKILL.md` do `src/pipeline_mcp/skills/<stacja>/`
2. Zaktualizuj kontrakty w `stations.py` i `contracts.py` jesli sie zmienily
3. Zaktualizuj `pipeline_sklills.md` i `kontrakty_pipelines.md` w `skills/`
4. Zbierz pakiet i opublikuj

Skille sa wersjonowane razem z kodem serwera w repozytorium Git.

## 7. Weryfikacja integralnosci skilli

Serwer przy starcie weryfikuje integralnosc wbudowanych skilli:

- Wszystkie 13 stacji maja `SKILL.md`
- Wszystkie `SKILL.md` maja poprawny frontmatter
- Kontrakty w `stations.py` sa zgodne z `kontrakty_pipelines.md`
- Sciezki w `routing.py` sa zgodne z `pipeline_sklills.md`

Naruszenia integralnosci sa logowane przy starcie serwera.
