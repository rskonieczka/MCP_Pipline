"""Logika koperty: tworzenie, aktualizacja, walidacja, kompresja."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import Envelope, Relacja, Stan, Walidacja
from .stations import STATIONS


def create_envelope(run_id: str, zamiar: str, sciezka: str = "pelny") -> Envelope:
    """Tworzy inicjalna koperte po start_run."""
    return Envelope(
        run_id=run_id,
        sciezka=sciezka,  # type: ignore
        stacja_aktualna="",
        stacja_poprzednia=None,
        stan=Stan(zamiar=zamiar),
        pola_stacji={},
        walidacja=Walidacja(),
        relacje=[],
        timestamp=datetime.now().isoformat(),
    )


def update_station_fields(
    envelope: Envelope, station: str, output: dict[str, Any]
) -> Envelope:
    """Aktualizuje pola_stacji.<station> wyjsciem stacji."""
    envelope.pola_stacji[station] = output
    envelope.stacja_poprzednia = envelope.stacja_aktualna
    envelope.stacja_aktualna = station
    envelope.timestamp = datetime.now().isoformat()
    return envelope


def accumulate_state(envelope: Envelope, station: str, output: dict[str, Any]) -> Envelope:
    """Kumuluje pola kluczowe w stan."""
    if station == "inicjuj":
        envelope.stan.klasyfikacja = output.get("klasyfikacja", envelope.stan.klasyfikacja)
        envelope.stan.punkt_wejscia = output.get("punkt_wejscia", envelope.stan.punkt_wejscia)
    return envelope


def add_station_relations(
    envelope: Envelope, station: str, run_id: str
) -> Envelope:
    """Dodaje relacje standardowe dla stacji (nastapila_po, zawiera)."""
    # Relacja: run -> stacja (zawiera) - deduplikacja
    zawiera = Relacja(
        zrodlo=f"run:{run_id}",
        cel=f"stacja:{station}",
        typ="zawiera",
    )
    if zawiera not in envelope.relacje:
        envelope.relacje.append(zawiera)

    # Relacja: stacja_aktualna -> stacja_poprzednia (nastapila_po)
    # Kierunek: aktualna stacja wskazuje na swoją poprzednią
    if envelope.stacja_poprzednia:
        nastapila = Relacja(
            zrodlo=f"stacja:{station}",
            cel=f"stacja:{envelope.stacja_poprzednia}",
            typ="nastapila_po",
        )
        if nastapila not in envelope.relacje:
            envelope.relacje.append(nastapila)

    return envelope


def compress_envelope(envelope: Envelope, keep_last_n: int = 3) -> Envelope:
    """Kompresuje koperte usuwajac starsze sekcje pola_stacji (sciezka doglebny).

    Pelne dane pozostaja w plikach checkpointow.
    """
    stations = list(envelope.pola_stacji.keys())
    if len(stations) <= keep_last_n:
        return envelope

    to_remove = stations[:-keep_last_n]
    for s in to_remove:
        del envelope.pola_stacji[s]

    return envelope


def serialize_envelope(envelope: Envelope) -> str:
    """Serializuje koperte do YAML."""
    import yaml
    return yaml.dump(
        envelope.model_dump(),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def deserialize_envelope(yaml_str: str) -> Envelope:
    """Deserializuje koperte z YAML."""
    import yaml
    data = yaml.safe_load(yaml_str)
    return Envelope(**data)


def get_envelope_summary(envelope: Envelope) -> dict[str, Any]:
    """Zwraca skrot koperty do wynikow narzedzi."""
    return {
        "run_id": envelope.run_id,
        "sciezka": envelope.sciezka,
        "stacja_aktualna": envelope.stacja_aktualna,
        "stacja_poprzednia": envelope.stacja_poprzednia,
        "stan": envelope.stan.model_dump(),
        "pola_stacji_keys": list(envelope.pola_stacji.keys()),
        "relacje_count": len(envelope.relacje),
        "walidacja_status": envelope.walidacja.status,
    }
