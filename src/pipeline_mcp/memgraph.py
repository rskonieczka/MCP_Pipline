"""Integracja z Memgraph (opcjonalna).

Memgraph stanowi warstwe grafowa uzupełniajaca checkpointy plikowe.
Jesli niedostepny, serwer kontynuuje bez zapisu grafu.
"""
from __future__ import annotations

import logging
import re

from .config import get_config
from .models import Envelope

logger = logging.getLogger(__name__)

# Dozwolony format typu relacji po normalizacji (ochrona przed Cypher injection,
# bo typ relacji nie moze byc parametrem zapytania)
_REL_TYPE_RE = re.compile(r"[A-Z_][A-Z0-9_]*")

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

    Uzywa konwencji id='stacja:<run_id>:<name>' spojnej z write_relation
    i add_station_relations. Wezel stacji jest per run - dzieki temu
    statusy i relacje NASTAPILA_PO roznych run'ow nie mieszaja sie.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        station_id = f"stacja:{run_id}:{station}"
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
        # Typ relacji jest interpolowany do zapytania - waliduj whitelista
        if not _REL_TYPE_RE.fullmatch(rel_type_safe):
            logger.warning(
                f"Odrzucono relacje {source}->{target}: "
                f"nieprawidlowy typ relacji '{rel_type}'"
            )
            return False
        # Okresl labeli na podstawie konwencji id
        source_label = _label_for_id(source)
        target_label = _label_for_id(target)

        with driver.session() as session:
            # MERGE wezlow z opcjonalnymi labelami i id
            source_clause = (
                f"MERGE (a:{source_label} {{id: $source}})"
                if source_label else "MERGE (a {id: $source})"
            )
            target_clause = (
                f"MERGE (b:{target_label} {{id: $target}})"
                if target_label else "MERGE (b {id: $target})"
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
        "wymaganie:": "Wymaganie",
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

    # Zapisz wezly Wymaganie i relacje z RTM
    if envelope.rtm:
        if not write_rtm_nodes(run_id, envelope):
            success = False

    return success


def write_rtm_nodes(run_id: str, envelope: Envelope) -> bool:
    """Zapisuje wezly Wymaganie i relacje ADRESUJE/WERYFIKUJE do Memgraph.

    Dla kazdego wpisu RTM tworzy wezel :Wymaganie i laczy go ze stacjami
    adresujacymi relacja ADRESUJE oraz ze stacja weryfikujaca relacja WERYFIKUJE.
    """
    driver = _get_driver()
    if driver is None:
        return False

    success = True
    run_node_id = f"run:{run_id}"

    for entry in envelope.rtm:
        req_node_id = f"wymaganie:{run_id}:{entry.req_id}"
        try:
            with driver.session() as session:
                # Wezel Wymaganie
                session.run(
                    "MERGE (w:Wymaganie {id: $req_node_id}) "
                    "SET w.req_id = $req_id, w.opis = $opis, "
                    "w.status = $status, w.zrodlo = $zrodlo",
                    req_node_id=req_node_id,
                    req_id=entry.req_id,
                    opis=entry.opis,
                    status=entry.status,
                    zrodlo=entry.zrodlo,
                )
                # Relacja: Run ZAWIERA Wymaganie
                session.run(
                    "MERGE (r:Run {id: $run_node_id}) "
                    "MERGE (w:Wymaganie {id: $req_node_id}) "
                    "MERGE (r)-[:ZAWIERA]->(w)",
                    run_node_id=run_node_id,
                    req_node_id=req_node_id,
                )
                # Relacje: Stacja ADRESUJE Wymaganie
                for stacja in entry.stacje_adresujace:
                    station_id = f"stacja:{run_id}:{stacja}"
                    session.run(
                        "MERGE (s:Stacja {id: $station_id}) "
                        "MERGE (w:Wymaganie {id: $req_node_id}) "
                        "MERGE (s)-[:ADRESUJE]->(w)",
                        station_id=station_id,
                        req_node_id=req_node_id,
                    )
                # Relacja: Stacja WERYFIKUJE Wymaganie
                if entry.stacja_weryfikujaca:
                    station_id = f"stacja:{run_id}:{entry.stacja_weryfikujaca}"
                    session.run(
                        "MERGE (s:Stacja {id: $station_id}) "
                        "MERGE (w:Wymaganie {id: $req_node_id}) "
                        "MERGE (s)-[:WERYFIKUJE]->(w)",
                        station_id=station_id,
                        req_node_id=req_node_id,
                    )
        except Exception as e:
            logger.warning(f"Blad zapisu wezla Wymaganie {entry.req_id}: {e}")
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
