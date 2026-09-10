"""Integracja z Memgraph (opcjonalna).

Memgraph stanowi warstwe grafowa uzupełniajaca checkpointy plikowe.
Jesli niedostepny, serwer kontynuuje bez zapisu grafu.

MT: Wezly Run, Stacja, Wymaganie posiadaja client_id w ID wezla dla izolacji
wieloklientowej. Wezly wiedzy wspoldzielonej maja client_id = "shared".
Konwencja ID (z client_id dla izolacji, bez dla legacy):
  run:<client_id>:<run_id>  lub  run:<run_id> (legacy)
  stacja:<client_id>:<run_id>:<station>  lub  stacja:<run_id>:<station> (legacy)
  wymaganie:<client_id>:<run_id>:<req_id>  lub  wymaganie:<run_id>:<req_id> (legacy)
  pamiec:<effective_client_id>:<memory_id>
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


def _run_node_id(run_id: str, client_id: str = "") -> str:
    """ID wezla Run z izolacja client_id (legacy gdy client_id puste)."""
    return f"run:{client_id}:{run_id}" if client_id else f"run:{run_id}"


def _station_node_id(run_id: str, station: str, client_id: str = "") -> str:
    """ID wezla Stacja z izolacja client_id (legacy gdy client_id puste)."""
    return f"stacja:{client_id}:{run_id}:{station}" if client_id else f"stacja:{run_id}:{station}"


def _req_node_id(run_id: str, req_id: str, client_id: str = "") -> str:
    """ID wezla Wymaganie z izolacja client_id (legacy gdy client_id puste)."""
    return f"wymaganie:{client_id}:{run_id}:{req_id}" if client_id else f"wymaganie:{run_id}:{req_id}"

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


def write_run_node(run_id: str, zamiar: str, sciezka: str, client_id: str = "") -> bool:
    """Zapisuje wezel Run do Memgraph.

    Uzywa konwencji id z _run_node_id (z client_id dla izolacji),
    spojnej z write_relation i add_station_relations.

    MT: client_id w ID wezla zapobiega kolizjom miedzy klientami.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        run_node_id = _run_node_id(run_id, client_id)
        with driver.session() as session:
            session.run(
                "MERGE (r:Run {id: $run_node_id}) "
                "SET r.run_id = $run_id, r.zamiar = $zamiar, "
                "r.sciezka = $sciezka, r.status = 'w_trakcie', "
                "r.client_id = $client_id",
                run_node_id=run_node_id, run_id=run_id,
                zamiar=zamiar, sciezka=sciezka, client_id=client_id,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Run: {e}")
        return False


def write_station_node(
    run_id: str, station: str, status: str, checkpoint: str = "",
    client_id: str = "",
) -> bool:
    """Zapisuje wezel Stacja do Memgraph.

    Uzywa konwencji id z _station_node_id (z client_id dla izolacji),
    spojnej z write_relation i add_station_relations.

    MT: client_id w ID wezla zapobiega kolizjom miedzy klientami.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        station_id = _station_node_id(run_id, station, client_id)
        with driver.session() as session:
            session.run(
                "MERGE (s:Stacja {id: $station_id}) "
                "SET s.run_id = $run_id, s.stacja = $station, "
                "s.status = $status, s.checkpoint = $checkpoint, "
                "s.client_id = $client_id",
                station_id=station_id, run_id=run_id,
                station=station, status=status, checkpoint=checkpoint,
                client_id=client_id,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Stacja: {e}")
        return False


def write_relation(
    source: str, target: str, rel_type: str
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
        # MT: nowe typy wezlow
        "wiedza:": "Wiedza",
        "pamiec:": "Pamiec",
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
        if not write_relation(rel.zrodlo, rel.cel, rel.typ):
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

    MT: client_id w ID wezlow Wymaganie zapobiega kolizjom miedzy klientami.
    """
    driver = _get_driver()
    if driver is None:
        return False

    success = True
    client_id = envelope.client_id
    run_node_id = _run_node_id(run_id, client_id)

    for entry in envelope.rtm:
        req_node_id = _req_node_id(run_id, entry.req_id, client_id)
        try:
            with driver.session() as session:
                # Wezel Wymaganie
                session.run(
                    "MERGE (w:Wymaganie {id: $req_node_id}) "
                    "SET w.req_id = $req_id, w.opis = $opis, "
                    "w.status = $status, w.zrodlo = $zrodlo, "
                    "w.client_id = $client_id",
                    req_node_id=req_node_id,
                    req_id=entry.req_id,
                    opis=entry.opis,
                    status=entry.status,
                    zrodlo=entry.zrodlo,
                    client_id=client_id,
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
                    station_id = _station_node_id(run_id, stacja, client_id)
                    session.run(
                        "MERGE (s:Stacja {id: $station_id}) "
                        "MERGE (w:Wymaganie {id: $req_node_id}) "
                        "MERGE (s)-[:ADRESUJE]->(w)",
                        station_id=station_id,
                        req_node_id=req_node_id,
                    )
                # Relacja: Stacja WERYFIKUJE Wymaganie
                if entry.stacja_weryfikujaca:
                    station_id = _station_node_id(run_id, entry.stacja_weryfikujaca, client_id)
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


def close_run_node(run_id: str, timestamp_end: str = "", client_id: str = "") -> bool:
    """Oznacza wezel Run jako zakonczony. Tworzy wezel jesli nie istnieje.

    MT: client_id w ID wezla zapobiega zamknieciu wezla innego klienta.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        run_node_id = _run_node_id(run_id, client_id)
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


def validate_graph_continuity(run_id: str, client_id: str = "") -> list[str]:
    """Walidacja ciaglosci grafu. Zwraca liste anomalii.

    MT: Filtruje po client_id jesli podany.
    """
    driver = _get_driver()
    if driver is None:
        return []

    anomalies: list[str] = []
    try:
        with driver.session() as session:
            if client_id:
                # MT: filtruj po client_id
                result = session.run(
                    "MATCH (s:Stacja {run_id: $run_id, client_id: $client_id}) "
                    "WHERE s.stacja <> 'inicjuj' "
                    "AND NOT (s)-[:NASTAPILA_PO]->(:Stacja) "
                    "RETURN s.stacja as stacja",
                    run_id=run_id, client_id=client_id,
                )
            else:
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


# MT: Wezly wiedzy wspoldzielonej i pamieci per-klient

def write_shared_knowledge_node(
    knowledge_id: str, category: str, title: str, content: str
) -> bool:
    """Zapisuje wezel Wiedza (wspoldzielony) do Memgraph.

    Wezly wiedzy wspoldzielonej maja client_id = "shared".
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        node_id = f"wiedza:{knowledge_id}"
        with driver.session() as session:
            session.run(
                "MERGE (w:Wiedza {id: $node_id}) "
                "SET w.knowledge_id = $knowledge_id, w.category = $category, "
                "w.title = $title, w.content = $content, "
                "w.client_id = 'shared'",
                node_id=node_id, knowledge_id=knowledge_id,
                category=category, title=title, content=content,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Wiedza: {e}")
        return False


def write_client_memory_node(
    memory_id: str, client_id: str, topic: str, content: str, scope: str = "client"
) -> bool:
    """Zapisuje wezel Pamiec do Memgraph.

    scope='client' -> pamiec per-klient (client_id podany).
    scope='shared' -> pamiec wspoldzielona (client_id='shared').
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        effective_client_id = client_id if scope == "client" else "shared"
        node_id = f"pamiec:{effective_client_id}:{memory_id}"
        with driver.session() as session:
            session.run(
                "MERGE (p:Pamiec {id: $node_id}) "
                "SET p.memory_id = $memory_id, p.client_id = $effective_client_id, "
                "p.topic = $topic, p.content = $content, p.scope = $scope",
                node_id=node_id, memory_id=memory_id,
                effective_client_id=effective_client_id,
                topic=topic, content=content, scope=scope,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad zapisu wezla Pamiec: {e}")
        return False


def delete_client_nodes(client_id: str) -> bool:
    """Usuwa wszystkie wezly grafu nalezace do klienta (GDPR right to be forgotten).

    Usuwa wezly Run, Stacja, Wymaganie, Pamiec z client_id pasujacym.
    Wezly wiedzy wspoldzielonej (client_id='shared') nie sa usuwane.
    """
    driver = _get_driver()
    if driver is None:
        return False

    try:
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.client_id = $client_id "
                "AND n.client_id <> 'shared' "
                "DETACH DELETE n",
                client_id=client_id,
            )
        return True
    except Exception as e:
        logger.warning(f"Blad usuwania wezlow klienta {client_id}: {e}")
        return False
