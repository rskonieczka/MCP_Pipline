"""Bramka jakosci: ocena, petla zwrotna, eskalacja."""
from __future__ import annotations

from typing import Any

from .manifest import increment_gate_iteration
from .models import GateHistoryEntry, Manifest, PipelineError, QualityGateResult
from .routing import get_post_gate_station, get_station_sequence, is_station_in_path

MAX_GATE_ITERATIONS = 2

# U7: dozwolone wartosci audit_status
_VALID_AUDIT_STATUSES = ("zgodny", "niezgodny")


def reset_stations_for_loop(manifest: Manifest, loop_target: str) -> Manifest:
    """Resetuje statusy stacji od loop_target do konca sciezki na 'w_trakcie'.

    Umozliwia ponowne wykonanie stacji w petli zwrotnej bramki bez
    StationAlreadyDoneError. Stacje spoza sciezki nie sa ruszane.
    """
    sequence = get_station_sequence(manifest.sciezka)
    if loop_target not in sequence:
        return manifest
    to_reset = set(sequence[sequence.index(loop_target):])
    for s in manifest.stacje:
        if s.stacja in to_reset and s.status == "zakonczona":
            s.status = "w_trakcie"
    return manifest


def evaluate_gate(
    run_id: str,
    manifest: Manifest,
    audit_status: str,
    audit_wymiary: dict[str, Any] | None = None,
    loop_target: str = "",
) -> QualityGateResult:
    """Ocenia bramke jakosci po stacji sprawdzenie."""
    audit_wymiary = audit_wymiary or {}
    iteration = manifest.iteracja_bramki

    # U7: walidacja audit_status - odrzuc nieprawidlowe wartosci
    if audit_status not in _VALID_AUDIT_STATUSES:
        raise PipelineError(
            f"Nieprawidlowy audit_status '{audit_status}'. "
            f"Dostepne: {list(_VALID_AUDIT_STATUSES)}"
        )

    if audit_status == "zgodny":
        next_station = get_post_gate_station(manifest.sciezka)
        komunikat = (
            f"Bramka zgodna. Przejscie do stacji '{next_station}'."
            if next_station
            else "Bramka zgodna. Sciezka zakonczona - wywolaj close_run."
        )
        # U4: zapisz historie iteracji
        manifest.historia_bramki.append(GateHistoryEntry(
            iteracja=iteration,
            audit_status=audit_status,
            gate_decision="przejdz",
        ))
        return QualityGateResult(
            run_id=run_id,
            gate_decision="przejdz",
            iteracja_bramki=iteration,
            next_station=next_station,
            komunikat=komunikat,
        )

    # niezgodny
    if iteration >= MAX_GATE_ITERATIONS:
        manifest.status_runu = "zablokowany"  # type: ignore
        # U4: zapisz historie eskalacji
        manifest.historia_bramki.append(GateHistoryEntry(
            iteracja=iteration,
            audit_status=audit_status,
            gate_decision="eskalacja",
        ))
        return QualityGateResult(
            run_id=run_id,
            gate_decision="eskalacja",
            iteracja_bramki=iteration,
            next_station=None,
            komunikat=(
                f"Osiagnieto max {MAX_GATE_ITERATIONS} iteracje bramki. "
                "Run oznaczony jako zablokowany. Wymagana interwencja uzytkownika."
            ),
        )

    # powrot - zwieksz iteracje
    target = loop_target or infer_loop_target(audit_wymiary, manifest.sciezka)
    if not is_station_in_path(target, manifest.sciezka):
        target = infer_loop_target(audit_wymiary, manifest.sciezka)
    new_iteration = iteration + 1
    manifest = increment_gate_iteration(manifest)
    manifest = reset_stations_for_loop(manifest, target)
    # U4: zapisz historie powrotu
    manifest.historia_bramki.append(GateHistoryEntry(
        iteracja=new_iteration,
        audit_status=audit_status,
        loop_target=target,
        gate_decision="powrot",
    ))

    return QualityGateResult(
        run_id=run_id,
        gate_decision="powrot",
        iteracja_bramki=new_iteration,
        next_station=target,
        loop_target=target,
        max_iteracje=MAX_GATE_ITERATIONS,
        komunikat=(
            f"Bramka niezgodna (iteracja {new_iteration}/{MAX_GATE_ITERATIONS}). "
            f"Powrot do stacji '{target}'."
        ),
    )


def infer_loop_target(wymiary: dict[str, Any], sciezka: str = "pelny") -> str:
    """Wnioskuje cel powrotu na podstawie wymiarow audytu i sciezki."""
    # Jesli niezgodnosc w Zgodnosc/Poprawnosc merytoryczna -> dobierz
    # Jesli niezgodnosc w Kompletnosc/Poprawnosc logiczna -> planuj
    if wymiary.get("Zgodnosc") == "niezgodny" or \
       wymiary.get("Poprawnosc merytoryczna") == "niezgodny":
        return "dobierz"
    # Sciezka szybka nie zawiera 'planuj' - jedynym celem petli jest 'dobierz'
    if not is_station_in_path("planuj", sciezka):
        return "dobierz"
    return "planuj"


def get_gate_history(run_id: str, manifest: Manifest) -> dict[str, Any]:
    """Zwraca historie iteracji bramki."""
    # U4: zwracaj faktyczna historie z manifestu zamiast pustej listy
    return {
        "run_id": run_id,
        "iteracja_aktualna": manifest.iteracja_bramki,
        "max_iteracje": MAX_GATE_ITERATIONS,
        "pozostale_iteracje": max(0, MAX_GATE_ITERATIONS - manifest.iteracja_bramki),
        "historia": [e.model_dump() for e in manifest.historia_bramki],
    }
