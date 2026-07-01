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
    """Zapisuje wezel Run do Memgraph.

    Uzywa konwencji id='run:<run_id>' spojnej z write_relation,
    aby relacje i wezly strukturalne wskazywaly na ten sam wezel.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        run_node_id = f"run:{run_id}"
        with driver.session() as session:
            session.run(
                "MERGE (r:Run {id: $run_node_id}) "
                "SET r.run_id = $run_id, r.zamiar = $zamiar, "
                "r.sciezka = $sciezka, r.status = 'w_trakcie'",
                run_node_id=run_node_id, run_id=run_id,
                zamiar=zamiar, sciezka=sciezka,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Run: {e}")
        return False


def write_station_node(
    run_id: str, station: str, status: str, checkpoint: str = ""
) -> bool:
    """Zapisuje wezel Stacja do Memgraph.

    Uzywa konwencji id='stacja:<name>' spojnej z write_relation,
    aby relacje i wezly strukturalne wskazywaly na ten sam wezel.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        station_id = f"stacja:{station}"
        with driver.session() as session:
            session.run(
                "MERGE (s:Stacja {id: $station_id}) "
                "SET s.run_id = $run_id, s.stacja = $station, "
                "s.status = $status, s.checkpoint = $checkpoint",
                station_id=station_id, run_id=run_id,
                station=station, status=status, checkpoint=checkpoint,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Stacja: {e}")
        return False


def write_relation(
    source: str, target: str, rel_type: str, fields: list[str] | None = None
) -> bool:
    """Zapisuje krawedz miedzy wezlami.

    Nadaje labeli wezlom na podstawie konwencji id:
    - 'run:*' -> label :Run
    - 'stacja:*' -> label :Stacja
    Pozostale wezly pozostaja generyczne (bez dodatkowego labela).
    Uzywa MERGE dla relacji aby uniknac duplikacji.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        rel_type_safe = rel_type.upper().replace("-", "_")
        # Okresl labeli na podstawie konwencji id
        source_label = _label_for_id(source)
        target_label = _label_for_id(target)

        with driver.session() as session:
            # MERGE wezlow z opcjonalnymi labelami i id
            source_clause = (
                f"MERGE (a:{source_label} {{id: $source}})"
                if source_label else "MERGE (a {{id: $source}})"
            )
            target_clause = (
                f"MERGE (b:{target_label} {{id: $target}})"
                if target_label else "MERGE (b {{id: $target}})"
            )
            session.run(
                f"{source_clause} {target_clause} "
                f"MERGE (a)-[:{rel_type_safe}]->(b)",
                source=source, target=target,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu relacji {source}->{target}: {e}")
        return False


def _label_for_id(node_id: str) -> str:
    """Zwraca label dla wezla na podstawie konwencji id."""
    _LABEL_MAP = {
        "run:": "Run",
        "stacja:": "Stacja",
        "zmienna:": "Zmienna",
        "podproblem:": "Podproblem",
        "decyzja:": "Decyzja",
        "krok:": "KrokPlanu",
        "zmiana:": "Zmiana",
        "twierdzenie:": "Twierdzenie",
        "werdykt:": "Werdykt",
        "wymiar:": "WymiarAudytu",
        "wniosek:": "Wniosek",
        "checkpoint:": "Checkpoint",
    }
    for prefix, label in _LABEL_MAP.items():
        if node_id.startswith(prefix):
            return label
    return ""


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


def close_run_node(run_id: str, timestamp_end: str = "") -> bool:
    """Oznacza wezel Run jako zakonczony. Tworzy wezel jesli nie istnieje."""
    driver = _get_driver()
    if driver is None:
        return False

    try:
        run_node_id = f"run:{run_id}"
        if timestamp_end:
            with driver.session() as session:
                session.run(
                    "MERGE (r:Run {id: $run_node_id}) "
                    "SET r.status = 'zakonczony', r.timestamp_end = $timestamp_end",
                    run_node_id=run_node_id, timestamp_end=timestamp_end,
                )
        else:
            with driver.session() as session:
                session.run(
                    "MERGE (r:Run {id: $run_node_id}) "
                    "SET r.status = 'zakonczony'",
                    run_node_id=run_node_id,
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
