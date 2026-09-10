"""Serwer FastMCP z narzedziami pipeline'u.

Glowny punkt wejscia. Rejestruje wszystkie narzedzia MCP.

MT: System wieloklientowy (multi-tenant). Kazde narzedzie przyjmuje opcjonalny
parametr client_id. Gdy podany - dane izolowane per-klient. Gdy pusty - tryb
legacy (kompatybilnosc wsteczna). Hierarchia rozwiazywania client_id:
1. Jawny parametr client_id w wywolaniu
2. Aktywny klient sesji (set_active_client)
3. PIPELINE_DEFAULT_CLIENT_ID (env var)
4. Tryb legacy (client_id = "")
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from fastmcp import FastMCP
from fastmcp.prompts import Message

from .config import get_config
from .envelope import (
    accumulate_state,
    add_station_relations,
    compress_envelope,
    create_envelope,
    get_envelope_summary,
    update_station_fields,
)
from .manifest import (
    add_station_to_manifest,
    close_manifest,
    create_manifest,
    get_last_completed_station,
    get_station_status,
    load_manifest,
    save_manifest,
    update_station_status,
)
from .models import (
    Envelope,
    Manifest,
    PipelineError,
    RunNotFoundError,
    RunClosedError,
    StationNotFoundError,
    StationAlreadyDoneError,
    ClientIdMismatchError,
)
from .checkpoint import (
    get_latest_checkpoint,
    list_checkpoints,
    load_checkpoint,
    save_checkpoint,
    save_envelope_final,
)
from .contracts import get_mapping_for_station, validate_input
from .rtm import auto_update_rtm as rtm_auto_update, update_entry as rtm_update_entry, add_entry as rtm_add_entry, validate_coverage as rtm_validate_coverage
from .quality_gate import evaluate_gate, get_gate_history
from .routing import (
    determine_path,
    get_next_station as routing_get_next_station,
    is_station_in_path,
)
from .stations import STATIONS, get_station, station_exists
from .skills_loader import (
    list_available_skills,
    load_skill,
    verify_skills_integrity,
)

# MT: Rejestr klientow, wiedza, RAG, pamiec
from . import client_registry
from . import knowledge
from . import rag
from . import client_memory

# Auto-pilot (lazy import zeby uniknac bledow jesli LLM nie skonfigurowany)
from . import auto_pilot

logger = logging.getLogger(__name__)

# MT: Stan sesji - aktywny klient per polaczenie MCP (stdio = jedno polaczenie)
_active_client_id: str = ""


def _resolve_client_id(explicit: str = "") -> str:
    """Rozwiazuje client_id wg hierarchii priorytetow.

    1. Jawny parametr explicit (nadpisuje wszystko)
    2. Aktywny klient sesji (_active_client_id)
    3. PIPELINE_DEFAULT_CLIENT_ID (env var)
    4. Pusty string (tryb legacy)
    """
    if explicit:
        return explicit
    if _active_client_id:
        return _active_client_id
    config = get_config()
    if config.default_client_id:
        return config.default_client_id
    return ""


def _ws(workspace: str) -> str | None:
    """Pomocnik: konwertuje pusty string na None."""
    return workspace if workspace else None


def _ensure_client_id_match(manifest: Manifest, client_id: str) -> None:
    """MT: Sprawdza czy client_id zgadza sie z manifeście run'u.

    Chroni przed cross-client access: jesli run nalezy do klienta A,
    a wywolanie przychodzi z client_id=B, rzuc blad.
    Run'y legacy (client_id="") sa dostepne z dowolnym client_id.
    """
    if manifest.client_id and client_id and manifest.client_id != client_id:
        raise ClientIdMismatchError(
            f"Run '{manifest.run_id}' nalezy do klienta '{manifest.client_id}', "
            f"a wywolano z client_id='{client_id}'. Brak dostepu cross-client."
        )


PIPELINE_INSTRUCTIONS = """\
Pipeline MCP Server orkiestruje prace agenta AI przez 13 stacji w petli pipeline.

## Wieloklientowosc (multi-tenant)

Jesli obslugujesz wielu klientow w jednym workspace:

1. Wywolaj `resolve_client(query)` z nazwa, aliasem, NIP, telefonem lub fragmentem.
   - Przy 100% pewnosci (NIP, telefon) klient jest auto-rozpoznany.
   - Ponizej 100% zwraca kandydatow - zapytaj uzytkownika o potwierdzenie.
2. Po potwierdzeniu wywolaj `set_active_client(client_id)` z kanonicznym ID.
3. Wszystkie kolejne operacje pipeline beda izolowane per ten klient.
4. Jesli klient nie istnieje, zarejestruj go przez `register_client`.
5. Wiedza wspoldzielona jest dostepna przez narzedzia `save_shared_knowledge`,
   `get_shared_knowledge`, `search_shared_knowledge`.
6. Pamiec AI per-klient: `save_client_memory`, `get_client_memory`, `list_client_memories`.
7. RAG per-klient: `index_client_document`, `search_client_rag`, `search_shared_rag`.

