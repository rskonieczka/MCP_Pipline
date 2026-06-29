"""Bramka jakosci: ocena, petla zwrotna, eskalacja."""
from __future__ import annotations

from typing import Any

from .manifest import increment_gate_iteration, load_manifest, save_manifest, update_station_status
from .models import GateMaxIterationsError, Manifest, QualityGateResult
from .routing import get_post_gate_station

MAX_GATE_ITERATIONS = 2


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

    if audit_status == "zgodny":
        next_station = get_post_gate_station(manifest.sciezka)
        return QualityGateResult(
            run_id=run_id,
            gate_decision="przejdz",
            iteracja_bramki=iteration,
            next_station=next_station,
            komunikat=f"Bramka zgodna. Przejscie do stacji '{next_station}'.",
        )

    # niezgodny
    if iteration >= MAX_GATE_ITERATIONS:
        return QualityGateResult(
            run_id=run_id,
            gate_decision="eskylacja",
            iteracja_bramki=iteration,
            next_station=None,
            komunikat=(
                f"Osiagnieto max {MAX_GATE_ITERATIONS} iteracje bramki. "
                "Wymagana interwencja uzytkownika."
            ),
        )

    # powrot - zwieksz iteracje
    target = loop_target or infer_loop_target(audit_wymiary)
    new_iteration = iteration + 1
    manifest = increment_gate_iteration(manifest)

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


def infer_loop_target(wymiary: dict[str, Any]) -> str:
    """Wnioskuje cel powrotu na podstawie wymiarow audytu."""
    # Jesli niezgodnosc w Zgodnosc/Poprawnosc merytoryczna -> dobierz
    # Jesli niezgodnosc w Kompletnosc/Poprawnosc logiczna -> planuj
    if wymiary.get("Zgodnosc") == "niezgodny" or \
       wymiary.get("Poprawnosc merytoryczna") == "niezgodny":
        return "dobierz"
    return "planuj"


def get_gate_history(run_id: str, manifest: Manifest) -> dict[str, Any]:
    """Zwraca historie iteracji bramki."""
    return {
        "run_id": run_id,
        "iteracja_aktualna": manifest.iteracja_bramki,
        "max_iteracje": MAX_GATE_ITERATIONS,
        "pozostale_iteracje": max(0, MAX_GATE_ITERATIONS - manifest.iteracja_bramki),
        "historia": [],  # TODO: sledzenie historii w przyszlosci
    }
