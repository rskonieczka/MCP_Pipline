"""Checkpointowanie plikowe YAML."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from .config import get_config
from .envelope import serialize_envelope
from .models import CheckpointNotFoundError, Envelope


def save_checkpoint(
    run_id: str, station: str, envelope: Envelope, suffix: str = "",
    workspace: str | None = None, client_id: str = "",
) -> str:
    """Zapisuje koperte do pliku checkpointu."""
    config = get_config()
    checkpoint_path = config.checkpoint_path(run_id, station, suffix, workspace, client_id)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    # Dodaj metadane checkpointu
    data = envelope.model_dump()
    data["_checkpoint"] = {
        "station": station,
        "suffix": suffix,
        "timestamp": datetime.now().isoformat(),
    }

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    return str(checkpoint_path)


def _load_envelope_file(checkpoint_path: Path) -> Envelope:
    """Odczytuje koperte bezposrednio z pliku checkpointu."""
    if not checkpoint_path.exists():
        raise CheckpointNotFoundError(
            f"Checkpoint nie istnieje: {checkpoint_path}"
        )

    with open(checkpoint_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Usun metadane checkpointu przed rekonstrukcja Envelope
    data.pop("_checkpoint", None)

    return Envelope(**data)


def load_checkpoint(
    run_id: str, station: str, suffix: str = "", workspace: str | None = None,
    client_id: str = "",
) -> Envelope:
    """Odczytuje koperte z pliku checkpointu."""
    config = get_config()
    return _load_envelope_file(config.checkpoint_path(run_id, station, suffix, workspace, client_id))


def list_checkpoints(run_id: str, workspace: str | None = None, client_id: str = "") -> list[dict]:
    """Lista wszystkich checkpointow dla run'u."""
    config = get_config()
    run_dir = config.run_dir(run_id, workspace, client_id)

    if not run_dir.exists():
        return []

    checkpoints = []
    for f in sorted(run_dir.glob("stan_*.yaml")):
        stat = f.stat()
        # Parsuj nazwe pliku: stan_<station><suffix>.yaml
        name = f.stem  # np. stan_inicjuj lub stan_dobierz_iter1
        parts = name.replace("stan_", "", 1)

        # Rozdziel station i suffix
        if "_iter" in parts:
            station, iter_part = parts.rsplit("_iter", 1)
            suffix = f"_iter{iter_part}"
        else:
            station = parts
            suffix = ""

        checkpoints.append({
            "station": station,
            "checkpoint_path": str(f),
            "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "suffix": suffix,
            "size_bytes": stat.st_size,
        })

    return checkpoints


def get_latest_checkpoint(
    run_id: str, workspace: str | None = None, client_id: str = "",
) -> tuple[str, Envelope] | None:
    """Zwraca ostatni checkpoint (stacja, koperta). None jesli brak.

    Uzywa manifestu do ustalenia ostatniej zakonczonej stacji (chronologicznie),
    nie sortowania alfabetycznego nazw plikow.
    """
    from .manifest import load_manifest
    config = get_config()
    manifest_path = config.manifest_path(run_id, workspace, client_id)

    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        # Szukaj ostatniej zakonczonej stacji z checkpointem na dysku
        for s in reversed(manifest.stacje):
            if s.status == "zakonczona" and s.checkpoint:
                cp_path = Path(s.checkpoint)
                if cp_path.exists():
                    # Czytaj plik wskazany w manifeście (moze miec sufiks _iterN)
                    return s.stacja, _load_envelope_file(cp_path)

    # Fallback: sortuj po timestamp pliku (mtime)
    checkpoints = list_checkpoints(run_id, workspace, client_id)
    if not checkpoints:
        return None

    main_checkpoints = [c for c in checkpoints if not c["suffix"]]
    if not main_checkpoints:
        main_checkpoints = checkpoints

    # Sortuj po timestamp (mtime), nie po nazwie pliku
    main_checkpoints.sort(key=lambda c: c["timestamp"])
    latest = main_checkpoints[-1]
    envelope = load_checkpoint(run_id, latest["station"], latest["suffix"], workspace, client_id)
    return latest["station"], envelope


def save_envelope_final(
    run_id: str, envelope: Envelope, workspace: str | None = None,
    client_id: str = "",
) -> str:
    """Zapisuje ostateczna koperte po zamknieciu run'u."""
    config = get_config()
    path = config.envelope_final_path(run_id, workspace, client_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(serialize_envelope(envelope))

    return str(path)
