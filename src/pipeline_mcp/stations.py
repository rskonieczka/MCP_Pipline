"""Definicje 13 stacji pipeline'u i ich kontrakty I/O.

Zaimplementowane na podstawie wbudowanej specyfikacji kontrakty_pipelines.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StationDef:
    """Definicja stacji pipeline'u."""

    name: str
    phase: str
    required_input: list[str]
    optional_input: list[str]
    output: list[str]
    # Logika wyznaczania nastepnej stacji: "sequential" | "klasyfikacja_based" | "gate_based"
    next_station_logic: str = "sequential"
    # Czy stacja jest opcjonalna (mozna pominac w niektorych sciezkach)
    optional_in_paths: list[str] = field(default_factory=list)


# Kolejnosc stacji w pelnym pipeline (sciezka doglebny)
ALL_STATIONS: list[str] = [
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
]

# Mapowanie nazw katalogow skilli na nazwy stacji
SKILL_DIR_MAP: dict[str, str] = {
    "inicjuj-run": "inicjuj",
    "zmienne": "zmienne",
    "analiza": "analiza",
    "dekompozycja": "dekompozycja",
    "dobierz": "dobierz",
    "routing": "routing",
    "planuj": "planuj",
    "realizuj": "realizuj",
    "weryfikacja": "weryfikacja",
    "sprawdzenie": "sprawdzenie",
    "ewaluacja": "ewaluacja",
    "utrwal": "utrwal",
    "monitoruj": "monitoruj",
    "audyt-runu": "audyt_runu",
}

# Odwrotne mapowanie: nazwa stacji -> katalog skilla
STATION_TO_SKILL_DIR: dict[str, str] = {v: k for k, v in SKILL_DIR_MAP.items()}

