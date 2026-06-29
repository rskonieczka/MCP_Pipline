"""Serwer FastMCP z narzedziami pipeline'u.

Glowny punkt wejscia. Rejestruje wszystkie narzedzia MCP.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from .config import get_config
from .envelope import (
    accumulate_state,
    add_station_relations,
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
    ContractValidationResult,
    Envelope,
    ExecuteStationResult,
    Manifest,
    NextStationResult,
    PipelineError,
    QualityGateResult,
    RunNotFoundError,
    RunClosedError,
    StartRunResult,
    StationContract,
    StationNotFoundError,
    StationAlreadyDoneError,
)
from .checkpoint import (
    get_latest_checkpoint,
    list_checkpoints,
    load_checkpoint,
    save_checkpoint,
    save_envelope_final,
)
from .contracts import get_mapping_for_station, validate_input
from .quality_gate import evaluate_gate, get_gate_history
from .routing import (
    determine_path,
    get_next_station as routing_get_next_station,
    get_post_gate_station,
    get_station_sequence,
    is_last_station,
    is_station_in_path,
)
from .stations import STATIONS, get_station, station_exists
from .skills_loader import (
    get_skill_prompt,
    list_available_skills,
    load_skill,
    verify_skills_integrity,
)

# Auto-pilot (lazy import zeby uniknac bledow jesli LLM nie skonfigurowany)
from . import auto_pilot

logger = logging.getLogger(__name__)

# Singleton serwera
mcp = FastMCP("Pipeline MCP Server")


def _generate_run_id(zamiar: str) -> str:
    """Generuje run_id w formacie <YYYY-MM-DD>-<skrot-zamiaru>."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    # Skrot zamiaru: pierwsze 3 slowa, max 30 znakow, bez polskich znakow
    import unicodedata
    normalized = unicodedata.normalize("NFKD", zamiar)
    ascii_zamiar = normalized.encode("ascii", "ignore").decode()
    words = ascii_zamiar.lower().split()
    skrot = "-".join(words[:3])[:30]
    skrot = skrot.replace(".", "").replace(",", "").replace("?", "")
    return f"{date_str}-{skrot}" if skrot else f"{date_str}-run"


def _load_run(run_id: str, workspace: str | None = None) -> tuple[Manifest, Envelope]:
    """Odczytuje manifest i ostatnia koperte dla run'u."""
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id, workspace))

    # Zaladuj ostatni checkpoint
    latest = get_latest_checkpoint(run_id, workspace)
    if latest:
        _, envelope = latest
    else:
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka)

    return manifest, envelope


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
) -> dict[str, Any]:
    """Tworzy nowy run pipeline'u. Generuje run_id, tworzy manifest i pusta koperte.

    Args:
        zamiar: Zamiar uzytkownika (wymagany)
        kontekst: Kontekst zadania (opcjonalny)
        zrodla: Zrodla bazowe (opcjonalne)
        tryb_inicjacji: "szybki" lub "pelny" (domyslnie "pelny")

    Returns:
        Slownik z run_id, first_station, manifest_path, envelope
    """
    if not zamiar:
        raise PipelineError("Zamiar jest wymagany")

    config = get_config()
    run_id = _generate_run_id(zamiar)

    # Utworz katalog run'u
    run_dir = config.run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Utworz manifest (sciezka domyslnie pelny, inicjuj ustali ostateczna)
    manifest = create_manifest(run_id, zamiar, sciezka="pelny")
    manifest = add_station_to_manifest(manifest, "inicjuj", "w_trakcie")
    save_manifest(manifest, config.manifest_path(run_id))

    # Utworz pusta koperte
    envelope = create_envelope(run_id, zamiar, sciezka="pelny")

    return {
        "run_id": run_id,
        "first_station": "inicjuj",
        "manifest_path": str(config.manifest_path(run_id)),
        "envelope": envelope.model_dump(),
    }


@mcp.tool
def get_run_status(run_id: str) -> dict[str, Any]:
    """Zwraca status run'u na podstawie manifestu.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Status run'u z lista stacji i ich statusami
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))

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
    }


@mcp.tool
def list_runs(status_filter: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Lista wszystkich run'ow w katalogu persystencji.

    Args:
        status_filter: Filtr statusu ("", "w_trakcie", "zakonczony", "zablokowany")
        limit: Maksymalna liczba wynikow

    Returns:
        Lista run'ow z metadanymi
    """
    config = get_config()
    runs: list[dict[str, Any]] = []

    if not config.runs_dir.exists():
        return []

    for run_dir in sorted(config.runs_dir.iterdir(), reverse=True):
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
            })

            if len(runs) >= limit:
                break
        except Exception as e:
            logger.warning(f"Blad odczytu run'u {run_dir.name}: {e}")

    return runs


