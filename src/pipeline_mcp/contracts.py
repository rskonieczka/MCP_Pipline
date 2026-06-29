"""Walidacja kontraktow I/O miedzy stacjami.

Zaimplementowane na podstawie wbudowanej specyfikacji kontrakty_pipelines.md.
"""
from __future__ import annotations

from typing import Any

from .models import (
    ContractValidationResult,
    Envelope,
    StationNotFoundError,
    ValidationStatus,
)
from .stations import STATIONS, get_station


# Mapowanie pol wejscia stacji docelowej na zrodlo w kopercie.
# Format: (stacja_docelowa, pole_wejscia) -> (stacja_zrodlowa, pole_wyjscia, status)
# status: "bezposrednie" | "wnioskowane" | "kontekstowe" | "brak"
FIELD_MAPPING: dict[tuple[str, str], tuple[str, str, str]] = {
    # inicjuj -> zmienne
    ("zmienne", "task_goal"): ("_stan", "zamiar", "kontekstowe"),
    ("zmienne", "context"): ("inicjuj", "uzasadnienie", "wnioskowane"),

    # zmienne -> analiza
    ("analiza", "NAZWA_OBIEKTU"): ("zmienne", "analysis_object.name", "bezposrednie"),
    ("analiza", "KONTEKST"): ("zmienne", "variables", "wnioskowane"),
    ("analiza", "ZRODLA"): ("zmienne", "sources_used", "bezposrednie"),

    # analiza -> dekompozycja
    ("dekompozycja", "PROBLEM_LUB_CEL_ZLOZONY"): ("analiza", "wnioski+ograniczenia", "wnioskowane"),
    ("dekompozycja", "OGRANICZENIA"): ("analiza", "ograniczenia", "bezposrednie"),
    ("dekompozycja", "KONTEKST"): ("analiza", "raport_streszczenie", "wnioskowane"),

    # analiza -> dobierz (gdy pominięto dekompozycję)
    ("dobierz", "CEL_DOBORU"): ("analiza", "wnioski", "wnioskowane"),
    ("dobierz", "WARIANTY"): ("analiza", "raport_streszczenie", "wnioskowane"),

    # dekompozycja -> dobierz
    # ("dobierz", "CEL_DOBORU") - juz zdefiniowane wyzej
    # dekompozycja moze tez dostarczyc WARIANTY i KRYTERIA

    # dobierz -> routing
    ("routing", "ZAMIAR_LUB_PROBLEM"): ("_stan", "zamiar", "kontekstowe"),
    ("routing", "ZASOBY"): ("dobierz", "najblizszy_krok", "wnioskowane"),

    # dobierz -> planuj (gdy pominięto routing)
    ("planuj", "CEL_DO_ZAPLANOWANIA"): ("dobierz", "rekomendacja", "wnioskowane"),
    ("planuj", "KONTEKST"): ("dobierz", "porownanie", "bezposrednie"),
    ("planuj", "OGRANICZENIA"): ("dobierz", "ryzyka_i_warunki_rewizji", "bezposrednie"),
    ("planuj", "KRYTERIA_SUKCESU"): ("dobierz", "kryteria", "wnioskowane"),

    # routing -> planuj
    ("planuj", "ZAKRES"): ("routing", "stacje_uruchomione", "bezposrednie"),

    # planuj -> realizuj
    ("realizuj", "PLAN_DO_ZREALIZOWANIA"): ("planuj", "kroki", "bezposrednie"),
    ("realizuj", "KONTEKST"): ("planuj", "zasoby", "bezposrednie"),

    # realizuj -> weryfikacja
    ("weryfikacja", "TWIERDZENIE_LUB_ZBIOR_TWIERDZEN"): ("realizuj", "zmiany", "wnioskowane"),
    ("weryfikacja", "ZAKRES"): ("realizuj", "kroki_zablokowane", "bezposrednie"),

    # weryfikacja -> sprawdzenie
    ("sprawdzenie", "ODPOWIEDZ_LUB_ARTEFAKT"): ("weryfikacja", "werdykty", "bezposrednie"),
    ("sprawdzenie", "PYTANIE_ZRODLOWE"): ("_stan", "zamiar", "kontekstowe"),
    ("sprawdzenie", "ZRODLA_PRAWDY"): ("weryfikacja", "konflikty_zrodel", "bezposrednie"),

    # sprawdzenie -> ewaluacja
    ("ewaluacja", "ROZWIAZANIE_LUB_ARTEFAKT"): ("sprawdzenie", "poprawiona_odpowiedz", "bezposrednie"),
    ("ewaluacja", "KRYTERIA_EWALUACJI"): ("sprawdzenie", "ocena_calkowita", "wnioskowane"),

    # sprawdzenie -> utrwal (gdy pominięto ewaluację)
    ("utrwal", "WNIOSKI_LUB_DECYZJE_DO_ZAPISANIA"): ("sprawdzenie", "werdykt", "wnioskowane"),
    ("utrwal", "CEL"): ("sprawdzenie", "poprawiona_odpowiedz", "wnioskowane"),

    # ewaluacja -> utrwal
    # ("utrwal", "WNIOSKI_LUB_DECYZJE_DO_ZAPISANIA") - moze tez z ewaluacja.wnioski

    # utrwal -> monitoruj
    ("monitoruj", "ZADANIE_LUB_PLAN"): ("planuj", "kroki", "kontekstowe"),
}


