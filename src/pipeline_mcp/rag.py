"""RAG per-klient i wspoldzielony.

Katalogi:
    <workspace>/.ai-kb/clients/<client_id>/rag/    - izolowany RAG per-klient
    <workspace>/.ai-kb/shared-knowledge/rag/       - wspoldzielony RAG

Implementacja: plikowa (YAML/JSON), prosty indeks keyword-based.
Brak zaleznosci zewnetrznych - wektorowa opcjonalna w przyszlosci.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
import weakref
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import get_config

logger = logging.getLogger(__name__)

# Blokady per-sciezka-indexu chronia przed lost update w rownoleglym indeksowaniu.
# WeakValueDictionary automatycznie zwalnia locki gdy nie sa uzywane (zapobiega wyciekowi pamieci).
_index_locks: weakref.WeakValueDictionary[str, threading.Lock] = weakref.WeakValueDictionary()
_index_locks_guard = threading.Lock()


def _get_index_lock(path: Path) -> threading.Lock:
    """Zwraca blokade per plik indeksu (chroni przed race condition)."""
    key = str(path)
    with _index_locks_guard:
        lock = _index_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _index_locks[key] = lock
        return lock


def _rag_index_path(client_id: str, workspace: str | None = None) -> Path:
    """Zwraca sciezke pliku indeksu RAG per-klient."""
    config = get_config()
    if client_id:
        return config.client_rag_dir(client_id, workspace) / "index.yaml"
    return config.shared_rag_dir(workspace) / "index.yaml"


def _load_index(path: Path) -> dict[str, Any]:
    """Laduje indeks RAG z pliku."""
    if not path.exists():
        return {"documents": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {"documents": []}
    except Exception:
        return {"documents": []}


def _save_index(path: Path, index: dict[str, Any]) -> None:
    """Zapisuje indeks RAG do pliku (atomowo - zapis do temp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=path.stem
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(index, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _tokenize(text: str) -> set[str]:
    """Prosta tokenizacja: lowercase, alfanumeryczne."""
    return set(re.findall(r"\w+", text.lower()))


def index_client_document(
    doc_id: str,
    content: str,
    title: str = "",
    metadata: dict[str, Any] | None = None,
    client_id: str = "",
    workspace: str | None = None,
) -> dict[str, Any]:
    """Indeksuje dokument w RAG per-klient (lub wspoldzielonym gdy client_id puste)."""
    path = _rag_index_path(client_id, workspace)
    lock = _get_index_lock(path)
    with lock:
        index = _load_index(path)

        # Sanityzacja doc_id
        did = re.sub(r"[^a-z0-9-]", "", doc_id.lower())
        if not did:
            did = f"doc-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Usun istniejacy wpis z tym samym doc_id (re-index)
        index["documents"] = [d for d in index["documents"] if d.get("doc_id") != did]

        doc_entry = {
            "doc_id": did,
            "title": title,
            "content": content,
            "tokens": list(_tokenize(content + " " + title)),
            "metadata": metadata or {},
            "indexed_at": datetime.now().isoformat(),
            "scope": "client" if client_id else "shared",
            "client_id": client_id,
        }

        index["documents"].append(doc_entry)
        _save_index(path, index)

        return {
            "doc_id": did,
            "scope": doc_entry["scope"],
            "client_id": client_id,
            "indexed": True,
            "total_docs": len(index["documents"]),
        }


def search_rag(
    query: str,
    client_id: str = "",
    limit: int = 10,
    workspace: str | None = None,
    include_shared: bool = True,
) -> list[dict[str, Any]]:
    """Wyszukuje w RAG per-klient (i opcjonalnie wspoldzielonym).

    Prosty algorytm: dopasowanie keyword (TF) - zlicza wspolne tokeny
    miedzy zapytaniem a dokumentem.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    results: list[dict[str, Any]] = []

    # Wyszukaj w RAG per-klient
    if client_id:
        client_path = _rag_index_path(client_id, workspace)
        client_index = _load_index(client_path)
        for doc in client_index.get("documents", []):
            doc_tokens = set(doc.get("tokens", []))
            overlap = len(query_tokens & doc_tokens)
            if overlap > 0:
                score = overlap / len(query_tokens)
                results.append({
                    "doc_id": doc.get("doc_id", ""),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "score": round(score, 3),
                    "scope": "client",
                    "client_id": client_id,
                    "metadata": doc.get("metadata", {}),
                })

    # Wyszukaj we wspoldzielonym RAG
    if include_shared:
        shared_path = _rag_index_path("", workspace)
        shared_index = _load_index(shared_path)
        for doc in shared_index.get("documents", []):
            doc_tokens = set(doc.get("tokens", []))
            overlap = len(query_tokens & doc_tokens)
            if overlap > 0:
                score = overlap / len(query_tokens)
                results.append({
                    "doc_id": doc.get("doc_id", ""),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "score": round(score, 3),
                    "scope": "shared",
                    "client_id": "",
                    "metadata": doc.get("metadata", {}),
                })

    # Sortuj po score malejaco
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def search_client_rag(
    query: str, client_id: str, limit: int = 10, workspace: str = "",
    include_shared: bool = True,
) -> list[dict[str, Any]]:
    """Wyszukuje w RAG per-klient (i opcjonalnie wspoldzielonym)."""
    ws = workspace if workspace else None
    return search_rag(query, client_id, limit, ws, include_shared=include_shared)


def search_shared_rag(
    query: str, limit: int = 10, workspace: str = ""
) -> list[dict[str, Any]]:
    """Wyszukuje wylacznie we wspoldzielonym RAG."""
    ws = workspace if workspace else None
    return search_rag(query, "", limit, ws, include_shared=True)


def list_rag_documents(
    client_id: str = "", workspace: str = ""
) -> list[dict[str, Any]]:
    """Lista dokumentow w RAG per-klient (lub wspoldzielonym)."""
    ws = workspace if workspace else None
    path = _rag_index_path(client_id, ws)
    index = _load_index(path)
    return [
        {
            "doc_id": d.get("doc_id", ""),
            "title": d.get("title", ""),
            "scope": d.get("scope", ""),
            "indexed_at": d.get("indexed_at", ""),
        }
        for d in index.get("documents", [])
    ]