# Definicje stacji z kontraktami I/O
STATIONS: dict[str, StationDef] = {
    "inicjuj": StationDef(
        name="inicjuj",
        phase="Inicjacja",
        required_input=["ZAMIAR_UZYTKOWNIKA"],
        optional_input=["KONTEKST", "ZRODLA", "TRYB_INICJACJI"],
        output=["klasyfikacja", "punkt_wejscia", "uzasadnienie", "ryzyka"],
        next_station_logic="klasyfikacja_based",
    ),
    "zmienne": StationDef(
        name="zmienne",
        phase="Normalizacja",
        required_input=["task_goal"],
        optional_input=["context", "operation_mode", "ZRODLA", "missing_data_resolution"],
        output=["variables", "relations", "sources_used", "missing_data_resolution", "analysis_object"],
    ),
    "analiza": StationDef(
        name="analiza",
        phase="Rozpoznanie",
        required_input=["NAZWA_OBIEKTU"],
        optional_input=["KONTEKST", "ZAKRES", "ZRODLA", "TRYB_ANALIZY"],
        output=["raport_streszczenie", "pewnosc", "ograniczenia", "wnioski"],
    ),
    "dekompozycja": StationDef(
        name="dekompozycja",
        phase="Podzial",
        required_input=["PROBLEM_LUB_CEL_ZLOZONY"],
        optional_input=["KONTEKST", "OGRANICZENIA", "ZRODLA", "TRYB_DEKOMPOZYCJI"],
        output=["podproblemy", "zaleznosci", "kolejnosc", "krytyczne"],
        optional_in_paths=["szybki", "pelny"],
    ),
    "dobierz": StationDef(
        name="dobierz",
        phase="Wybor",
        required_input=["CEL_DOBORU"],
        optional_input=["WARIANTY", "ZRODLA", "KONTEKST", "KRYTERIA", "OGRANICZENIA", "PREFERENCJE"],
        output=["status_doboru", "metoda_doboru", "warianty", "kryteria", "porownanie", "rekomendacja", "ryzyka_i_warunki_rewizji", "najblizszy_krok"],
    ),
    "routing": StationDef(
        name="routing",
        phase="Routing sciezki",
        required_input=["ZAMIAR_LUB_PROBLEM"],
        optional_input=["STAWKA_DECYZYJNA", "RYZYKO", "ZASOBY", "TRYB_ROUTINGU"],
        output=["sciezka", "stawka", "ryzyko", "stacje_uruchomione", "stacje_pominiete", "stacje_poglebione"],
        optional_in_paths=["szybki", "pelny"],
    ),
    "planuj": StationDef(
        name="planuj",
        phase="Planowanie",
        required_input=["CEL_DO_ZAPLANOWANIA"],
        optional_input=["KONTEKST", "OGRANICZENIA", "HORYZONT", "TRYB_PLANOWANIA", "ZRODLA", "KRYTERIA_SUKCESU", "ZAKRES"],
        output=["cel", "sytuacja", "kroki", "zasoby", "ryzyka", "kryteria_sukcesu", "punkty_kontrolne"],
    ),
    "realizuj": StationDef(
        name="realizuj",
        phase="Realizacja",
        required_input=["PLAN_DO_ZREALIZOWANIA"],
        optional_input=["KONTEKST", "ZRODLA", "TRYB_REALIZACJI"],
        output=["kroki_wykonane", "kroki_pominiete", "kroki_zablokowane", "zmiany", "status"],
    ),
    "weryfikacja": StationDef(
        name="weryfikacja",
        phase="Weryfikacja",
        required_input=["TWIERDZENIE_LUB_ZBIOR_TWIERDZEN"],
        optional_input=["KRYTERIUM_WERYFIKACJI", "ZRODLA", "TRYB_WERYFIKACJI", "ZAKRES"],
        output=["werdykty", "konflikty_zrodel", "braki_dowodowe", "podsumowanie"],
    ),
    "sprawdzenie": StationDef(
        name="sprawdzenie",
        phase="Audyt",
        required_input=["PYTANIE_ZRODLOWE", "ODPOWIEDZ_LUB_ARTEFAKT"],
        optional_input=["TRYB_AUDYTU", "KONTEKST_DODATKOWY", "ZRODLA_PRAWDY", "KRYTERIA_OCENY"],
        output=["status_audytu", "ocena_calkowita", "werdykt", "wymiary", "poprawiona_odpowiedz"],
        next_station_logic="gate_based",
    ),
    "ewaluacja": StationDef(
        name="ewaluacja",
        phase="Ewaluacja ex-post",
        required_input=["ROZWIAZANIE_LUB_ARTEFAKT"],
        optional_input=["CEL_ZRODLOWY", "KRYTERIA_EWALUACJI", "HORYZONT", "ZRODLA", "TRYB_EWALUACJI"],
        output=["typ_ewaluacji", "ocena_ogolna", "wymiary", "wnioski", "rekomendacje", "status"],
        optional_in_paths=["szybki", "pelny"],
    ),
    "utrwal": StationDef(
        name="utrwal",
        phase="Utrwalenie",
        required_input=["WNIOSKI_LUB_DECYZJE_DO_ZAPISANIA"],
        optional_input=["TYP_WIEDZY", "CEL", "ZRODLA", "TRYB_UTRWALANIA"],
        output=["typ_wiedzy", "miejsca_zapisu", "akcje", "status"],
    ),
    "monitoruj": StationDef(
        name="monitoruj",
        phase="Monitorowanie",
        required_input=["ZADANIE_LUB_PLAN"],
        optional_input=["CHECKPOINTY", "METRYKI", "ZRODLA", "TRYB_MONOTOROWANIA"],
        output=["checkpointy", "blokady", "odchylenia", "warunki_przejscia", "status"],
        optional_in_paths=["szybki", "pelny"],
    ),
    "audyt_runu": StationDef(
        name="audyt_runu",
        phase="Audyt run'u",
        required_input=["RUN_ID"],
        optional_input=["TRYB_AUDYTU", "ZAKRES", "ZRODLA"],
        output=["wymiary_audytu", "ocena_calkowita", "liczba_anomalii", "anomalie", "rekomendacje", "status"],
        optional_in_paths=["szybki", "pelny", "doglebny"],  # opcjonalna we wszystkich sciezkach
    ),
}


def get_station(name: str) -> StationDef:
    """Zwraca definicje stacji. Rzuca StationNotFoundError jesli nie istnieje."""
    if name not in STATIONS:
        from .models import StationNotFoundError
        raise StationNotFoundError(f"Stacja '{name}' nie istnieje. Dostepne: {list(STATIONS.keys())}")
    return STATIONS[name]


def station_exists(name: str) -> bool:
    """Sprawdza czy stacja istnieje."""
    return name in STATIONS
