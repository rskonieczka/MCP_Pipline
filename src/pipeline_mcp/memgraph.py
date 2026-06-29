"""Integracja z Memgraph (opcjonalna).

Memgraph stanowi warstwe grafowa uzupełniajaca checkpointy plikowe.
Jesli niedostepny, serwer kontynuuje bez zapisu grafu.
"""
from __future__ import annotations

import logging
from typing import Any

from .config import get_config
from .models import Envelope, MemgraphUnavailableError

logger = logging.getLogger(__name__)

# Lazy import neo4j
_driver = None
_driver_checked = False


def _get_driver():
    """Zwraca sterownik neo4j (lazy init). None jesli niedostepny."""
    global _driver, _driver_checked
    if _driver_checked:
        return _driver
    _driver_checked = True

    config = get_config()
    if not config.memgraph_enabled:
        logger.info("Memgraph wylaczony przez konfiguracje")
        return None

    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(
            config.memgraph_url,
            auth=(config.memgraph_user, config.memgraph_password) if config.memgraph_user else None,
        )
        # Test polaczenia
        with _driver.session() as session:
            session.run("RETURN 1").consume()
        logger.info(f"Polaczono z Memgraph: {config.memgraph_url}")
    except ImportError:
        logger.warning("Pakiet neo4j nie zainstalowany. Memgraph niedostepny.")
        _driver = None
    except Exception as e:
        logger.warning(f"Memgraph niedostepny: {e}")
        _driver = None

    return _driver


def is_available() -> bool:
    """Sprawdza czy Memgraph jest dostepny."""
    return _get_driver() is not None


def write_run_node(run_id: str, zamiar: str, sciezka: str) -> bool:
    """Zapisuje wezel Run do Memgraph."""
    driver = _get_driver()
    if driver is None:
        return False

    try:
        with driver.session() as session:
            session.run(
                "CREATE (r:Run {run_id: $run_id, zamiar: $zamiar, "
                "sciezka: $sciezka, status: 'w_trakcie'})",
                run_id=run_id, zamiar=zamiar, sciezka=sciezka,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Run: {e}")
        return False


def write_station_node(
    run_id: str, station: str, status: str, checkpoint: str = ""
) -> bool:
    """Zapisuje wezel Stacja do Memgraph."""
    driver = _get_driver()
    if driver is None:
        return False

    try:
        with driver.session() as session:
            session.run(
                "CREATE (s:Stacja {run_id: $run_id, stacja: $station, "
                "status: $status, checkpoint: $checkpoint})",
                run_id=run_id, station=station, status=status, checkpoint=checkpoint,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Stacja: {e}")
        return False


def write_relation(
    source: str, target: str, rel_type: str, fields: list[str] | None = None
) -> bool:
    """Zapisuje krawedz miedzy wezlami."""
    driver = _get_driver()
    if driver is None:
        return False

    try:
        rel_type_safe = rel_type.upper().replace("-", "_")
        with driver.session() as session:
            # Szukaj wezlow po id (konwencja: stacja:<name>, run:<id>, zmienna:<id>)
            session.run(
                f"MERGE (a {{id: $source}}) MERGE (b {{id: $target}}) "
                f"CREATE (a)-[:{rel_type_safe}]->(b)",
                source=source, target=target,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu relacji {source}->{target}: {e}")
        return False


def write_relations_from_envelope(run_id: str, envelope: Envelope) -> bool:
    """Zapisuje relacje z sekcji relacje koperty do Memgraph."""
    driver = _get_driver()
    if driver is None:
        return False

    success = True
    for rel in envelope.relacje:
        if not write_relation(rel.zrodlo, rel.cel, rel.typ, rel.pola):
            success = False

    return success


def close_run_node(run_id: str) -> bool:
    """Oznacza wezel Run jako zakonczony."""
    driver = _get_driver()
    if driver is None:
        return False

    try:
        with driver.session() as session:
            session.run(
                "MATCH (r:Run {run_id: $run_id}) "
                "SET r.status = 'zakonczony'",
                run_id=run_id,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zamykania wezla Run: {e}")
        return False


def validate_graph_continuity(run_id: str) -> list[str]:
    """Walidacja ciaglosci grafu. Zwraca liste anomalii."""
    driver = _get_driver()
    if driver is None:
        return []

    anomalies: list[str] = []
    try:
        with driver.session() as session:
            # Stacje bez poprzednika (oprocz inicjuj)
            result = session.run(
                "MATCH (s:Stacja {run_id: $run_id}) "
                "WHERE s.stacja <> 'inicjuj' "
                "AND NOT (s)-[:NASTAPILA_PO]->(:Stacja) "
                "RETURN s.stacja as stacja",
                run_id=run_id,
            )
            for record in result:
                anomalies.append(
                    f"Stacja '{record['stacja']}' bez poprzednika w grafie"
                )
    except Exception as e:
        logger.warning(f"Blad walidacji grafu: {e}")

    return anomalies
