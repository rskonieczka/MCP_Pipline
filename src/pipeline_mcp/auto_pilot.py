"""Tryb auto-pilot: sekwencyjne wywolywanie LLM per stacja."""
from __future__ import annotations

import logging
import re
from typing import Any

import yaml

from .config import get_config
from .llm import get_provider, is_configured
from .models import (
    AutoPilotStatus,
    Envelope,
    LLMNotConfiguredError,
)
from .quality_gate import MAX_GATE_ITERATIONS
from .skills_loader import get_skill_prompt

logger = logging.getLogger(__name__)

# Stan auto-pilota w pamieci (run_id -> status)
_auto_pilot_state: dict[str, dict[str, Any]] = {}


def start_auto_pilot(
    run_id: str,
    from_station: str = "",
    to_station: str = "",
    max_gate_iterations: int = MAX_GATE_ITERATIONS,
) -> dict[str, Any]:
    """Uruchamia tryb auto-pilot."""
    if not is_configured():
        raise LLMNotConfiguredError(
            "Auto-pilot wymaga skonfigurowanego LLM. Ustaw PIPELINE_LLM_API_KEY."
        )

    _auto_pilot_state[run_id] = {
        "status": "uruchomiony",
        "stacja_aktualna": from_station or "inicjuj",
        "stacje_wykonane": [],
        "stacje_pozostale": [],
        "iteracja_bramki": 0,
        "bledy": [],
        "to_station": to_station,
        "max_gate_iterations": max_gate_iterations,
        "laczny_koszt": {"tokens_wejscie": 0, "tokens_wyjscie": 0, "koszt_usd": 0.0},
        "ostatni_llm_koszt": None,
    }

    return {
        "run_id": run_id,
        "status": "uruchomiony",
        "from_station": from_station or "inicjuj",
        "to_station": to_station or None,
        "auto_pilot_id": run_id,
    }


def execute_station_with_llm(
    run_id: str,
    station: str,
    envelope: Envelope,
) -> tuple[dict[str, Any], Envelope]:
    """Wywoluje LLM z promptem stacji i parsuje wyjscie.

    Zwraca (station_output, updated_envelope).
    """
    provider = get_provider()
    config = get_config()

    # Buduj prompt
    envelope_dict = envelope.model_dump()
    prompt = get_skill_prompt(station, envelope_dict)

    # Wywolaj LLM
    llm_output = provider.complete(prompt, system=config.llm_system_prompt)

    # Parsuj wyjscie - szukaj bloku KOPERTA
    station_output = parse_llm_output(llm_output, station)

    # Aktualizuj koperte
    envelope.pola_stacji[station] = station_output
    envelope.stacja_poprzednia = envelope.stacja_aktualna
    envelope.stacja_aktualna = station

    return station_output, envelope


def parse_llm_output(output: str, station: str) -> dict[str, Any]:
    """Parsuje wyjscie LLM, szukajac bloku KOPERTA i pol stacji.

    U9: tolerancyjny parser - akceptuje puste linie bez indentacji w bloku KOPERTA.
    """
    # Szukaj bloku KOPERTA - od 'KOPERTA:' do konca lub nastepnego naglowka
    # bez wymogu indentacji kazdej linii (tolerancja na puste linie)
    koperta_match = re.search(
        r"KOPERTA:\s*\n(.*?)(?=\n\S|\Z)",
        output,
        re.DOTALL,
    )

    if koperta_match:
        # Zbuduj poprawny YAML: KOPERTA: z indentowanym blokiem
        raw_block = koperta_match.group(1)
        # Indentuj kazda linie o 2 spacje (YAML wymaga indentacji)
        indented = "\n".join(
            "  " + line if line.strip() else line for line in raw_block.splitlines()
        )
        koperta_yaml = "KOPERTA:\n" + indented
        try:
            koperta_data = yaml.safe_load(koperta_yaml)
            if koperta_data and "KOPERTA" in koperta_data:
                pola_stacji = koperta_data["KOPERTA"].get("pola_stacji", {})
                if station in pola_stacji:
                    return pola_stacji[station]
        except yaml.YAMLError:
            pass

    # Fallback: szukaj bloku YAML z polami stacji
    # Format: ```yaml\n<station>:\n  ...\n```
    yaml_block_match = re.search(
        rf"```yaml\s*\n{station}:\s*\n((?:[ \t].*\n)*)```",
        output,
    )
    if yaml_block_match:
        try:
            data = yaml.safe_load(f"{station}:\n" + yaml_block_match.group(1))
            if data and station in data:
                return data[station]
        except yaml.YAMLError:
            pass

    # Jesli nie znaleziono struktury, zwroc surowy tekst jako fallback
    logger.warning(
        f"Nie znaleziono bloku KOPERTA w wyjsciu LLM dla stacji '{station}'. "
        "Uzywam fallback (surowy tekst)."
    )
    return {"_raw_output": output}


def stop_auto_pilot(run_id: str) -> dict[str, Any]:
    """Zatrzymuje auto-pilot."""
    if run_id in _auto_pilot_state:
        _auto_pilot_state[run_id]["status"] = "zatrzymany"

    return {
        "run_id": run_id,
        "status": "zatrzymany",
        "stacja_zatrzymania": _auto_pilot_state.get(run_id, {}).get("stacja_aktualna", ""),
    }


def finish_auto_pilot(run_id: str, status: str, error: str = "") -> None:
    """Ustawia finalny status auto-pilota po zakonczeniu petli."""
    if run_id not in _auto_pilot_state:
        return
    _auto_pilot_state[run_id]["status"] = status
    if error:
        _auto_pilot_state[run_id]["bledy"].append(error)


def is_stopped(run_id: str) -> bool:
    """Sprawdza czy auto-pilot zostal zatrzymany przez uzytkownika."""
    return _auto_pilot_state.get(run_id, {}).get("status") == "zatrzymany"


def get_auto_pilot_status(run_id: str) -> AutoPilotStatus:
    """Zwraca status wykonania auto-pilota."""
    state = _auto_pilot_state.get(run_id, {
        "status": "zakonczony",
        "stacja_aktualna": "",
        "stacje_wykonane": [],
        "stacje_pozostale": [],
        "iteracja_bramki": 0,
        "bledy": [],
        "laczny_koszt": {"tokens_wejscie": 0, "tokens_wyjscie": 0, "koszt_usd": 0.0},
        "ostatni_llm_koszt": None,
    })

    return AutoPilotStatus(
        run_id=run_id,
        status=state["status"],  # type: ignore
        stacja_aktualna=state["stacja_aktualna"],
        stacje_wykonane=state["stacje_wykonane"],
        stacje_pozostale=state["stacje_pozostale"],
        iteracja_bramki=state["iteracja_bramki"],
        bledy=state["bledy"],
        ostatni_llm_koszt=state.get("ostatni_llm_koszt"),
        laczny_koszt=state.get("laczny_koszt"),
    )


def update_auto_pilot_state(
    run_id: str,
    station: str,
    status: str,
    error: str = "",
) -> None:
    """Aktualizuje stan auto-pilota w pamieci."""
    if run_id not in _auto_pilot_state:
        return

    state = _auto_pilot_state[run_id]
    state["stacja_aktualna"] = station

    if status == "zakonczona":
        if station not in state["stacje_wykonane"]:
            state["stacje_wykonane"].append(station)
    elif status == "zablokowany":
        state["status"] = "zablokowany"
        if error:
            state["bledy"].append(error)
