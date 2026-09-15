"""Wiedza wspoldzielona (cross-client).

Katalog: <workspace>/.ai-kb/shared-knowledge/{decisions,patterns,pitfalls}/
Format: YAML (spojny z checkpointami).
Integracja z Memgraph: wezly :Wiedza z client_id='shared'.
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
from .models import SharedKnowledgeEntry

logger = logging.getLogger(__name__)

_CATEGORIES = ("decision", "pattern", "pitfall")


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


def _category_dir(category: str, workspace: str | None = None) -> Path:
    """Zwraca katalog dla kategorii wiedzy."""
    # W1: kategoria wchodzi w sklad sciezki - whitelist (wczesniej walidowana
    # tylko przy zapisie; odczyt i wyszukiwanie akceptowaly dowolna wartosc)
    if category not in _CATEGORIES:
        raise ValueError(
            f"Nieprawidlowa kategoria '{category}'. Dostepne: {list(_CATEGORIES)}"
        )
    config = get_config()
    return config.shared_knowledge_dir(workspace) / f"{category}s"


def _knowledge_path(knowledge_id: str, category: str, workspace: str | None = None) -> Path:
    """Zwraca sciezke pliku wiedzy."""
    from .config import validate_path_segment
    # W1: knowledge_id wchodzi w sklad nazwy pliku - walidacja przed traversal
    validate_path_segment("knowledge_id", knowledge_id)
    return _category_dir(category, workspace) / f"{knowledge_id}.yaml"


def save_shared_knowledge(
    knowledge_id: str,
    category: str,
    title: str,
    content: str,
    source: str = "",
    tags: list[str] | None = None,
    workspace: str | None = None,
) -> SharedKnowledgeEntry:
    """Zapisuje wpis wiedzy wspoldzielonej."""
    if category not in _CATEGORIES:
        raise ValueError(
            f"Nieprawidlowa kategoria '{category}'. Dostepne: {list(_CATEGORIES)}"
        )

    # Sanityzacja knowledge_id
    kid = re.sub(r"[^a-z0-9-]", "", knowledge_id.lower())
    if not kid:
        kid = f"k-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    entry = SharedKnowledgeEntry(
        knowledge_id=kid,
        category=category,  # type: ignore
        title=title,
        content=content,
        source=source,
        tags=tags or [],
    )

    path = _knowledge_path(kid, category, workspace)
    _atomic_yaml_dump(path, entry.model_dump())

    # Zapis do Memgraph (opcjonalny)
    from . import memgraph
    memgraph.write_shared_knowledge_node(kid, category, title, content)

    return entry


def get_shared_knowledge(
    knowledge_id: str, category: str, workspace: str | None = None
) -> SharedKnowledgeEntry | None:
    """Odczytuje wpis wiedzy wspoldzielonej."""
    path = _knowledge_path(knowledge_id, category, workspace)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return SharedKnowledgeEntry(**data)
    except Exception as e:
        logger.warning(f"Blad ladowania wiedzy {knowledge_id}: {e}")
        return None


def search_shared_knowledge(
    query: str, category: str = "", workspace: str | None = None
) -> list[dict[str, Any]]:
    """Wyszukuje w wiedzy wspoldzielonej (proste dopasowanie keyword).

    Przeszukuje tytuly i tresc wszystkich wpisow (lub wybranej kategorii).
    """
    query_lower = query.lower()
    results: list[dict[str, Any]] = []

    categories = [category] if category else _CATEGORIES
    for cat in categories:
        cat_dir = _category_dir(cat, workspace)
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not data:
                    continue
                title = str(data.get("title", ""))
                content = str(data.get("content", ""))
                if query_lower in title.lower() or query_lower in content.lower():
                    results.append({
                        "knowledge_id": data.get("knowledge_id", f.stem),
                        "category": data.get("category", cat),
                        "title": title,
                        "source": data.get("source", ""),
                        "tags": data.get("tags", []),
                        "path": str(f),
                    })
            except Exception as e:
                logger.warning(f"Blad odczytu {f}: {e}")

    return results


def list_shared_knowledge(
    category: str = "", workspace: str | None = None
) -> list[dict[str, Any]]:
    """Lista wszystkich wpisow wiedzy wspoldzielonej."""
    results: list[dict[str, Any]] = []
    categories = [category] if category else _CATEGORIES
    for cat in categories:
        cat_dir = _category_dir(cat, workspace)
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if data:
                    results.append({
                        "knowledge_id": data.get("knowledge_id", f.stem),
                        "category": data.get("category", cat),
                        "title": data.get("title", ""),
                        "tags": data.get("tags", []),
                    })
            except Exception:
                pass
    return results
