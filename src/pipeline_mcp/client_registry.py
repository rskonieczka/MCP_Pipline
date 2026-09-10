"""Rejestr klientow z aliasami, identyfikatorami zewnetrznymi i dopasowaniem.

System wieloklientowy (multi-tenant). Kazdy klient ma kanoniczny client_id (slug)
oraz liste aliasow i identyfikatorow zewnetrznych (NIP, telefon, KRS) do
rozpoznawania z niejednoznacznych identyfikatorow.

Struktura pliku klienta:
    <workspace>/.ai-kb/clients/<client_id>/context.yaml

Warstwy dopasowania (od najpewniejszej):
    L1 (100%): exact client_id
    L2 (100%): exact external_id (NIP, telefon, KRS)
    L3 (95%):  exact alias (normalized)
    L4 (80%):  id_fragment (np. ostatnie 4 cyfry NIP)
    L5 (60-79%): fuzzy name (podobienstwo leksykalne)
    L6 (0%):   brak dopasowania

Progi:
    >= 100%: auto-przypisz (nie pytaj)
    >= 60%:  sugeruj, pytaj o potwierdzenie
    < 60%:   brak dopasowania, zaproponuj rejestracje
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from .config import get_config
from .models import (
    AmbiguousClientError,
    ClientAlreadyExistsError,
    ClientContext,
    ClientMatch,
    ClientNotFoundError,
    InvalidClientIdError,
    PipelineError,
    ResolveResult,
)

logger = logging.getLogger(__name__)

# Walidacja client_id: slug [a-z0-9][a-z0-9-]*[a-z0-9] (min 2 znaki)
CLIENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

# Progi pewnosci
AUTO_RESOLVE_THRESHOLD = 100
SUGGEST_THRESHOLD = 60

# Poziomy pewnosci per warstwa
_CONFIDENCE_LEVELS = {
    "client_id": 100,
    "external_id": 100,
    "alias": 95,
    "id_fragment": 80,
}


def normalize(s: str) -> str:
    """Normalizuje string do dopasowania.

    Operacje:
    - Zamien polskie znaki na ASCII odpowiedniki (ł->l, ż->z, ś->s, etc.)
    - Usun akcenty (NFKD -> ASCII)
    - Lowercase
    - Usun spacje, mylniki, kropki, przecinki, podkreslenia, nawiasy

    Przyklady:
        "UrsaMajor" -> "ursamajor"
        "ursa major" -> "ursamajor"
        "262-977-6197" -> "2629776197"
        "Zółw S.A." -> "zolwsa"
    """
    # Polskie znaki -> ASCII (NFKD nie rozklada ł, ź, ż, ś, etc.)
    pl_map = str.maketrans({
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "a", "Ć": "c", "Ę": "e", "Ł": "l", "Ń": "n",
        "Ó": "o", "Ś": "s", "Ź": "z", "Ż": "z",
    })
    s = s.translate(pl_map)
    # Usun pozostale akcenty
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    # Lowercase
    s = s.lower()
    # Usun separatory i interpunkcje
    s = re.sub(r'[\s\-.,_()\'"]+', "", s)
    return s


def validate_client_id(client_id: str) -> None:
    """Waliduje format client_id. Rzuca InvalidClientIdError przy nieprawidlowym formacie."""
    if not client_id:
        raise InvalidClientIdError("client_id jest wymagany")
    if not CLIENT_ID_RE.fullmatch(client_id):
        raise InvalidClientIdError(
            f"Nieprawidlowy client_id '{client_id}'. "
            "Wymagany format: slug [a-z0-9][a-z0-9-]*[a-z0-9] (min 2 znaki, bez spacji)."
        )


def _similarity(a: str, b: str) -> float:
    """Proste podobienstwo leksykalne oparte na wspolnych znakach.

    Zwraca wartosc 0.0-1.0. Uzywa prostego algorytmu opartego na dlugosci
    najdluzszego wspolnego podciagu (LCS) wzgledem dluzszego stringa.
    """
    if not a or not b:
        return 0.0

    # Najdluzszy wspolny podciag (LCS) - prosta implementacja
    m, n = len(a), len(b)
    # Optymalizacja: uzyj tylko 2 wierszy zamiast pelnej macierzy
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, prev
    lcs_len = prev[n]
    return lcs_len / max(m, n)


def load_client(client_id: str, workspace: str | None = None) -> ClientContext | None:
    """Laduje kontekst klienta z pliku context.yaml.

    Zwraca None jesli klient nie istnieje.
    """
    validate_client_id(client_id)
    config = get_config()
    path = config.client_context_path(client_id, workspace)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return ClientContext(**data)
    except Exception as e:
        logger.warning(f"Blad ladowania klienta {client_id}: {e}")
        return None


def load_all_clients(workspace: str | None = None) -> list[ClientContext]:
    """Laduje wszystkich zarejestrowanych klientow."""
    config = get_config()
    clients_dir = config.clients_dir(workspace)
    if not clients_dir.exists():
        return []

    clients: list[ClientContext] = []
    for d in sorted(clients_dir.iterdir()):
        if not d.is_dir():
            continue
        context_path = d / "context.yaml"
        if not context_path.exists():
            continue
        try:
            with open(context_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            clients.append(ClientContext(**data))
        except Exception as e:
            logger.warning(f"Blad ladowania klienta z {d.name}: {e}")
    return clients


def register_client(
    client_id: str,
    display_name: str,
    aliases: list[str] | None = None,
    external_ids: dict[str, str] | None = None,
    id_fragments: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> ClientContext:
    """Rejestruje nowego klienta z aliasami i identyfikatorami zewnetrznymi.

    Rzuca ClientAlreadyExistsError jesli klient juz istnieje.
    """
    validate_client_id(client_id)

    # Sprawdz czy klient juz istnieje
    existing = load_client(client_id, workspace)
    if existing is not None:
        raise ClientAlreadyExistsError(
            f"Klient '{client_id}' juz istnieje. Uzyj update_client aby zmodyfikowac."
        )

    context = ClientContext(
        client_id=client_id,
        display_name=display_name,
        aliases=aliases or [],
        external_ids=external_ids or {},
        id_fragments=id_fragments or [],
        metadata=metadata or {},
    )

    _save_client(context, workspace)
    return context


def update_client(
    client_id: str,
    updates: dict[str, Any],
    workspace: str | None = None,
) -> ClientContext:
    """Aktualizuje aliasy, external_ids, id_fragments, metadane klienta.

    Rzuca ClientNotFoundError jesli klient nie istnieje.
    """
    validate_client_id(client_id)
    context = load_client(client_id, workspace)
    if context is None:
        raise ClientNotFoundError(f"Klient '{client_id}' nie istnieje.")

    if "display_name" in updates:
        context.display_name = updates["display_name"]
    if "aliases" in updates:
        context.aliases = updates["aliases"]
    if "external_ids" in updates:
        context.external_ids = updates["external_ids"]
    if "id_fragments" in updates:
        context.id_fragments = updates["id_fragments"]
    if "metadata" in updates:
        context.metadata = updates["metadata"]
    if "status" in updates:
        context.status = updates["status"]  # type: ignore

    _save_client(context, workspace)
    return context


def archive_client(client_id: str, workspace: str | None = None) -> ClientContext:
    """Archiwizuje klienta (zmiana statusu na zarchiwizowany).

    Dane klienta pozostaja na dysku, ale klient nie jest brany pod uwage
    w resolve_client.
    """
    validate_client_id(client_id)
    return update_client(client_id, {"status": "zarchiwizowany"}, workspace)


def delete_client(client_id: str, workspace: str | None = None) -> dict[str, Any]:
    """Usuwa klienta i wszystkie jego dane (GDPR right to be forgotten).

    Usuwa:
    - context.yaml
    - pipeline-runs/
    - rag/
    - memory/

    Rzuca ClientNotFoundError jesli klient nie istnieje.
    """
    import shutil

    validate_client_id(client_id)
    config = get_config()
    client_dir = config.client_dir(client_id, workspace)

    if not client_dir.exists():
        raise ClientNotFoundError(f"Klient '{client_id}' nie istnieje.")

    # Policz co usuwamy - PRZED rmtree (po rmtree sciezki nie istnieja)
    runs_dir = client_dir / "pipeline-runs"
    run_count = len([d for d in runs_dir.iterdir() if d.is_dir()]) if runs_dir.exists() else 0
    rag_existed = (client_dir / "rag").exists()
    memory_existed = (client_dir / "memory").exists()

    shutil.rmtree(client_dir)

    # Usun wezly grafu klienta z Memgraph (GDPR right to be forgotten)
    from . import memgraph
    memgraph_deleted = memgraph.delete_client_nodes(client_id)

    return {
        "client_id": client_id,
        "deleted": True,
        "runs_deleted": run_count,
        "rag_deleted": rag_existed,
        "memory_deleted": memory_existed,
        "memgraph_deleted": memgraph_deleted,
    }


def resolve_client(query: str, workspace: str | None = None) -> ResolveResult:
    """Rozpoznaje klienta na podstawie niejednoznacznego identyfikatora.

    Przeszukuje rejestr klientow: client_id, aliasy, identyfikatory zewnetrzne
    (NIP, telefon, KRS), fragmenty identyfikatorow. Zwraca kandydatow z
    poziomem pewnosci.

    Przy 100% pewnosci auto-przypisuje. Ponizej 100% zwraca needs_confirmation=true
    i agent powinien zapytac uzytkownika o potwierdzenie.
    """
    normalized = normalize(query)
    clients = load_all_clients(workspace)

    # Filtruj tylko aktywnych klientow
    clients = [c for c in clients if c.status == "aktywny"]

    matches: list[ClientMatch] = []

    for client in clients:
        matched = False

        # L1: exact client_id
        if normalized == normalize(client.client_id):
            matches.append(ClientMatch(
                client_id=client.client_id,
                display_name=client.display_name,
                confidence=_CONFIDENCE_LEVELS["client_id"],
                matched_on="client_id",
            ))
            matched = True
            continue

        # L2: exact external_id
        if not matched:
            for id_type, id_value in client.external_ids.items():
                if normalized == normalize(id_value):
                    matches.append(ClientMatch(
                        client_id=client.client_id,
                        display_name=client.display_name,
                        confidence=_CONFIDENCE_LEVELS["external_id"],
                        matched_on=f"external_id:{id_type}",
                    ))
                    matched = True
                    break

        # L3: exact alias (normalized)
        if not matched:
            for alias in client.aliases:
                if normalized == normalize(alias):
                    matches.append(ClientMatch(
                        client_id=client.client_id,
                        display_name=client.display_name,
                        confidence=_CONFIDENCE_LEVELS["alias"],
                        matched_on="alias",
                    ))
                    matched = True
                    break

        # L4: id_fragment
        if not matched:
            for fragment in client.id_fragments:
                if normalized == normalize(fragment):
                    matches.append(ClientMatch(
                        client_id=client.client_id,
                        display_name=client.display_name,
                        confidence=_CONFIDENCE_LEVELS["id_fragment"],
                        matched_on="id_fragment",
                    ))
                    matched = True
                    break

        # L5: fuzzy name (zawsze wymaga potwierdzenia - max 79%)
        if not matched:
            name_norm = normalize(client.display_name)
            sim = _similarity(normalized, name_norm)
            if sim >= 0.6:
                matches.append(ClientMatch(
                    client_id=client.client_id,
                    display_name=client.display_name,
                    confidence=min(int(sim * 100), 79),
                    matched_on="fuzzy_name",
                ))

    # Sortuj po pewnosci malejaco
    matches.sort(key=lambda m: m.confidence, reverse=True)

    # Auto-resolve: dokladnie 1 match na 100%
    auto = len(matches) == 1 and matches[0].confidence >= AUTO_RESOLVE_THRESHOLD

    # Potrzeba potwierdzenia: jakikolwiek match ponizej 100% lub wielu kandydatow
    needs_confirm = bool(matches) and not auto

    # Sugerowana akcja
    suggested = ""
    if not matches:
        suggested = (
            "Nie znaleziono klienta. Zarejestruj nowego przez register_client "
            "lub podaj inny identyfikator."
        )
    elif auto:
        suggested = f"Auto-rozpoznano: {matches[0].display_name} ({matches[0].client_id})."
    elif len(matches) == 1:
        suggested = (
            f"Zapytaj uzytkownika: 'Czy chodzi o klienta {matches[0].display_name}?"
        )
    else:
        names = "; ".join(
            f"{i + 1}) {m.display_name}" for i, m in enumerate(matches[:5])
        )
        suggested = (
            f"Zapytaj uzytkownika o wybor: 'Znaleziono {len(matches)} klientow: "
            f"{names}. Dla ktorego pracujesz?'"
        )

    return ResolveResult(
        query=query,
        normalized=normalized,
        matches=matches,
        auto_resolved=auto,
        needs_confirmation=needs_confirm,
        suggested_action=suggested,
    )


def _save_client(context: ClientContext, workspace: str | None = None) -> None:
    """Zapisuje kontekst klienta do pliku context.yaml (atomowo)."""
    config = get_config()
    path = config.client_context_path(context.client_id, workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=path.stem
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(
                context.model_dump(),
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
