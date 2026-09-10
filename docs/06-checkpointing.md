# Mechanizm checkpointow i restart

Checkpointowanie umozliwia restart pipeline od dowolnej stacji oraz kompresje kontekstu w dlugich pipeline'ach. Po zakonczeniu kazdej stacji merytorycznej koperta jest zapisywana do pliku checkpointu.

## 1. Struktura katalogow

Tryb wieloklientowy (z `client_id`):

```
.ai-kb/clients/<client_id>/pipeline-runs/
  <run_id>/
    manifest.yaml              # indeks stacji, statusy, sciezka, iteracja bramki
    stan_inicjuj.yaml       # checkpoint po inicjuj
    stan_zmienne.yaml       # checkpoint po zmienne
    stan_analiza.yaml
    stan_dekompozycja.yaml  # tylko sciezka doglebny
    stan_dobierz.yaml
    stan_dobierz_iter1.yaml # checkpoint po 1. iteracji bramki
    stan_routing.yaml       # tylko sciezka doglebny
    stan_planuj.yaml
    stan_planuj_iter1.yaml  # checkpoint po iteracji bramki
    stan_realizuj.yaml
    stan_weryfikacja.yaml
    stan_sprawdzenie.yaml
    stan_ewaluacja.yaml     # tylko sciezka doglebny
    stan_utrwal.yaml
    stan_monitoruj.yaml     # tylko sciezka doglebny
    envelope_final.yaml        # ostateczna koperta po zamknieciu
```

Tryb legacy (brak `client_id`): `.ai-kb/pipeline-runs/<run_id>/` (kompatybilnosc wstecz).

## 2. Manifest

```yaml
MANIFEST:
  run_id: "<YYYY-MM-DD>-<skrot-zamiaru>"
  zamiar: ""
  sciezka: szybki | pelny | doglebny
  iteracja_bramki: 0
  status_runu: w_trakcie | zakonczony | zablokowany
  client_id: ""               # identyfikator klienta (pusty = legacy)
  timestamp_start: "2026-06-29T14:32:00"
  timestamp_end: null
  historia_bramki: []         # U4: historia iteracji bramki
  stacje:
    - stacja: inicjuj
      status: zakonczona           # zakonczona | w_trakcie | zablokowana | pominieta
      timestamp: "2026-06-29T14:32:10"
      checkpoint: stan_inicjuj.yaml
    - stacja: zmienne
      status: zakonczona
      timestamp: "2026-06-29T14:35:22"
      checkpoint: stan_zmienne.yaml
    - stacja: analiza
      status: w_trakcie
      timestamp: null
      checkpoint: null
```

## 3. Zasady checkpointowania

### 3.1. Tworzenie run

Stacja `inicjuj` tworzy katalog `.ai-kb/clients/<client_id>/pipeline-runs/<run_id>/` (tryb legacy bez `client_id`: `.ai-kb/pipeline-runs/<run_id>/`) i plik `manifest.yaml` z pustym stanem stacji. Serwer wykonuje to w narzedziu `start_run`.

### 3.2. Zapis po stacji

Po zakonczeniu kazdej stacji merytorycznej (wywolanie `execute_station`) serwer:
1. Zapisuje koperte do `stan_<NN>_<stacja>.yaml`
2. Aktualizuje `manifest.yaml` (status `zakonczona`, timestamp, nazwa checkpointu)

### 3.3. Aktualizacja statusu

Przed rozpoczeciem stacji serwer ustawia jej status na `w_trakcie` w manifeście. Po zakonczeniu na `zakonczona`. Przy blokadzie na `zablokowana`.

### 3.4. Restart od stacji

Przy restarcie (`resume_run`) serwer:
1. Odczytuje `manifest.yaml`
2. Identifikuje ostatnia stacje `zakonczona`
3. Odczytuje jej checkpoint
4. Zwraca stacje wznowienia (nastepna po ostatniej zakonczonej)
5. Skilla `monitoruj` raportuje status restartu

### 3.5. Kompresja kontekstu

W sciezce `doglebny` (10+ stacji), po zapisaniu checkpointu dla stacji starszych niz 3 wstecz, serwer moze usunac ich sekcje `pola_stacji` z koperty w kontekscie konwersacji. Pozostawia tylko `stan` i sekcje 3 ostatnich stacji. Pelne dane pozostaja w plikach checkpointow.

```python
def compress_envelope(envelope: Envelope, keep_last_n: int = 3) -> Envelope:
    stations = list(envelope.pola_stacji.keys())
    if len(stations) <= keep_last_n:
        return envelope
    to_remove = stations[:-keep_last_n]
    for s in to_remove:
        del envelope.pola_stacji[s]
    return envelope
```

### 3.6. Bramka jakosci

Iteracje bramki zwiekszaja `iteracja_bramki` w manifeście. Przy powrocie do `dobierz`/`planuj` serwer zapisuje nowy checkpoint z sufiksem `_iter<N>`.

### 3.7. Stacje pominiete

Stacje pomijane w sciezce `szybki`/`pelny` oznaczane w manifeście jako `pominieta` bez checkpointu.

### 3.8. Czyszczenie

Po zakonczeniu pipeline'u (status `zakonczony` dla ostatniej stacji) katalog run pozostaje jako historia audytowa. Serwer nie usuwa automatycznie.