@mcp.tool
def resume_run(run_id: str) -> dict[str, Any]:
    """Wznawia run od ostatniej zakonczonej stacji.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Stacja wznowienia i zaladowana koperta
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))
    _ensure_run_open(manifest)

    last_station = get_last_completed_station(manifest)
    if not last_station:
        # Brak zakonczonych stacji - zaczynamy od inicjuj
        return {
            "run_id": run_id,
            "stacja_wznowienia": "inicjuj",
            "envelope": create_envelope(run_id, manifest.zamiar, manifest.sciezka).model_dump(),
            "walidacja": {"status": "gotowy"},
        }

    # Zaladuj ostatni checkpoint
    latest = get_latest_checkpoint(run_id)
    if not latest:
        raise RunNotFoundError(f"Brak checkpointu dla run'u {run_id}")

    _, envelope = latest

    # Wyznacz nastepna stacje
    next_station = routing_get_next_station(last_station, manifest.sciezka)

    # Waliduj wejscie nastepnej stacji
    walidacja = validate_input(next_station, envelope) if next_station else None

    return {
        "run_id": run_id,
        "stacja_wznowienia": next_station or "zakonczony",
        "envelope": envelope.model_dump(),
        "walidacja": walidacja.model_dump() if walidacja else None,
    }


@mcp.tool
def close_run(run_id: str) -> dict[str, Any]:
    """Zamyka run. Zapisuje ostateczna koperte, oznacza run jako zakonczony.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Status zamkniecia
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))

    # Zaladuj ostatnia koperte
    latest = get_latest_checkpoint(run_id)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka)

    # Zapisz ostateczna koperte
    envelope_path = save_envelope_final(run_id, envelope)

    # Zamknij manifest
    manifest = close_manifest(manifest)
    save_manifest(manifest, config.manifest_path(run_id))

    # Zamknij wezel Run w Memgraph
    from . import memgraph
    memgraph.close_run_node(run_id)

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
) -> dict[str, Any]:
    """Rejestruje wynik wykonania stacji przez agenta (tryb manual).

    Aktualizuje koperte, zapisuje checkpoint, wyznacza nastepna stacje.

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji (np. "inicjuj")
        output: Wyjscie stacji (pola kontraktu wyjsciowego)
        skip_validation: Pomin walidacje kontraktu (domyslnie False)

    Returns:
        Status wykonania, nastepna stacja, walidacja, sciezka checkpointu
    """
    if not station_exists(station):
        raise StationNotFoundError(f"Stacja '{station}' nie istnieje")

    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))
    _ensure_run_open(manifest)

    # Sprawdz czy stacja juz zakonczona
    existing_status = get_station_status(manifest, station)
    if existing_status == "zakonczona" and not skip_validation:
        raise StationAlreadyDoneError(
            f"Stacja '{station}' juz zakonczona w run'u {run_id}"
        )

    # Zaladuj aktualna koperte
    latest = get_latest_checkpoint(run_id)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka)

    # Aktualizuj koperte
    envelope = update_station_fields(envelope, station, output)
    envelope = accumulate_state(envelope, station, output)
    envelope = add_station_relations(envelope, station, run_id)

    # Jesli inicjuj - ustal sciezke na podstawie klasyfikacji
    if station == "inicjuj":
        klasyfikacja = output.get("klasyfikacja", "rutynowe")
        sciezka = determine_path(klasyfikacja)
        envelope.sciezka = sciezka  # type: ignore
        manifest.sciezka = sciezka  # type: ignore

    # Waliduj wejscie nastepnej stacji
    next_station = routing_get_next_station(station, envelope.sciezka)
    validation = validate_input(next_station, envelope) if next_station else None

    if validation:
        envelope.walidacja.stacja_docelowa = next_station or ""
        envelope.walidacja.pola_wymagane = validation.pola_wymagane
        envelope.walidacja.pola_obecne = validation.pola_obecne
        envelope.walidacja.pola_brakujace = validation.pola_brakujace
        envelope.walidacja.status = validation.status  # type: ignore
        envelope.walidacja.akcja_naprawcza = validation.akcja_naprawcza

    # Zapisz checkpoint
    checkpoint_path = save_checkpoint(run_id, station, envelope)

    # Aktualizuj manifest
    manifest = update_station_status(manifest, station, "zakonczona", checkpoint_path)
    save_manifest(manifest, config.manifest_path(run_id))

    # Zapisz relacje do Memgraph
    from . import memgraph
    memgraph_written = memgraph.write_relations_from_envelope(run_id, envelope)

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
def get_next_station(run_id: str) -> dict[str, Any]:
    """Zwraca nastepna stacje na podstawie aktualnego stanu run'u.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Nastepna stacja, sciezka, czy ostatnia stacja
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))

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
    is_last = is_last_station(last_station, manifest.sciezka) if next_station is None else False

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
    run_id: str,
    station: str,
    reason: str = "",
) -> dict[str, Any]:
    """Ręczne pominiecie stacji (tryb hybrydowy).

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji do pominiecia
        reason: Powod pominiecia

    Returns:
        Status pominiecia i nastepna stacja
    """
    if not station_exists(station):
        raise StationNotFoundError(f"Stacja '{station}' nie istnieje")

    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))
    _ensure_run_open(manifest)

    # Sprawdz czy stacja jest w sciezce
    if is_station_in_path(station, manifest.sciezka):
        raise PipelineError(
            f"Stacja '{station}' jest w sciezce '{manifest.sciezka}' i nie powinna byc pomijana. "
            "Pominiecie dozwolone tylko dla stacji opcjonalnych."
        )

    # Oznacz jako pominieta
    manifest = update_station_status(manifest, station, "pominieta")
    save_manifest(manifest, config.manifest_path(run_id))

    # Wyznacz nastepna stacje
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
def get_station_contract(run_id: str, station: str) -> dict[str, Any]:
    """Zwraca kontrakt I/O dla stacji: wymagane i opcjonalne pola, mappowanie, prompt skilla.

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji

    Returns:
        Kontrakt stacji z promptem wbudowanego skilla
    """
    if not station_exists(station):
        raise StationNotFoundError(f"Stacja '{station}' nie istnieje")

    station_def = get_station(station)
    mapping = get_mapping_for_station(station)

    # Zaladuj prompt skilla
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
def get_envelope(run_id: str) -> dict[str, Any]:
    """Zwraca aktualna koperte run'u.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Pelna koperta run'u
    """
    latest = get_latest_checkpoint(run_id)
    if not latest:
        config = get_config()
        manifest = load_manifest(config.manifest_path(run_id))
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka)
        return envelope.model_dump()

    _, envelope = latest
    return envelope.model_dump()


@mcp.tool
def update_envelope(
    run_id: str,
    section: str,
    fields: dict[str, Any],
    merge: bool = True,
) -> dict[str, Any]:
    """Ręczna aktualizacja koperty (tryb hybrydowy).

    Args:
        run_id: Identyfikator run'u
        section: Sekcja koperty ("stan", "pola_stacji.<stacja>", "walidacja", "relacje")
        fields: Pola do aktualizacji
        merge: True = scal z istniejacymi, False = zastap

    Returns:
        Zaktualizowana koperta (skrot)
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))
    _ensure_run_open(manifest)

    latest = get_latest_checkpoint(run_id)
    envelope = latest[1] if latest else create_envelope(run_id, manifest.zamiar, manifest.sciezka)

    # Parsuj section
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
    else:
        raise PipelineError(f"Nieznana sekcja koperty: '{section}'")

    # Zapisz zaktualizowana koperte jako checkpoint
    save_checkpoint(run_id, "_manual_update", envelope)

    return {
        "run_id": run_id,
        "updated_fields": list(fields.keys()),
        "envelope_summary": get_envelope_summary(envelope),
    }