def _get_field_from_envelope(envelope: Envelope, source_station: str, field_path: str) -> Any:
    """Pobiera pole z koperty. Obsluguje zagniezdzone sciezki (np. analysis_object.name)."""
    if source_station == "_stan":
        # Pole ze stanu kumulowanego
        return getattr(envelope.stan, field_path, None)

    station_data = envelope.pola_stacji.get(source_station, {})
    if "." in field_path:
        # Zagniezdzone pole (np. analysis_object.name)
        parts = field_path.split(".")
        value = station_data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    return station_data.get(field_path)


def validate_input(target_station: str, envelope: Envelope) -> ContractValidationResult:
    """Waliduje czy wejscie stacji docelowej jest kompletne na podstawie koperty."""
    if target_station not in STATIONS:
        raise StationNotFoundError(f"Stacja '{target_station}' nie istnieje")

    station_def = STATIONS[target_station]
    pola_wymagane = station_def.required_input
    pola_obecne: list[str] = []
    pola_brakujace: list[str] = []
    pola_wnioskowane: list[str] = []

    for req_field in pola_wymagane:
        mapping = FIELD_MAPPING.get((target_station, req_field))
        if mapping is None:
            # Brak mapowania - pole musi byc dostarczone przez uzytkownika/agenta
            pola_brakujace.append(req_field)
            continue

        source_station, source_field, status = mapping
        value = _get_field_from_envelope(envelope, source_station, source_field)

        if value is not None and value != "" and value != []:
            pola_obecne.append(req_field)
            if status == "wnioskowane":
                pola_wnioskowane.append(req_field)
        else:
            if status == "wnioskowane":
                # Pole wnioskowane - moze byc wyprowadzone przez agenta
                pola_wnioskowane.append(req_field)
            else:
                pola_brakujace.append(req_field)

    # Ustal status walidacji
    if not pola_brakujace:
        if pola_wnioskowane:
            status = ValidationStatus.WNISKOWANE if False else "wnioskowane"
        else:
            status = "gotowy"
    else:
        status = "niekompletne"

    # Akcja naprawcza
    akcja = ""
    if status == "niekompletne":
        if all(
            FIELD_MAPPING.get((target_station, f), (None, None, "brak"))[2] == "brak"
            for f in pola_brakujace
        ):
            akcja = "pytanie_do_uzytkownika"
        else:
            akcja = "agent_inference"

    return ContractValidationResult(
        stacja_docelowa=target_station,
        pola_wymagane=pola_wymagane,
        pola_obecne=pola_obecne,
        pola_brakujace=pola_brakujace,
        pola_wnioskowane=pola_wnioskowane,
        status=status,  # type: ignore
        akcja_naprawcza=akcja,
    )


def get_mapping_for_station(target_station: str) -> list[dict[str, Any]]:
    """Zwraca mapowanie pol wejscia stacji docelowej na zrodla w kopercie."""
    mappings: list[dict[str, Any]] = []
    for (station, field), (src_station, src_field, status) in FIELD_MAPPING.items():
        if station == target_station:
            mappings.append({
                "pole_wejscia": field,
                "stacja_zrodlowa": src_station,
                "pole_wyjscia": src_field,
                "status": status,
                "uwagi": "",
            })
    return mappings