Jesli nie ustawisz aktywnego klienta, pipeline dziala w trybie legacy
(wszystkie run'y we wspolnym katalogu, bez izolacji).

## Jak uzywac

1. Na poczatku zadania wywolaj prompt `pipeline_start` z zamiarem uzytkownika.
   Prompt automatycznie wywola `start_run` i zwroci instrukcje do pierwszej stacji.
2. Wykonuj stacje sekwencyjnie uzywajac `execute_station` z wynikiem pracy.
3. Po kazdej stacji serwer zwraca `next_station` i `validation` - postepuj zgodnie z nimi.
4. Po stacji `sprawdzenie` wywolaj `quality_gate` z wynikiem audytu.
5. Na koncu wywolaj `close_run` aby zamknac run.

## Kluczowe zasady

- Koperta (envelope) jest jedynym noznikiem danych miedzy stacjami.
- Kazda stacja ma kontrakt I/O - sprawdz `get_station_contract` przed wykonaniem.
- Skille stacji sa wbudowane w serwer - uzyj `get_station_contract` aby pobrac prompt skilla.
- Bramka jakosci max 2 iteracje - po eskalacji wymagana interwencja uzytkownika.
- `workspace` jest opcjonalny - domyslnie uzywa cwd (katalog projektu).
- `client_id` jest opcjonalny - domyslnie uzywa aktywnego klienta sesji lub trybu legacy.
- RTM (Requirements Traceability Matrix) sledzi wymagania przez pipeline automatycznie.
  Uzyj `get_rtm` aby pobrac macierz, `validate_rtm_coverage` do raportu pokrycia.

## Sciezki pipeline'u

- `szybki` (5 stacji): inicjuj -> zmienne -> analiza -> dobierz -> sprawdzenie
- `pelny` (9 stacji): inicjuj -> zmienne -> analiza -> dobierz -> planuj -> realizuj -> weryfikacja -> sprawdzenie -> utrwal
- `doglebny` (13 stacji): pelna sekwencja z dekompozycja, routing, ewaluacja, monitoruj

Sciezke wybiera stacja `inicjuj` na podstawie klasyfikacji zadania.
"""

mcp = FastMCP("Pipeline MCP Server", instructions=PIPELINE_INSTRUCTIONS)


def _generate_run_id(zamiar: str) -> str:
    """Generuje run_id w formacie <YYYY-MM-DD>-<skrot-zamiaru>."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    import unicodedata
    normalized = unicodedata.normalize("NFKD", zamiar)
    ascii_zamiar = normalized.encode("ascii", "ignore").decode()
    words = ascii_zamiar.lower().split()
    skrot = "-".join(words[:3])[:30]
    skrot = re.sub(r"[^a-z0-9-]", "", skrot)
    skrot = re.sub(r"-{2,}", "-", skrot).strip("-")
    return f"{date_str}-{skrot}" if skrot else f"{date_str}-run"


def _unique_run_id(run_id: str, workspace: str | None, client_id: str = "") -> str:
    """Zapewnia unikalnosc run_id - przy kolizji dodaje sufiks -2, -3, ..."""
    config = get_config()
    if not config.manifest_path(run_id, workspace, client_id).exists():
        return run_id
    counter = 2
    while config.manifest_path(f"{run_id}-{counter}", workspace, client_id).exists():
        counter += 1
    return f"{run_id}-{counter}"


def _ensure_run_open(manifest: Manifest) -> None:
    """Sprawdza czy run nie jest zamkniety."""
    if manifest.status_runu == "zakonczony":
        raise RunClosedError(f"Run '{manifest.run_id}' jest zakonczony.")


# =====================================================================
# 1. RUN MANAGEMENT
# =====================================================================


@mcp.tool
def start_run(
    zamiar: str,
    kontekst: str = "",
    zrodla: list[str] | None = None,
    tryb_inicjacji: str = "pelny",
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Tworzy nowy run pipeline'u. Generuje run_id, tworzy manifest i pusta koperte.

    Args:
        zamiar: Zamiar uzytkownika (wymagany)
        kontekst: Kontekst zadania (opcjonalny)
        zrodla: Zrodla bazowe (opcjonalne)
        tryb_inicjacji: "szybki" lub "pelny" (domyslnie "pelny")
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny). Jesli pusty, uzywa aktywnego klienta sesji.

    Returns:
        Slownik z run_id, first_station, manifest_path, envelope
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not zamiar:
        raise PipelineError("Zamiar jest wymagany")

    # F4: waliduj istnienie klienta w rejestrze (zapobiega osieroconym katalogom)
    if cid:
        existing = client_registry.load_client(cid, ws)
        if existing is None:
            from .models import ClientNotFoundError
            raise ClientNotFoundError(
                f"Klient '{cid}' nie istnieje w rejestrze. "
                "Uzyj register_client aby go utworzyc, lub usun client_id aby dzialac w trybie legacy."
            )

    config = get_config()
    run_id = _unique_run_id(_generate_run_id(zamiar), ws, cid)

    # Utworz katalog run'u
    run_dir = config.run_dir(run_id, ws, cid)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Utworz manifest (sciezka domyslnie pelny, inicjuj ustali ostateczna)
    manifest = create_manifest(run_id, zamiar, sciezka="pelny", client_id=cid)
    manifest = add_station_to_manifest(manifest, "inicjuj", "w_trakcie")
    save_manifest(manifest, config.manifest_path(run_id, ws, cid))

    # Utworz pusta koperte
    envelope = create_envelope(run_id, zamiar, sciezka="pelny", client_id=cid)

    # Zapisz wejscie uzytkownika do koperty
    wejscie = {
        "kontekst": kontekst,
        "zrodla": zrodla or [],
        "tryb_inicjacji": tryb_inicjacji,
    }
    if any([kontekst, zrodla]):
        envelope.wejscie = wejscie
        save_checkpoint(run_id, "_start", envelope, "", ws, cid)

    # Zapisz wezel Run do Memgraph (A1: strukturalny wezel grafu)
    from . import memgraph
    memgraph.write_run_node(run_id, zamiar, "pelny", cid)

    return {
        "run_id": run_id,
        "first_station": "inicjuj",
        "manifest_path": str(config.manifest_path(run_id, ws, cid)),
        "client_id": cid,
        "wejscie": wejscie,
        "envelope": envelope.model_dump(),
    }


@mcp.tool
def get_run_status(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca status run'u na podstawie manifestu.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)

    return {
        "run_id": manifest.run_id,
        "zamiar": manifest.zamiar,
        "sciezka": manifest.sciezka,
        "iteracja_bramki": manifest.iteracja_bramki,
        "status_runu": manifest.status_runu,
        "stacja_aktualna": get_last_completed_station(manifest) or "inicjuj",
        "stacje": [s.model_dump() for s in manifest.stacje],
        "timestamp_start": manifest.timestamp_start,
        "timestamp_end": manifest.timestamp_end,
        "client_id": manifest.client_id,
    }


@mcp.tool
def list_runs(
    status_filter: str = "", limit: int = 50, workspace: str = "", client_id: str = ""
) -> list[dict[str, Any]]:
    """Lista wszystkich run'ow w katalogu persystencji.

    MT: Gdy client_id podany, zwraca tylko run'y tego klienta.
    Gdy client_id pusty i brak aktywnego klienta, zwraca run'y legacy.

    Args:
        status_filter: Filtr statusu ("", "w_trakcie", "zakonczony", "zablokowany")
        limit: Maksymalna liczba wynikow
        workspace: Sciezka do workspace'a (opcjonalna).
        client_id: Identyfikator klienta (opcjonalny).
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    runs: list[dict[str, Any]] = []

    runs_dir = config.runs_dir_for(ws, cid)
    if not runs_dir.exists():
        return []

    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue

        manifest_path = run_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        try:
            manifest = load_manifest(manifest_path)
            if status_filter and manifest.status_runu != status_filter:
                continue

            runs.append({
                "run_id": manifest.run_id,
                "zamiar": manifest.zamiar,
                "sciezka": manifest.sciezka,
                "status": manifest.status_runu,
                "stacja_aktualna": get_last_completed_station(manifest) or "inicjuj",
                "timestamp_start": manifest.timestamp_start,
                "client_id": manifest.client_id,
            })

            if len(runs) >= limit:
                break
        except Exception as e:
            logger.warning(f"Blad odczytu run'u {run_dir.name}: {e}")

    return runs


@mcp.tool
def resume_run(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Wznawia run od ostatniej zakonczonej stacji.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna).
        client_id: Identyfikator klienta (opcjonalny).
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    last_station = get_last_completed_station(manifest)
    if not last_station:
        return {
            "run_id": run_id,
            "stacja_wznowienia": "inicjuj",
            "envelope": create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id).model_dump(),
            "walidacja": {"status": "gotowy"},
        }

    latest = get_latest_checkpoint(run_id, ws, cid)
    if not latest:
        raise RunNotFoundError(f"Brak checkpointu dla run'u {run_id}")

    _, envelope = latest
    next_station = routing_get_next_station(last_station, manifest.sciezka)
    walidacja = validate_input(next_station, envelope) if next_station else None

    return {
        "run_id": run_id,
        "stacja_wznowienia": next_station or "zakonczony",
        "envelope": envelope.model_dump(),
        "walidacja": walidacja.model_dump() if walidacja else None,
    }


@mcp.tool
def close_run(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zamyka run. Zapisuje ostateczna koperte, oznacza run jako zakonczony.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna).
        client_id: Identyfikator klienta (opcjonalny).
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)

    if manifest.status_runu == "zakonczony":
        return {
            "run_id": run_id,
            "status": "zakonczony",
            "envelope_final_path": str(config.envelope_final_path(run_id, ws, cid)),
            "stacje_wykonane": len([s for s in manifest.stacje if s.status == "zakonczona"]),
            "iteracje_bramki": manifest.iteracja_bramki,
            "already_closed": True,
        }

    latest = get_latest_checkpoint(run_id, ws, cid)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)

    envelope_path = save_envelope_final(run_id, envelope, ws, cid)
    manifest = close_manifest(manifest)
    save_manifest(manifest, config.manifest_path(run_id, ws, cid))

    from . import memgraph
    memgraph.close_run_node(run_id, manifest.timestamp_end or "", manifest.client_id)

    return {
        "run_id": run_id,
        "status": "zakonczony",
        "envelope_final_path": envelope_path,
        "stacje_wykonane": len([s for s in manifest.stacje if s.status == "zakonczona"]),
        "iteracje_bramki": manifest.iteracja_bramki,
    }


# =====================================================================
# 2. STATION EXECUTION
# =====================================================================


@mcp.tool
def execute_station(
    run_id: str,
    station: str,
    output: dict[str, Any],
    skip_validation: bool = False,
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Rejestruje wynik wykonania stacji przez agenta (tryb manual).

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji (np. "inicjuj")
        output: Wyjscie stacji (pola kontraktu wyjsciowego)
        skip_validation: Pomin walidacje kontraktu (domyslnie False)
        workspace: Sciezka do workspace'a (opcjonalna).
        client_id: Identyfikator klienta (opcjonalny).
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not station_exists(station):
        raise StationNotFoundError(f"Stacja '{station}' nie istnieje")

    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    if station != "audyt_runu":
        _ensure_run_open(manifest)

    existing_status = get_station_status(manifest, station)
    if existing_status == "zakonczona" and not skip_validation:
        raise StationAlreadyDoneError(
            f"Stacja '{station}' juz zakonczona w run'u {run_id}. "
            "Aby wymusic ponowne wykonanie, uzyj skip_validation=True."
        )

    latest = get_latest_checkpoint(run_id, ws, cid)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)

    envelope = update_station_fields(envelope, station, output)
    envelope = accumulate_state(envelope, station, output)
    envelope = add_station_relations(envelope, station, run_id)

    rtm_auto_update(envelope, station, output)

    if station == "inicjuj":
        klasyfikacja = output.get("klasyfikacja", "rutynowe")
        sciezka = determine_path(klasyfikacja)
        envelope.sciezka = sciezka  # type: ignore
        manifest.sciezka = sciezka  # type: ignore

    if station == "routing" and output.get("sciezka"):
        nowa_sciezka = output["sciezka"]
        if nowa_sciezka in ("szybki", "pelny", "doglebny"):
            envelope.sciezka = nowa_sciezka  # type: ignore
            manifest.sciezka = nowa_sciezka  # type: ignore

    next_station = routing_get_next_station(station, envelope.sciezka)
    validation = validate_input(next_station, envelope) if next_station else None

    if validation:
        envelope.walidacja.stacja_docelowa = next_station or ""
        envelope.walidacja.pola_wymagane = validation.pola_wymagane
        envelope.walidacja.pola_obecne = validation.pola_obecne
        envelope.walidacja.pola_brakujace = validation.pola_brakujace
        envelope.walidacja.status = validation.status  # type: ignore
        envelope.walidacja.akcja_naprawcza = validation.akcja_naprawcza

    suffix = f"_iter{manifest.iteracja_bramki}" if manifest.iteracja_bramki > 0 else ""
    checkpoint_path = save_checkpoint(run_id, station, envelope, suffix, ws, cid)

    if envelope.sciezka == "doglebny" and station in ("analiza", "dobierz", "sprawdzenie"):
        envelope = compress_envelope(envelope)

    manifest = update_station_status(manifest, station, "zakonczona", checkpoint_path)
    save_manifest(manifest, config.manifest_path(run_id, ws, cid))

    from . import memgraph
    station_written = memgraph.write_station_node(
        run_id, station, "zakonczona", checkpoint_path, manifest.client_id
    )
    if station == "inicjuj":
        memgraph.write_run_node(run_id, envelope.stan.zamiar, manifest.sciezka, manifest.client_id)
    relations_written = memgraph.write_relations_from_envelope(run_id, envelope)
    memgraph_written = station_written and relations_written

    return {
        "run_id": run_id,
        "station": station,
        "status": "zakonczona",
        "next_station": next_station,
        "envelope_summary": get_envelope_summary(envelope),
        "validation": validation.model_dump() if validation else None,
        "checkpoint_path": checkpoint_path,
        "memgraph_written": memgraph_written,
    }


@mcp.tool
def get_next_station(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca nastepna stacje na podstawie aktualnego stanu run'u.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Nastepna stacja, sciezka, czy ostatnia stacja
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)

    last_station = get_last_completed_station(manifest)
    if not last_station:
        return {
            "run_id": run_id,
            "next_station": "inicjuj",
            "sciezka": manifest.sciezka,
            "reason": "Brak zakonczonych stacji - zaczynamy od inicjuj",
            "gate_iteration": manifest.iteracja_bramki,
            "is_last_station": False,
        }

    next_station = routing_get_next_station(last_station, manifest.sciezka)

    return {
        "run_id": run_id,
        "next_station": next_station,
        "sciezka": manifest.sciezka,
        "reason": f"Nastepna stacja po '{last_station}' w sciezce '{manifest.sciezka}'",
        "gate_iteration": manifest.iteracja_bramki,
        "is_last_station": next_station is None,
    }


@mcp.tool
def skip_station(
    run_id: str, station: str, reason: str = "", workspace: str = "", client_id: str = ""
) -> dict[str, Any]:
    """Reczne pominiecie stacji (tryb hybrydowy).

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji do pominiecia
        reason: Powod pominiecia
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Status pominiecia i nastepna stacja
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not station_exists(station):
        raise StationNotFoundError(f"Stacja '{station}' nie istnieje")

    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    if is_station_in_path(station, manifest.sciezka):
        raise PipelineError(
            f"Stacja '{station}' jest w sciezce '{manifest.sciezka}' i nie powinna byc pomijana. "
            "Pominiecie dozwolone tylko dla stacji opcjonalnych."
        )

    manifest = update_station_status(manifest, station, "pominieta")
    save_manifest(manifest, config.manifest_path(run_id, ws, cid))

    last_completed = get_last_completed_station(manifest)
    next_station = routing_get_next_station(last_completed or "inicjuj", manifest.sciezka) if last_completed else "inicjuj"

    return {
        "run_id": run_id,
        "station": station,
        "status": "pominieta",
        "reason": reason,
        "next_station": next_station,
    }


@mcp.tool
def get_station_contract(run_id: str, station: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca kontrakt I/O dla stacji: wymagane i opcjonalne pola, mappowanie, prompt skilla.

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Kontrakt stacji z promptem wbudowanego skilla
    """
    if not station_exists(station):
        raise StationNotFoundError(f"Stacja '{station}' nie istnieje")

    station_def = get_station(station)
    mapping = get_mapping_for_station(station)

    try:
        skill = load_skill(station)
        skill_prompt = skill["content"]
    except Exception as e:
        skill_prompt = f"[Blad ladowania skilla: {e}]"

    return {
        "station": station,
        "phase": station_def.phase,
        "required_input": station_def.required_input,
        "optional_input": station_def.optional_input,
        "output": station_def.output,
        "mapping_from_previous": mapping,
        "skill_prompt": skill_prompt,
    }


# =====================================================================
# 3. ENVELOPE MANAGEMENT
# =====================================================================


@mcp.tool
def get_envelope(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca aktualna koperte run'u.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Pelna koperta run'u
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    latest = get_latest_checkpoint(run_id, ws, cid)
    if not latest:
        config = get_config()
        manifest = load_manifest(config.manifest_path(run_id, ws, cid))
        _ensure_client_id_match(manifest, cid)
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)
        return envelope.model_dump()

    _, envelope = latest
    return envelope.model_dump()


@mcp.tool
def update_envelope(
    run_id: str,
    section: str,
    fields: dict[str, Any],
    merge: bool = True,
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Reczna aktualizacja koperty (tryb hybrydowy).

    Args:
        run_id: Identyfikator run'u
        section: Sekcja koperty ("stan", "pola_stacji.<stacja>", "walidacja", "relacje", "rtm")
        fields: Pola do aktualizacji
        merge: True = scal z istniejacymi, False = zastap
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Zaktualizowana koperta (skrot)
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    latest = get_latest_checkpoint(run_id, ws, cid)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)

    if section == "stan":
        if merge:
            for k, v in fields.items():
                setattr(envelope.stan, k, v)
        else:
            from .models import Stan
            envelope.stan = Stan(**fields)
    elif section.startswith("pola_stacji."):
        station = section.replace("pola_stacji.", "", 1)
        if merge:
            existing = envelope.pola_stacji.get(station, {})
            existing.update(fields)
            envelope.pola_stacji[station] = existing
        else:
            envelope.pola_stacji[station] = fields
    elif section == "walidacja":
        if merge:
            for k, v in fields.items():
                setattr(envelope.walidacja, k, v)
        else:
            from .models import Walidacja
            envelope.walidacja = Walidacja(**fields)
    elif section == "relacje":
        from .models import Relacja
        if merge:
            envelope.relacje.extend([Relacja(**r) for r in fields.get("relacje", [])])
        else:
            envelope.relacje = [Relacja(**r) for r in fields.get("relacje", [])]
    elif section == "rtm":
        from .models import RTMEntry
        if merge:
            existing_ids = {e.req_id for e in envelope.rtm}
            for entry_data in fields.get("rtm", []):
                entry = RTMEntry(**entry_data)
                if entry.req_id not in existing_ids:
                    envelope.rtm.append(entry)
                    existing_ids.add(entry.req_id)
        else:
            envelope.rtm = [RTMEntry(**e) for e in fields.get("rtm", [])]
    else:
        raise PipelineError(f"Nieznana sekcja koperty: '{section}'")

    last_station = get_last_completed_station(manifest) or "_start"
    save_checkpoint(run_id, last_station, envelope, "", ws, cid)

    return {
        "run_id": run_id,
        "updated_fields": list(fields.keys()),
        "envelope_summary": get_envelope_summary(envelope),
    }


@mcp.tool
def validate_contract(
    run_id: str, target_station: str, workspace: str = "", client_id: str = ""
) -> dict[str, Any]:
    """Waliduje czy wejscie stacji docelowej jest kompletne.

    Args:
        run_id: Identyfikator run'u
        target_station: Stacja docelowa do walidacji
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Wynik walidacji kontraktu
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not station_exists(target_station):
        raise StationNotFoundError(f"Stacja '{target_station}' nie istnieje")

    latest = get_latest_checkpoint(run_id, ws, cid)
    if not latest:
        config = get_config()
        manifest = load_manifest(config.manifest_path(run_id, ws, cid))
        _ensure_client_id_match(manifest, cid)
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)
    else:
        _, envelope = latest

    result = validate_input(target_station, envelope)
    return result.model_dump()


# =====================================================================
# 3b. REQUIREMENTS TRACEABILITY MATRIX (RTM)
# =====================================================================


@mcp.tool
def get_rtm(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca macierz Requirements Traceability Matrix dla run'u.

    RTM mapuje wymagania uzytkownika na stacje adresujace, weryfikujace
    i artefakty. Automatycznie aktualizowana w trakcie wykonywania pipeline'u.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Lista wpisow RTM z metadanymi i raportem pokrycia
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    latest = get_latest_checkpoint(run_id, ws, cid)
    if not latest:
        config = get_config()
        manifest = load_manifest(config.manifest_path(run_id, ws, cid))
        _ensure_client_id_match(manifest, cid)
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)
    else:
        _, envelope = latest

    return {
        "run_id": run_id,
        "rtm": [entry.model_dump() for entry in envelope.rtm],
        "coverage": rtm_validate_coverage(envelope),
    }


@mcp.tool
def update_rtm(
    run_id: str, req_id: str, updates: dict[str, Any], workspace: str = "", client_id: str = ""
) -> dict[str, Any]:
    """Reczna aktualizacja wpisu Requirements Traceability Matrix.

    Pozwala agentowi nadpisac status wymagania, dodac stacje adresujace
    lub artefakty bez wykonywania pelnej stacji.

    Args:
        run_id: Identyfikator run'u
        req_id: Identyfikator wymagania (np. "REQ-001")
        updates: Pola do aktualizacji (status, stacje_adresujace, artefakty, ...)
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Zaktualizowany wpis RTM i raport pokrycia
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    latest = get_latest_checkpoint(run_id, ws, cid)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)

    entry = rtm_update_entry(envelope, req_id, updates)
    if entry is None:
        raise PipelineError(f"Wpis RTM o req_id='{req_id}' nie istnieje w run'u {run_id}")

    last_station = get_last_completed_station(manifest) or "_start"
    save_checkpoint(run_id, last_station, envelope, "", ws, cid)

    return {
        "run_id": run_id,
        "entry": entry.model_dump(),
        "coverage": rtm_validate_coverage(envelope),
    }


@mcp.tool
def add_rtm_entry(
    run_id: str,
    req_id: str,
    opis: str,
    zrodlo: str = "zamiar",
    stacje_adresujace: list[str] | None = None,
    status: str = "nieadresowane",
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Dodaje nowy wpis do Requirements Traceability Matrix.

    Uzyj gdy wymaganie nie zostalo automatycznie wyekstrahowane przez stacje
    zmienne, ale agent identyfikuje je w trakcie wykonywania pipeline'u.

    Args:
        run_id: Identyfikator run'u
        req_id: Identyfikator wymagania (np. "REQ-001")
        opis: Opis wymagania
        zrodlo: Zrodlo wymagania ("zamiar", "kontekst", "zrodla", "agent_inference")
        stacje_adresujace: Stacje adresujace to wymaganie
        status: Status poczatkowy (domyslnie "nieadresowane")
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Dodany wpis RTM i raport pokrycia
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    latest = get_latest_checkpoint(run_id, ws, cid)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)

    entry_data: dict[str, Any] = {
        "req_id": req_id,
        "opis": opis,
        "zrodlo": zrodlo,
        "status": status,
    }
    if stacje_adresujace:
        entry_data["stacje_adresujace"] = stacje_adresujace

    try:
        entry = rtm_add_entry(envelope, entry_data)
    except ValueError as e:
        raise PipelineError(str(e))

    last_station = get_last_completed_station(manifest) or "_start"
    save_checkpoint(run_id, last_station, envelope, "", ws, cid)

    return {
        "run_id": run_id,
        "entry": entry.model_dump(),
        "coverage": rtm_validate_coverage(envelope),
    }


@mcp.tool
def validate_rtm_coverage(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Waliduje pokrycie wymagan w Requirements Traceability Matrix.

    Zwraca raport: liczbe wymagan w poszczegolnych statusach, procent pokrycia,
    listy nieadresowanych i niespelnionych wymagan.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Raport pokrycia wymagan z lista problematycznych req_id
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    latest = get_latest_checkpoint(run_id, ws, cid)
    if not latest:
        config = get_config()
        manifest = load_manifest(config.manifest_path(run_id, ws, cid))
        _ensure_client_id_match(manifest, cid)
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)
    else:
        _, envelope = latest

    return {
        "run_id": run_id,
        "coverage": rtm_validate_coverage(envelope),
    }


# =====================================================================
# 4. QUALITY GATE
# =====================================================================


@mcp.tool
def quality_gate(
    run_id: str,
    audit_status: str,
    audit_wymiary: dict[str, Any] | None = None,
    loop_target: str = "",
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Ocenia bramke jakosci po stacji sprawdzenie.

    Args:
        run_id: Identyfikator run'u
        audit_status: "zgodny" lub "niezgodny"
        audit_wymiary: Wymiary audytu (opcjonalne)
        loop_target: Gdzie wrocic przy niezgodnym ("dobierz" lub "planuj")
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Decyzja bramki, nastepna stacja, iteracja
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    result = evaluate_gate(run_id, manifest, audit_status, audit_wymiary or {}, loop_target)
    save_manifest(manifest, config.manifest_path(run_id, ws, cid))

    return result.model_dump()


@mcp.tool
def get_gate_iterations(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca historie iteracji bramki dla run'u.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Aktualna iteracja, max iteracje, pozostale
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    return get_gate_history(run_id, manifest)


# =====================================================================
# 5. CHECKPOINTING
# =====================================================================


@mcp.tool
def save_checkpoint_tool(
    run_id: str,
    station: str,
    envelope: dict[str, Any],
    suffix: str = "",
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Reczny zapis checkpointu (normalnie wywolywane automatycznie przez execute_station).

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji
        envelope: Koperta do zapisania
        suffix: Sufiks nazwy pliku (np. "_iter1")
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Sciezka zapisanego checkpointu
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    env = Envelope(**envelope)
    path = save_checkpoint(run_id, station, env, suffix, ws, cid)
    return {
        "run_id": run_id,
        "station": station,
        "checkpoint_path": path,
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool
def load_checkpoint_tool(
    run_id: str, station: str, suffix: str = "", workspace: str = "", client_id: str = ""
) -> dict[str, Any]:
    """Odczyt checkpointu stacji.

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji
        suffix: Sufiks nazwy pliku (np. "_iter1")
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Koperta z checkpointu
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    env = load_checkpoint(run_id, station, suffix, ws, cid)
    return {
        "run_id": run_id,
        "station": station,
        "envelope": env.model_dump(),
        "timestamp": env.timestamp,
    }


@mcp.tool
def list_checkpoints_tool(run_id: str, workspace: str = "", client_id: str = "") -> list[dict[str, Any]]:
    """Lista wszystkich checkpointow dla run'u.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Lista checkpointow z metadanymi
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    return list_checkpoints(run_id, ws, cid)


# =====================================================================
# 6. AUTO-PILOT
# =====================================================================


_AUTO_PILOT_MAX_STEPS = 40


@mcp.tool
def auto_pilot_start(
    run_id: str,
    from_station: str = "",
    to_station: str = "",
    max_gate_iterations: int = 2,
    workspace: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Uruchamia tryb auto-pilot. Serwer synchronicznie wykonuje stacje,
    wywolujac LLM dla kazdej z nich, az do konca sciezki lub blokady.

    Args:
        run_id: Identyfikator run'u
        from_station: Stacja startowa (puste = od nastepnej stacji)
        to_station: Stacja koncowa (puste = do konca pipeline'u)
        max_gate_iterations: Max powrotow bramki tolerowanych przez auto-pilot
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Finalny status auto-pilota, wykonane stacje, bledy
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, ws, cid))
    _ensure_client_id_match(manifest, cid)
    _ensure_run_open(manifest)

    auto_pilot.start_auto_pilot(run_id, from_station, to_station, max_gate_iterations)

    executed: list[str] = []
    bledy: list[str] = []
    final_status = "zakonczony"
    station: str | None = from_station or None

    for _ in range(_AUTO_PILOT_MAX_STEPS):
        if auto_pilot.is_stopped(run_id):
            final_status = "zatrzymany"
            break

        manifest = load_manifest(config.manifest_path(run_id, ws, cid))
        if station is None:
            last = get_last_completed_station(manifest)
            station = routing_get_next_station(last, manifest.sciezka) if last else "inicjuj"
        if station is None:
            break

        latest = get_latest_checkpoint(run_id, ws, cid)
        envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka, manifest.client_id)

        try:
            output, _ = auto_pilot.execute_station_with_llm(run_id, station, envelope)
        except Exception as e:
            bledy.append(f"{station}: {e}")
            auto_pilot.update_auto_pilot_state(run_id, station, "zablokowany", str(e))
            final_status = "zablokowany"
            break

        if set(output.keys()) == {"_raw_output"}:
            blad = f"{station}: LLM nie zwrocil bloku KOPERTA (blad parsowania)"
            bledy.append(blad)
            auto_pilot.update_auto_pilot_state(run_id, station, "zablokowany", blad)
            final_status = "zablokowany"
            break

        exec_result = execute_station(
            run_id, station, output, skip_validation=True, workspace=workspace, client_id=cid
        )
        executed.append(station)
        auto_pilot.update_auto_pilot_state(run_id, station, "zakonczona")

        if to_station and station == to_station:
            final_status = "zatrzymany"
            break

        if station == "sprawdzenie":
            audit_status = str(output.get("status_audytu", "niezgodny"))
            gate = quality_gate(
                run_id, audit_status, output.get("wymiary") or {}, "", workspace, cid
            )
            if gate["gate_decision"] == "eskalacja":
                final_status = "zablokowany"
                bledy.append("Bramka jakosci: eskalacja po max iteracjach")
                auto_pilot.update_auto_pilot_state(run_id, station, "zablokowany", "eskalacja bramki")
                break
            station = gate["next_station"]
        else:
            station = exec_result["next_station"]

        if station is None:
            break
    else:
        final_status = "zablokowany"
        bledy.append(f"Przekroczono limit {_AUTO_PILOT_MAX_STEPS} krokow auto-pilota")

    auto_pilot.finish_auto_pilot(run_id, final_status)

    return {
        "run_id": run_id,
        "status": final_status,
        "stacje_wykonane": executed,
        "bledy": bledy,
        "iteracja_bramki": load_manifest(config.manifest_path(run_id, ws, cid)).iteracja_bramki,
    }


@mcp.tool
def auto_pilot_status(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zwraca status wykonania auto-pilota.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Status auto-pilota z lista wykonanych i pozostalych stacji
    """
    status = auto_pilot.get_auto_pilot_status(run_id)
    return status.model_dump()


@mcp.tool
def auto_pilot_stop(run_id: str, workspace: str = "", client_id: str = "") -> dict[str, Any]:
    """Zatrzymuje auto-pilot. Zapisuje stan, pozwala na reczna kontynuacje.

    Args:
        run_id: Identyfikator run'u
        workspace: Sciezka do workspace'a (opcjonalna). Jesli puste, uzywa cwd.
        client_id: Identyfikator klienta (opcjonalny).

    Returns:
        Status zatrzymania
    """
    return auto_pilot.stop_auto_pilot(run_id)


# =====================================================================
# UTILS
# =====================================================================


@mcp.tool
def list_stations() -> list[str]:
    """Lista wszystkich dostepnych stacji pipeline'u."""
    return list_available_skills()


@mcp.tool
def verify_integrity() -> dict[str, Any]:
    """Weryfikuje integralnosc wbudowanych skilli. Zwraca liste bledow."""
    errors = verify_skills_integrity()
    return {
        "errors": errors,
        "status": "ok" if not errors else "bledy",
        "skills_count": len(STATIONS),
    }


# =====================================================================
# 7. ZARZADZANIE KLIENTAMI (multi-tenant)
# =====================================================================


@mcp.tool
def register_client(
    client_id: str,
    display_name: str,
    aliases: list[str] | None = None,
    external_ids: dict[str, str] | None = None,
    id_fragments: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    workspace: str = "",
) -> dict[str, Any]:
    """Rejestruje nowego klienta z aliasami i identyfikatorami zewnetrznymi.

    Args:
        client_id: Kanoniczny identyfikator (slug [a-z0-9-]+)
        display_name: Nazwa wyswietlana
        aliases: Alternatywne nazwy (przypadki, skroty, literowki)
        external_ids: Identyfikatory zewnetrzne {"nip": "...", "phone": "...", "krs": "..."}
        id_fragments: Fragmenty ID do dopasowania (np. ostatnie 4 cyfry NIP)
        metadata: Dodatkowe metadane (branza, osoba kontaktowa)
        workspace: Sciezka do workspace'a (opcjonalna)
    """
    ws = _ws(workspace)
    context = client_registry.register_client(
        client_id=client_id,
        display_name=display_name,
        aliases=aliases,
        external_ids=external_ids,
        id_fragments=id_fragments,
        metadata=metadata,
        workspace=ws,
    )
    return context.model_dump()


@mcp.tool
def resolve_client(query: str, workspace: str = "") -> dict[str, Any]:
    """Rozpoznaje klienta na podstawie niejednoznacznego identyfikatora.

    Przeszukuje rejestr klientow: client_id, aliasy, identyfikatory zewnetrzne
    (NIP, telefon, KRS), fragmenty identyfikatorow. Zwraca kandydatow z
    poziomem pewnosci.

    Przy 100% pewnosci auto-przypisuje. Ponizej 100% zwraca needs_confirmation=true
    i agent powinien zapytac uzytkownika o potwierdzenie.

    Args:
        query: Identyfikator klienta (nazwa, alias, NIP, telefon, fragment)
        workspace: Sciezka do workspace'a (opcjonalna)
    """
    ws = _ws(workspace)
    result = client_registry.resolve_client(query, ws)
    return result.model_dump()


@mcp.tool
def set_active_client(client_id: str, workspace: str = "") -> dict[str, Any]:
    """Ustawia aktywnego klienta dla biezacej sesji MCP.

    Wszystkie kolejne operacje pipeline beda izolowane per ten klient,
    chyba ze jawnie nadpiszesz parametrem client_id w konkretnym narzedziu.

    Args:
        client_id: Kanoniczny identyfikator klienta (z resolve_client lub register_client)
        workspace: Sciezka do workspace'a (opcjonalna)
    """
    global _active_client_id
    ws = _ws(workspace)
    client_registry.validate_client_id(client_id)

    # Sprawdz czy klient istnieje
    context = client_registry.load_client(client_id, ws)
    if context is None:
        from .models import ClientNotFoundError
        raise ClientNotFoundError(f"Klient '{client_id}' nie istnieje. Uzyj register_client aby go utworzyc.")

    _active_client_id = client_id
    return {
        "client_id": client_id,
        "display_name": context.display_name,
        "status": "aktywny",
    }


@mcp.tool
def get_active_client() -> dict[str, Any]:
    """Zwraca aktualnie aktywnego klienta sesji MCP."""
    return {
        "client_id": _active_client_id,
        "is_set": bool(_active_client_id),
    }


@mcp.tool
def get_client_info(client_id: str, workspace: str = "") -> dict[str, Any]:
    """Zwraca metadane klienta."""
    ws = _ws(workspace)
    context = client_registry.load_client(client_id, ws)
    if context is None:
        from .models import ClientNotFoundError
        raise ClientNotFoundError(f"Klient '{client_id}' nie istnieje.")
    return context.model_dump()


@mcp.tool
def list_clients(workspace: str = "") -> list[dict[str, Any]]:
    """Lista zarejestrowanych klientow w workspace."""
    ws = _ws(workspace)
    clients = client_registry.load_all_clients(ws)
    return [
        {
            "client_id": c.client_id,
            "display_name": c.display_name,
            "status": c.status,
            "aliases_count": len(c.aliases),
            "external_ids_count": len(c.external_ids),
        }
        for c in clients
    ]


@mcp.tool
def update_client(
    client_id: str,
    updates: dict[str, Any],
    workspace: str = "",
) -> dict[str, Any]:
    """Aktualizuje aliasy, external_ids, id_fragments, metadane klienta."""
    ws = _ws(workspace)
    context = client_registry.update_client(client_id, updates, ws)
    return context.model_dump()


@mcp.tool
def archive_client(client_id: str, workspace: str = "") -> dict[str, Any]:
    """Archiwizuje klienta (zmiana statusu na zarchiwizowany)."""
    ws = _ws(workspace)
    context = client_registry.archive_client(client_id, ws)
    return context.model_dump()


@mcp.tool
def delete_client(client_id: str, workspace: str = "") -> dict[str, Any]:
    """Usuwa klienta i wszystkie jego dane (GDPR right to be forgotten).

    Usuwa: context.yaml, pipeline-runs/, rag/, memory/.
    """
    ws = _ws(workspace)
    result = client_registry.delete_client(client_id, ws)
    # Wyczysc aktywnego klienta jesli to byl on
    global _active_client_id
    if _active_client_id == client_id:
        _active_client_id = ""
    return result


# =====================================================================
# 8. WIEDZA WSPOLDZIELONA (cross-client)
# =====================================================================


@mcp.tool
def save_shared_knowledge(
    knowledge_id: str,
    category: str,
    title: str,
    content: str,
    source: str = "",
    tags: list[str] | None = None,
    workspace: str = "",
) -> dict[str, Any]:
    """Zapisuje wpis wiedzy wspoldzielonej (cross-client).

    Args:
        knowledge_id: Identyfikator wpisu (slug)
        category: Kategoria ("decision", "pattern", "pitfall")
        title: Tytul
        content: Tresc
        source: Zrodlo wiedzy
        tags: Tagi
        workspace: Sciezka do workspace'a (opcjonalna)
    """
    ws = _ws(workspace)
    entry = knowledge.save_shared_knowledge(
        knowledge_id=knowledge_id,
        category=category,
        title=title,
        content=content,
        source=source,
        tags=tags,
        workspace=ws,
    )
    return entry.model_dump()


@mcp.tool
def get_shared_knowledge(
    knowledge_id: str, category: str, workspace: str = ""
) -> dict[str, Any]:
    """Odczytuje wpis wiedzy wspoldzielonej."""
    ws = _ws(workspace)
    entry = knowledge.get_shared_knowledge(knowledge_id, category, ws)
    if entry is None:
        raise PipelineError(f"Wiedza '{knowledge_id}' w kategorii '{category}' nie istnieje.")
    return entry.model_dump()


@mcp.tool
def search_shared_knowledge(
    query: str, category: str = "", workspace: str = ""
) -> list[dict[str, Any]]:
    """Wyszukuje w wiedzy wspoldzielonej."""
    ws = _ws(workspace)
    return knowledge.search_shared_knowledge(query, category, ws)


@mcp.tool
def list_shared_knowledge(
    category: str = "", workspace: str = ""
) -> list[dict[str, Any]]:
    """Lista wszystkich wpisow wiedzy wspoldzielonej."""
    ws = _ws(workspace)
    return knowledge.list_shared_knowledge(category, ws)


# =====================================================================
# 9. PAMIEC AI per-klient
# =====================================================================


@mcp.tool
def save_client_memory(
    topic: str,
    content: str,
    client_id: str = "",
    memory_id: str = "",
    tags: list[str] | None = None,
    workspace: str = "",
) -> dict[str, Any]:
    """Zapisuje wpis pamieci AI per-klient.

    Args:
        topic: Temat wpisu
        content: Tresc pamieci
        client_id: Identyfikator klienta (opcjonalny, uzywa aktywnego jesli pusty)
        memory_id: Identyfikator wpisu (opcjonalny, auto-generowany)
        tags: Tagi
        workspace: Sciezka do workspace'a (opcjonalna)
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not cid:
        raise PipelineError("client_id jest wymagany dla pamieci per-klient. Uzyj set_active_client lub podaj client_id.")
    entry = client_memory.save_client_memory(
        topic=topic, content=content, client_id=cid,
        memory_id=memory_id, tags=tags, workspace=ws,
    )
    return entry.model_dump()


@mcp.tool
def get_client_memory(
    memory_id: str, client_id: str = "", workspace: str = ""
) -> dict[str, Any]:
    """Odczytuje wpis pamieci per-klient."""
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not cid:
        raise PipelineError("client_id jest wymagany.")
    entry = client_memory.get_client_memory(memory_id, cid, ws)
    if entry is None:
        raise PipelineError(f"Pamiec '{memory_id}' nie istnieje dla klienta '{cid}'.")
    return entry.model_dump()


@mcp.tool
def list_client_memories(
    client_id: str = "", workspace: str = ""
) -> list[dict[str, Any]]:
    """Lista wpisow pamieci per-klient."""
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not cid:
        raise PipelineError("client_id jest wymagany.")
    return client_memory.list_client_memories(cid, ws)


@mcp.tool
def save_shared_memory(
    topic: str,
    content: str,
    memory_id: str = "",
    tags: list[str] | None = None,
    workspace: str = "",
) -> dict[str, Any]:
    """Zapisuje wpis pamieci AI wspoldzielonej (cross-client)."""
    ws = _ws(workspace)
    entry = client_memory.save_shared_memory(
        topic=topic, content=content, memory_id=memory_id, tags=tags, workspace=ws,
    )
    return entry.model_dump()


@mcp.tool
def get_shared_memory(
    memory_id: str, workspace: str = ""
) -> dict[str, Any]:
    """Odczytuje wpis pamieci wspoldzielonej."""
    ws = _ws(workspace)
    entry = client_memory.get_shared_memory(memory_id, ws)
    if entry is None:
        raise PipelineError(f"Pamiec wspoldzielona '{memory_id}' nie istnieje.")
    return entry.model_dump()


@mcp.tool
def search_client_memories(
    query: str, client_id: str = "", include_shared: bool = True, workspace: str = ""
) -> list[dict[str, Any]]:
    """Wyszukuje w pamieci per-klient (i opcjonalnie wspoldzielonej)."""
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    if not cid:
        raise PipelineError("client_id jest wymagany.")
    return client_memory.search_client_memories(query, cid, include_shared, ws)


# =====================================================================
# 10. RAG per-klient
# =====================================================================


@mcp.tool
def index_client_document(
    doc_id: str,
    content: str,
    title: str = "",
    metadata: dict[str, Any] | None = None,
    client_id: str = "",
    workspace: str = "",
) -> dict[str, Any]:
    """Indeksuje dokument w RAG per-klient (lub wspoldzielonym gdy client_id puste).

    Args:
        doc_id: Identyfikator dokumentu
        content: Tresc dokumentu
        title: Tytul dokumentu
        metadata: Metadane dokumentu
        client_id: Identyfikator klienta (opcjonalny). Pusty = RAG wspoldzielony.
        workspace: Sciezka do workspace'a (opcjonalna)
    """
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    return rag.index_client_document(
        doc_id=doc_id, content=content, title=title,
        metadata=metadata, client_id=cid, workspace=ws,
    )


@mcp.tool
def search_client_rag(
    query: str, client_id: str = "", limit: int = 10, workspace: str = ""
) -> list[dict[str, Any]]:
    """Wyszukuje w RAG per-klient (i wspoldzielonym)."""
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    return rag.search_client_rag(query, cid, limit, workspace)


@mcp.tool
def search_shared_rag(
    query: str, limit: int = 10, workspace: str = ""
) -> list[dict[str, Any]]:
    """Wyszukuje wylacznie we wspoldzielonym RAG."""
    ws = _ws(workspace)
    return rag.search_shared_rag(query, limit, workspace)


@mcp.tool
def list_rag_documents(
    client_id: str = "", workspace: str = ""
) -> list[dict[str, Any]]:
    """Lista dokumentow w RAG per-klient (lub wspoldzielonym)."""
    ws = _ws(workspace)
    cid = _resolve_client_id(client_id)
    return rag.list_rag_documents(cid, workspace)


# =====================================================================
# PROMPTS - auto-inicjalizacja pipeline'u
# =====================================================================


@mcp.prompt
async def pipeline_start(
    zamiar: str,
    kontekst: str = "",
    workspace: str = "",
    client_id: str = "",
) -> list[Message]:
    """Auto-start pipeline'u. Wywoluje start_run i zwraca instrukcje do pierwszej stacji.

    Args:
        zamiar: Cel zadania od uzytkownika (wymagany)
        kontekst: Dodatkowy kontekst zadania (opcjonalny)
        workspace: Sciezka do workspace'a (opcjonalna, domyslnie cwd)
        client_id: Identyfikator klienta (opcjonalny, domyslnie aktywny klient sesji)
    """
    result = await mcp.call_tool("start_run", {
        "zamiar": zamiar,
        "kontekst": kontekst,
        "workspace": workspace,
        "client_id": client_id,
    })
    data = result.structured_content or {}
    run_id = data.get("run_id", "")
    manifest_path = data.get("manifest_path", "")
    resolved_cid = data.get("client_id", "")

    contract_result = await mcp.call_tool("get_station_contract", {
        "run_id": run_id,
        "station": "inicjuj",
        "workspace": workspace,
        "client_id": client_id,
    })
    contract = contract_result.structured_content or {}
    skill_prompt = contract.get("skill_prompt", "")
    required_input = contract.get("required_input", [])
    output_fields = contract.get("output", [])

    client_info = f"\nKlient: {resolved_cid}" if resolved_cid else "\nTryb: legacy (bez izolacji klienta)"

    return [
        Message(
            f"Pipeline uruchomiony automatycznie.\n"
            f"Run ID: {run_id}\n"
            f"Manifest: {manifest_path}{client_info}\n\n"
            f"Przystapujesz do stacji: inicjuj (Inicjacja)\n\n"
            f"Wymagane wejscie: {required_input}\n"
            f"Oczekiwane wyjscie: {output_fields}\n\n"
            f"SKILL STACJI inicjuj:\n{skill_prompt}\n\n"
            f"Wykonaj stacje inicjuj na podstawie powyzszego skilla.\n"
            f"Po zakonczeniu wywolaj execute_station z run_id='{run_id}', "
            f"station='inicjuj' i output zawierajacym pola: {output_fields}.\n"
            f"Nastepnie sprawdz next_station i validation z wyniku."
        ),
        Message(
            "Rozpoczynam prace zgodnie z pipeline. Najpierw wykonam stacje inicjuj.",
            role="assistant",
        ),
    ]


@mcp.prompt
async def pipeline_continue(
    run_id: str,
    workspace: str = "",
    client_id: str = "",
) -> list[Message]:
    """Wznawia istniejacy run pipeline'u.

    Args:
        run_id: Identyfikator run'u do wznowienia
        workspace: Sciezka do workspace'a (opcjonalna, domyslnie cwd)
        client_id: Identyfikator klienta (opcjonalny)
    """
    result = await mcp.call_tool("resume_run", {
        "run_id": run_id,
        "workspace": workspace,
        "client_id": client_id,
    })
    data = result.structured_content or {}
    stacja_wznowienia = data.get("stacja_wznowienia", "")
    walidacja = data.get("walidacja", {})

    skill_prompt = ""
    required_input = []
    output_fields = []

    if stacja_wznowienia and stacja_wznowienia != "zakonczony":
        contract_result = await mcp.call_tool("get_station_contract", {
            "run_id": run_id,
            "station": stacja_wznowienia,
            "workspace": workspace,
            "client_id": client_id,
        })
        contract = contract_result.structured_content or {}
        skill_prompt = contract.get("skill_prompt", "")
        required_input = contract.get("required_input", [])
        output_fields = contract.get("output", [])

    status_msg = (
        f"Run '{run_id}' wznowiony.\n"
        f"Nastepna stacja: {stacja_wznowienia}\n"
        f"Walidacja wejscia: {walidacja}\n\n"
    )

    if stacja_wznowienia == "zakonczony":
        status_msg += "Run jest juz zakonczony. Wywolaj close_run aby sfinalizowac."
    else:
        status_msg += (
            f"SKILL STACJI {stacja_wznowienia}:\n{skill_prompt}\n\n"
            f"Wymagane wejscie: {required_input}\n"
            f"Oczekiwane wyjscie: {output_fields}\n\n"
            f"Wykonaj stacje {stacja_wznowienia} i wywolaj execute_station "
            f"z run_id='{run_id}', station='{stacja_wznowienia}'."
        )

    return [
        Message(status_msg),
        Message(
            f"Wznawiam prace nad run'em {run_id}. Przystepuje do stacji {stacja_wznowienia}.",
            role="assistant",
        ),
    ]


def main() -> None:
    """Punkt wejscia dla pipeline-mcp."""
    import sys
    logging.basicConfig(
        level=get_config().log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()