@mcp.tool
def validate_contract(
    run_id: str,
    target_station: str,
) -> dict[str, Any]:
    """Waliduje czy wejscie stacji docelowej jest kompletne.

    Args:
        run_id: Identyfikator run'u
        target_station: Stacja docelowa do walidacji

    Returns:
        Wynik walidacji kontraktu
    """
    if not station_exists(target_station):
        raise StationNotFoundError(f"Stacja '{target_station}' nie istnieje")

    latest = get_latest_checkpoint(run_id)
    if not latest:
        config = get_config()
        manifest = load_manifest(config.manifest_path(run_id))
        envelope = create_envelope(run_id, manifest.zamiar, manifest.sciezka)
    else:
        _, envelope = latest

    result = validate_input(target_station, envelope)
    return result.model_dump()


# =====================================================================
# 4. QUALITY GATE
# =====================================================================


@mcp.tool
def quality_gate(
    run_id: str,
    audit_status: str,
    audit_wymiary: dict[str, Any] | None = None,
    loop_target: str = "",
) -> dict[str, Any]:
    """Ocenia bramke jakosci po stacji sprawdzenie.

    Args:
        run_id: Identyfikator run'u
        audit_status: "zgodny" lub "niezgodny"
        audit_wymiary: Wymiary audytu (opcjonalne)
        loop_target: Gdzie wrocic przy niezgodnym ("dobierz" lub "planuj")

    Returns:
        Decyzja bramki, nastepna stacja, iteracja
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))
    _ensure_run_open(manifest)

    result = evaluate_gate(
        run_id, manifest, audit_status, audit_wymiary or {}, loop_target
    )

    # Zapisz zaktualizowany manifest (iteracja bramki)
    save_manifest(manifest, config.manifest_path(run_id))

    return result.model_dump()


@mcp.tool
def get_gate_iterations(run_id: str) -> dict[str, Any]:
    """Zwraca historie iteracji bramki dla run'u.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Aktualna iteracja, max iteracje, pozostale
    """
    config = get_config()
    manifest = load_manifest(config.manifest_path(run_id))
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
) -> dict[str, Any]:
    """Ręczny zapis checkpointu (normalnie wywolywane automatycznie przez execute_station).

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji
        envelope: Koperta do zapisania
        suffix: Sufiks nazwy pliku (np. "_iter1")

    Returns:
        Sciezka zapisanego checkpointu
    """
    env = Envelope(**envelope)
    path = save_checkpoint(run_id, station, env, suffix)
    return {
        "run_id": run_id,
        "station": station,
        "checkpoint_path": path,
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool
def load_checkpoint_tool(
    run_id: str,
    station: str,
    suffix: str = "",
) -> dict[str, Any]:
    """Odczyt checkpointu stacji.

    Args:
        run_id: Identyfikator run'u
        station: Nazwa stacji
        suffix: Sufiks nazwy pliku (np. "_iter1")

    Returns:
        Koperta z checkpointu
    """
    env = load_checkpoint(run_id, station, suffix)
    return {
        "run_id": run_id,
        "station": station,
        "envelope": env.model_dump(),
        "timestamp": env.timestamp,
    }


@mcp.tool
def list_checkpoints_tool(run_id: str) -> list[dict[str, Any]]:
    """Lista wszystkich checkpointow dla run'u.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Lista checkpointow z metadanymi
    """
    return list_checkpoints(run_id)


# =====================================================================
# 6. AUTO-PILOT
# =====================================================================


@mcp.tool
def auto_pilot_start(
    run_id: str,
    from_station: str = "",
    to_station: str = "",
    max_gate_iterations: int = 2,
) -> dict[str, Any]:
    """Uruchamia tryb auto-pilot. Serwer sekwencyjnie wywoluje LLM dla kazdej stacji.

    Args:
        run_id: Identyfikator run'u
        from_station: Stacja startowa (puste = od nastepnej stacji)
        to_station: Stacja koncowa (puste = do konca pipeline'u)
        max_gate_iterations: Max iteracji bramki (domyslnie 2)

    Returns:
        Status uruchomienia auto-pilota
    """
    return auto_pilot.start_auto_pilot(
        run_id, from_station, to_station, max_gate_iterations
    )


@mcp.tool
def auto_pilot_status(run_id: str) -> dict[str, Any]:
    """Zwraca status wykonania auto-pilota.

    Args:
        run_id: Identyfikator run'u

    Returns:
        Status auto-pilota z lista wykonanych i pozostalych stacji
    """
    status = auto_pilot.get_auto_pilot_status(run_id)
    return status.model_dump()


@mcp.tool
def auto_pilot_stop(run_id: str) -> dict[str, Any]:
    """Zatrzymuje auto-pilot. Zapisuje stan, pozwala na reczna kontynuacje.

    Args:
        run_id: Identyfikator run'u

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
