"""Logika sciezek pipeline'u: szybki, pelny, doglebny."""
from __future__ import annotations

from .models import InvalidPathError
from .stations import ALL_STATIONS

# Definicje sciezek: lista stacji w kolejnosci wykonania
PATHS: dict[str, list[str]] = {
    "szybki": [
        "inicjuj",
        "zmienne",
        "analiza",
        "dobierz",
        "sprawdzenie",
    ],
    "pelny": [
        "inicjuj",
        "zmienne",
        "analiza",
        "dobierz",
        "planuj",
        "realizuj",
        "weryfikacja",
        "sprawdzenie",
        "utrwal",
    ],
    "doglebny": [
        "inicjuj",
        "zmienne",
        "analiza",
        "dekompozycja",
        "dobierz",
        "routing",
        "planuj",
        "realizuj",
        "weryfikacja",
        "sprawdzenie",
        "ewaluacja",
        "utrwal",
        "monitoruj",
    ],
}


def determine_path(klasyfikacja: str, stawka: str = "", ryzyko: str = "") -> str:
    """Wybor sciezki na podstawie klasyfikacji inicjuj."""
    if klasyfikacja == "trywialne":
        return "szybki"
    elif klasyfikacja == "rutynowe":
        if stawka == "niska" and ryzyko == "niskie":
            return "szybki"
        return "pelny"
    elif klasyfikacja == "zlozone":
        return "doglebny"
    # Default
    return "pelny"


def get_station_sequence(path: str) -> list[str]:
    """Zwraca kolejnosc stacji dla sciezki."""
    if path not in PATHS:
        raise InvalidPathError(
            f"Nieprawidlowa sciezka '{path}'. Dostepne: {list(PATHS.keys())}"
        )
    return PATHS[path]


def get_next_station(
    current: str, path: str, gate_status: str = ""
) -> str | None:
    """Zwraca nastepna stacje na podstawie aktualnej stacji i sciezki."""
    sequence = get_station_sequence(path)
    try:
        idx = sequence.index(current)
    except ValueError:
        # Stacja nie w sciezce - szukaj nastepnej po niej w ALL_STATIONS
        try:
            all_idx = ALL_STATIONS.index(current)
            for s in sequence:
                if ALL_STATIONS.index(s) > all_idx:
                    return s
            return None
        except ValueError:
            return None

    if idx + 1 >= len(sequence):
        return None  # ostatnia stacja

    return sequence[idx + 1]


def is_station_in_path(station: str, path: str) -> bool:
    """Sprawdza czy stacja jest w sciezce."""
    return station in get_station_sequence(path)


def get_post_gate_station(sciezka: str) -> str | None:
    """Zwraca stacje po bramce jakosci (po sprawdzenie).

    Dla sciezki szybkiej 'sprawdzenie' jest ostatnia stacja - zwraca None.
    """
    if sciezka == "pelny":
        return "utrwal"
    elif sciezka == "doglebny":
        return "ewaluacja"
    return None  # szybki: sprawdzenie konczy sciezke