## 4. Format checkpointu

Checkpoint jest plikiem YAML zawierajacym pelna koperte po zakonczeniu stacji:

```yaml
# stan_zmienne.yaml
run_id: "2026-06-29-weryfikacja-mechanizmu"
sciezka: pelny
stacja_aktualna: zmienne
stacja_poprzednia: inicjuj
timestamp: "2026-06-29T14:35:22"
stan:
  zamiar: "Zweryfikuj mechanizm koperty"
  klasyfikacja: rutynowe
  punkt_wejscia: zmienne
pola_stacji:
  inicjuj:
    klasyfikacja: rutynowe
    punkt_wejscia: zmienne
    uzasadnienie: "..."
    ryzyka: []
  zmienne:
    variables: [...]
    relations: [...]
    sources_used: [...]
    missing_data_resolution: {...}
    analysis_object:
      name: "Mechanizm koperty"
walidacja:
  stacja_docelowa: analiza
  pola_wymagane: [NAZWA OBIEKTU]
  pola_obecne: [analysis_object.name]
  pola_brakujace: []
  status: gotowy
  akcja_naprawcza: ""
relacje:
  - zrodlo: "stacja:inicjuj"
    cel: "stacja:zmienne"
    typ: nastapila_po
  - zrodlo: "run:2026-06-29-weryfikacja-mechanizmu"
    cel: "stacja:zmienne"
    typ: zawiera
```

## 5. Implementacja w serwerze

`checkpoint.py`:

```python
import yaml
from pathlib import Path
from .models import Envelope

def save_checkpoint(
    run_id: str, station: str, envelope: Envelope, suffix: str = "",
    workspace: str | None = None, client_id: str = ""
) -> str:
    config = get_config()
    checkpoint_path = config.checkpoint_path(run_id, station, suffix, workspace, client_id)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    data = envelope.model_dump()
    data["_checkpoint"] = {
        "station": station, "suffix": suffix,
        "timestamp": datetime.now().isoformat(),
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return str(checkpoint_path)

def load_checkpoint(
    run_id: str, station: str, suffix: str = "",
    workspace: str | None = None, client_id: str = ""
) -> Envelope:
    config = get_config()
    checkpoint_path = config.checkpoint_path(run_id, station, suffix, workspace, client_id)
    with open(checkpoint_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data.pop("_checkpoint", None)
    return Envelope(**data)

def list_checkpoints(
    run_id: str, workspace: str | None = None, client_id: str = ""
) -> list[dict]:
    config = get_config()
    run_dir = config.run_dir(run_id, workspace, client_id)
    if not run_dir.exists():
        return []
    checkpoints = []
    for f in sorted(run_dir.glob("stan_*.yaml")):
        stat = f.stat()
        name = f.stem.replace("stan_", "", 1)
        if "_iter" in name:
            station, iter_part = name.rsplit("_iter", 1)
            suffix = f"_iter{iter_part}"
        else:
            station, suffix = name, ""
        checkpoints.append({
            "station": station, "checkpoint_path": str(f),
            "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "suffix": suffix, "size_bytes": stat.st_size,
        })
    return checkpoints

def get_latest_checkpoint(
    run_id: str, workspace: str | None = None, client_id: str = ""
) -> tuple[str, Envelope] | None:
    # Uzywa manifestu do ustalenia ostatniej zakonczonej stacji (chronologicznie)
    from .manifest import load_manifest
    config = get_config()
    manifest_path = config.manifest_path(run_id, workspace, client_id)
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        for s in reversed(manifest.stacje):
            if s.status == "zakonczona" and s.checkpoint:
                cp_path = Path(s.checkpoint)
                if cp_path.exists():
                    return s.stacja, _load_envelope_file(cp_path)
    # Fallback: sortuj po timestamp pliku (mtime)
    checkpoints = list_checkpoints(run_id, workspace, client_id)
    if not checkpoints:
        return None
    main_checkpoints = [c for c in checkpoints if not c["suffix"]] or checkpoints
    main_checkpoints.sort(key=lambda c: c["timestamp"])
    latest = main_checkpoints[-1]
    envelope = load_checkpoint(run_id, latest["station"], latest["suffix"], workspace, client_id)
    return latest["station"], envelope
```

## 6. Narzedzia MCP

### save_checkpoint_tool

Ręczny zapis checkpointu (normalnie wywolywane automatycznie przez `execute_station`).

### load_checkpoint_tool

Odczyt checkpointu stacji. Zwraca koperte z checkpointu.

### list_checkpoints_tool

Lista wszystkich checkpointow dla run'u z metadanymi (rozmiar, timestamp, suffix).

## 7. Integralnosc checkpointow

Serwer waliduje integralnosc checkpointow:

1. **Ciaglosc stacji** - kazda stacja `zakonczona` musi miec checkpoint
2. **Kolejnosc** - numery checkpointow rosnace
3. **Spójnosc run_id** - wszystkie checkpointy w katalogu maja ten sam `run_id`
4. **Spójnosc sciezki** - wszystkie checkpointy maja ta sama `sciezka`

Naruszenia integralnosci sa zgłaszane przez narzedzie `get_run_status` i skilla `audyt_runu`.
