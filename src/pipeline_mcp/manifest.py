"""Zarzadzanie manifestem run'u."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from .models import Manifest, StacjaManifest, StationStatus


def create_manifest(run_id: str, zamiar: str, sciezka: str = "pelny") -> Manifest:
    """Tworzy nowy manifest run'u."""
    return Manifest(
        run_id=run_id,
        zamiar=zamiar,
        sciezka=sciezka,  # type: ignore
        iteracja_bramki=0,
        status_runu="w_trakcie",
        timestamp_start=datetime.now().isoformat(),
        stacje=[],
    )


def save_manifest(manifest: Manifest, path: Path) -> None:
    """Zapisuje manifest do pliku YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            manifest.model_dump(),
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def load_manifest(path: Path) -> Manifest:
    """Odczytuje manifest z pliku YAML."""
    from .models import RunNotFoundError
    if not path.exists():
        raise RunNotFoundError(f"Manifest nie istnieje: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Manifest(**data)


def add_station_to_manifest(
    manifest: Manifest, station: str, status: StationStatus = "w_trakcie"
) -> Manifest:
    """Dodaje stacje do manifestu."""
    # Sprawdz czy stacja juz istnieje
    for s in manifest.stacje:
        if s.stacja == station:
            s.status = status
            if status == "zakonczona":
                s.timestamp = datetime.now().isoformat()
            return manifest

    manifest.stacje.append(StacjaManifest(
        stacja=station,
        status=status,
        timestamp=datetime.now().isoformat() if status == "zakonczona" else None,
    ))
    return manifest


def update_station_status(
    manifest: Manifest, station: str, status: StationStatus, checkpoint: str | None = None
) -> Manifest:
    """Aktualizuje status stacji w manifeście."""
    for s in manifest.stacje:
        if s.stacja == station:
            s.status = status
            if status == "zakonczona":
                s.timestamp = datetime.now().isoformat()
            if checkpoint:
                s.checkpoint = checkpoint
            return manifest

    # Stacja nie istnieje - dodaj
    manifest.stacje.append(StacjaManifest(
        stacja=station,
        status=status,
        timestamp=datetime.now().isoformat() if status == "zakonczona" else None,
        checkpoint=checkpoint,
    ))
    return manifest


def get_station_status(manifest: Manifest, station: str) -> StationStatus | None:
    """Zwraca status stacji z manifestu."""
    for s in manifest.stacje:
        if s.stacja == station:
            return s.status  # type: ignore
    return None


def get_last_completed_station(manifest: Manifest) -> str | None:
    """Zwraca ostatnia zakonczona stacje."""
    last = None
    for s in manifest.stacje:
        if s.status == "zakonczona":
            last = s.stacja
    return last


def get_current_station(manifest: Manifest) -> str | None:
    """Zwraca stacje w_trakcie."""
    for s in manifest.stacje:
        if s.status == "w_trakcie":
            return s.stacja
    return None


def close_manifest(manifest: Manifest) -> Manifest:
    """Zamyka manifest - ustawia status_runu na zakonczony."""
    manifest.status_runu = "zakonczony"  # type: ignore
    manifest.timestamp_end = datetime.now().isoformat()
    return manifest


def increment_gate_iteration(manifest: Manifest) -> Manifest:
    """Zwieksza iteracje bramki."""
    manifest.iteracja_bramki += 1
    return manifest
