"""Pamiec AI per-klient i wspoldzielona.

Katalogi:
    <workspace>/.ai-kb/clients/<client_id>/memory/   - izolowana pamiec per-klient
    <workspace>/.ai-kb/shared-knowledge/memory/      - wspoldzielona pamiec

Format: YAML (spojny z checkpointami).
Integracja z Memgraph: wezly :Pamiec z client_id.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import get_config
from .models import ClientMemoryEntry

logger = logging.getLogger(__name__)


def _atomic_yaml_dump(path: Path, data: dict[str, Any]) -> None:
    """Atomowy zapis YAML (tempfile + os.replace). Chroni przed uszkodzeniem pliku."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=path.stem
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(
                data, f, allow_unicode=True,
                default_flow_style=False, sort_keys=False,
            )
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _unique_memory_id(base: str, path: Path) -> str:
    """Zapewnia unikalnosc memory_id - przy kolizji dolacza sufiks timestamp."""
    if not path.exists():
        return base
    return f"{base}-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _memory_path(
    memory_id: str, client_id: str, scope: str, workspace: str | None = None
) -> Path:
    """Zwraca sciezke pliku pamieci."""
    config = get_config()
    if scope == "shared":
        return config.shared_memory_dir(workspace) / f"{memory_id}.yaml"
    return config.client_memory_dir(client_id, workspace) / f"{memory_id}.yaml"


def save_client_memory(
    topic: str,
    content: str,
    client_id: str,
    memory_id: str = "",
    tags: list[str] | None = None,
    workspace: str | None = None,
) -> ClientMemoryEntry:
    """Zapisuje wpis pamieci AI per-klient."""
    if not client_id:
        raise ValueError("client_id jest wymagany dla pamieci per-klient")

    base_mid = memory_id or re.sub(r"[^a-z0-9-]", "", topic.lower().replace(" ", "-"))[:50]
    if not base_mid:
        base_mid = f"m-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    path = _memory_path(base_mid, client_id, "client", workspace)
    # F2: przy auto-generowanym memory_id zapobiegaj cichemu nadpisaniu
    mid = base_mid if memory_id else _unique_memory_id(base_mid, path)
    path = _memory_path(mid, client_id, "client", workspace)

    entry = ClientMemoryEntry(
        memory_id=mid,
        topic=topic,
        content=content,
        scope="client",
        client_id=client_id,
        tags=tags or [],
    )

    _atomic_yaml_dump(path, entry.model_dump())

    # Zapis do Memgraph (opcjonalny)
    from . import memgraph
    memgraph.write_client_memory_node(mid, client_id, topic, content, "client")

    return entry


def save_shared_memory(
    topic: str,
    content: str,
    memory_id: str = "",
    tags: list[str] | None = None,
    workspace: str | None = None,
) -> ClientMemoryEntry:
    """Zapisuje wpis pamieci AI wspoldzielonej (cross-client)."""
    base_mid = memory_id or re.sub(r"[^a-z0-9-]", "", topic.lower().replace(" ", "-"))[:50]
    if not base_mid:
        base_mid = f"m-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    path = _memory_path(base_mid, "", "shared", workspace)
    # F2: przy auto-generowanym memory_id zapobiegaj cichemu nadpisaniu
    mid = base_mid if memory_id else _unique_memory_id(base_mid, path)
    path = _memory_path(mid, "", "shared", workspace)

    entry = ClientMemoryEntry(
        memory_id=mid,
        topic=topic,
        content=content,
        scope="shared",
        client_id="shared",
        tags=tags or [],
    )

    _atomic_yaml_dump(path, entry.model_dump())

    # Zapis do Memgraph (opcjonalny)
    from . import memgraph
    memgraph.write_client_memory_node(mid, "shared", topic, content, "shared")

    return entry


def get_client_memory(
    memory_id: str, client_id: str, workspace: str | None = None
) -> ClientMemoryEntry | None:
    """Odczytuje wpis pamieci per-klient."""
    path = _memory_path(memory_id, client_id, "client", workspace)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return ClientMemoryEntry(**data)
    except Exception as e:
        logger.warning(f"Blad ladowania pamieci {memory_id}: {e}")
        return None


def get_shared_memory(
    memory_id: str, workspace: str | None = None
) -> ClientMemoryEntry | None:
    """Odczytuje wpis pamieci wspoldzielonej."""
    path = _memory_path(memory_id, "", "shared", workspace)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return ClientMemoryEntry(**data)
    except Exception as e:
        logger.warning(f"Blad ladowania pamieci shared {memory_id}: {e}")
        return None


def list_client_memories(
    client_id: str, workspace: str | None = None
) -> list[dict[str, Any]]:
    """Lista wpisow pamieci per-klient."""
    config = get_config()
    mem_dir = config.client_memory_dir(client_id, workspace)
    if not mem_dir.exists():
        return []

    results: list[dict[str, Any]] = []
    for f in sorted(mem_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data:
                results.append({
                    "memory_id": data.get("memory_id", f.stem),
                    "topic": data.get("topic", ""),
                    "tags": data.get("tags", []),
                    "timestamp": data.get("timestamp", ""),
                })
        except Exception:
            pass
    return results


def list_shared_memories(
    workspace: str | None = None
) -> list[dict[str, Any]]:
    """Lista wpisow pamieci wspoldzielonej."""
    config = get_config()
    mem_dir = config.shared_memory_dir(workspace)
    if not mem_dir.exists():
        return []

    results: list[dict[str, Any]] = []
    for f in sorted(mem_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data:
                results.append({
                    "memory_id": data.get("memory_id", f.stem),
                    "topic": data.get("topic", ""),
                    "tags": data.get("tags", []),
                    "timestamp": data.get("timestamp", ""),
                })
        except Exception:
            pass
    return results


def search_client_memories(
    query: str, client_id: str, include_shared: bool = True, workspace: str | None = None
) -> list[dict[str, Any]]:
    """Wyszukuje w pamieci per-klient (i opcjonalnie wspoldzielonej)."""
    query_lower = query.lower()
    results: list[dict[str, Any]] = []

    # Pamiec per-klient
    config = get_config()
    mem_dir = config.client_memory_dir(client_id, workspace)
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not data:
                    continue
                topic = str(data.get("topic", ""))
                content = str(data.get("content", ""))
                if query_lower in topic.lower() or query_lower in content.lower():
                    results.append({
                        "memory_id": data.get("memory_id", f.stem),
                        "topic": topic,
                        "content": content[:200],
                        "scope": "client",
                        "client_id": client_id,
                        "tags": data.get("tags", []),
                    })
            except Exception:
                pass

    # Pamiec wspoldzielona
    if include_shared:
        shared_dir = config.shared_memory_dir(workspace)
        if shared_dir.exists():
            for f in sorted(shared_dir.glob("*.yaml")):
                try:
                    with open(f, encoding="utf-8") as fh:
                        data = yaml.safe_load(fh)
                    if not data:
                        continue
                    topic = str(data.get("topic", ""))
                    content = str(data.get("content", ""))
                    if query_lower in topic.lower() or query_lower in content.lower():
                        results.append({
                            "memory_id": data.get("memory_id", f.stem),
                            "topic": topic,
                            "content": content[:200],
                            "scope": "shared",
                            "client_id": "shared",
                            "tags": data.get("tags", []),
                        })
                except Exception:
                    pass

    return results
