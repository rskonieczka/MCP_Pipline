"""Requirements Traceability Matrix - sledzenie wymagan przez pipeline.

RTM mapuje wymagania uzytkownika (ekstrahowane ze stacji zmienne) na stacje
adresujace, stacje weryfikujace i artefakty wyjsciowe. Automatycznie aktualizuje
statusy wymagan w trakcie wykonywania pipeline'u.
"""
from __future__ import annotations

import logging
from typing import Any

from .models import Envelope, RTMEntry

logger = logging.getLogger(__name__)

# W4: dozwolone statusy RTM (zgodne z RTMStatus w models.py)
_VALID_RTM_STATUSES = frozenset({
    "nieadresowane", "adresowane", "zrealizowane", "weryfikowane", "niespelnione"
})


def extract_requirements_from_zmienne(output: dict[str, Any]) -> list[RTMEntry]:
    """Ekstrahuje wymagania z wyjscia stacji zmienne.

    Zmienne typu 'requirement' z ontologii skilla zmienne staja sie wpisami RTM.
    """
    entries: list[RTMEntry] = []
    variables = output.get("variables", [])

    if not isinstance(variables, list):
        return entries

    for i, var in enumerate(variables):
        if not isinstance(var, dict):
            continue
        var_type = str(var.get("type", "")).lower()
        if var_type != "requirement":
            continue

        req_id = var.get("id") or var.get("name") or f"REQ-{i + 1:03d}"
        opis = var.get("value") or var.get("description") or var.get("name", "")
        entries.append(RTMEntry(
            req_id=str(req_id),
            opis=str(opis),
            zrodlo="zmienne",
            stacje_adresujace=[],
            status="nieadresowane",
        ))

    return entries


def auto_update_rtm(
    envelope: Envelope, station: str, output: dict[str, Any]
) -> None:
    """Automatyczna aktualizacja RTM po wykonaniu stacji.

    Wywolywane z execute_station po accumulate_state. Modyfikuje envelope.rtm
    in-place.

    Stacje wyzwalajace aktualizacje:
    - zmienne: ekstrakcja wymagan z variables typu requirement
    - realizuj: oznaczanie wymagan jako zrealizowane (kroki_wykonane)
    - weryfikacja: oznaczanie wymagan jako weryfikowane (werdykty potwierdzone)
    - sprawdzenie: oznaczanie niespelnionych wymagan (wymiar Zgodnosc = niezgodny)
    """
    if station == "zmienne":
        _update_after_zmienne(envelope, output)
    elif station == "realizuj":
        _update_after_realizuj(envelope, output)
    elif station == "weryfikacja":
        _update_after_weryfikacja(envelope, output)
    elif station == "sprawdzenie":
        _update_after_sprawdzenie(envelope, output)


def _update_after_zmienne(envelope: Envelope, output: dict[str, Any]) -> None:
    """Ekstrahuje wymagania z wyjscia zmienne i dodaje do RTM."""
    new_entries = extract_requirements_from_zmienne(output)
    existing_ids = {e.req_id for e in envelope.rtm}

    for entry in new_entries:
        if entry.req_id not in existing_ids:
            entry.stacje_adresujace.append("zmienne")
            entry.status = "adresowane"
            envelope.rtm.append(entry)


def _update_after_realizuj(envelope: Envelope, output: dict[str, Any]) -> None:
    """Oznacza wymagania jako zrealizowane na podstawie wykonanych krokow.

    Dopasowuje req_id wymagan do tresci kroki_wykonane (po req_id lub opisie).
    """
    kroki = output.get("kroki_wykonane", [])
    if not isinstance(kroki, list):
        return

    kroki_text = " ".join(str(k) for k in kroki).lower()

    for entry in envelope.rtm:
        if entry.status in ("nieadresowane", "adresowane"):
            if "realizuj" not in entry.stacje_adresujace:
                entry.stacje_adresujace.append("realizuj")
            # U1: sprawdzaj dopasowanie opisu tylko gdy niepusty -
            # pusty opis powoduje 'in' zwracac True dla dowolnego tekstu
            if entry.req_id.lower() in kroki_text or (
                entry.opis and entry.opis.lower() in kroki_text
            ):
                entry.status = "zrealizowane"


def _update_after_weryfikacja(envelope: Envelope, output: dict[str, Any]) -> None:
    """Oznacza wymagania jako weryfikowane na podstawie werdyktow.

    Werdykty potwierdzone mapuja na status 'weryfikowane'.
    Werdykty obalone mapuja na status 'niespelnione'.
    """
    werdykty = output.get("werdykty", [])
    if not isinstance(werdykty, list):
        return

    for werdykt in werdykty:
        if not isinstance(werdykt, dict):
            continue
        status_w = str(werdykt.get("status", "")).lower()
        tekst = str(werdykt.get("twierdzenie", "")) + " " + str(werdykt.get("uzasadnienie", ""))
        tekst_lower = tekst.lower()

        for entry in envelope.rtm:
            # U1: sprawdzaj dopasowanie opisu tylko gdy niepusty -
            # pusty opis powoduje 'in' zwracac True dla dowolnego tekstu
            if entry.req_id.lower() in tekst_lower or (
                entry.opis and entry.opis.lower() in tekst_lower
            ):
                entry.stacja_weryfikujaca = "weryfikacja"
                if status_w == "potwierdzony":
                    if entry.status != "niespelnione":
                        entry.status = "weryfikowane"
                elif status_w == "obalony":
                    entry.status = "niespelnione"


def _update_after_sprawdzenie(envelope: Envelope, output: dict[str, Any]) -> None:
    """Oznacza niespelnione wymagania na podstawie wymiaru Zgodnosc audytu.

    Jesli wymiar Zgodnosc = niezgodny, wymagania w statusie 'weryfikowane'
    moga zostac oznaczone jako 'niespelnione'.
    """
    wymiary = output.get("wymiary", {})
    if not isinstance(wymiary, dict):
        return

    zgodnosc = str(wymiary.get("Zgodnosc", "")).lower()
    if zgodnosc != "niezgodny":
        return

    for entry in envelope.rtm:
        if entry.status == "weryfikowane":
            entry.status = "niespelnione"
            # U6: nie nadpisuj stacja_weryfikujaca - zachowaj pierwotna weryfikacje
            entry.stacja_niespelnienia = "sprawdzenie"


def validate_coverage(envelope: Envelope) -> dict[str, Any]:
    """Zwraca raport pokrycia wymagan w RTM.

    Metryki: laczna liczba, nieadresowane, adresowane, zrealizowane,
    weryfikowane, niespelnione, procent pokrycia.
    """
    total = len(envelope.rtm)
    if total == 0:
        return {
            "total": 0,
            "nieadresowane": 0,
            "adresowane": 0,
            "zrealizowane": 0,
            "weryfikowane": 0,
            "niespelnione": 0,
            "pokrycie_procent": 100.0,
            "nieadresowane_ids": [],
            "niespelnione_ids": [],
            "status": "brak_wymagan",
        }

    nieadresowane = [e for e in envelope.rtm if e.status == "nieadresowane"]
    adresowane = [e for e in envelope.rtm if e.status == "adresowane"]
    zrealizowane = [e for e in envelope.rtm if e.status == "zrealizowane"]
    weryfikowane = [e for e in envelope.rtm if e.status == "weryfikowane"]
    niespelnione = [e for e in envelope.rtm if e.status == "niespelnione"]

    pokryte = len(zrealizowane) + len(weryfikowane)
    pokrycie = round((pokryte / total) * 100, 1) if total > 0 else 100.0

    if niespelnione:
        status = "niekompletne"
    elif nieadresowane or adresowane:
        status = "w_trakcie"
    else:
        status = "kompletne"

    return {
        "total": total,
        "nieadresowane": len(nieadresowane),
        "adresowane": len(adresowane),
        "zrealizowane": len(zrealizowane),
        "weryfikowane": len(weryfikowane),
        "niespelnione": len(niespelnione),
        "pokrycie_procent": pokrycie,
        "nieadresowane_ids": [e.req_id for e in nieadresowane],
        "niespelnione_ids": [e.req_id for e in niespelnione],
        "status": status,
    }


def update_entry(
    envelope: Envelope, req_id: str, updates: dict[str, Any]
) -> RTMEntry | None:
    """Aktualizuje pojedynczy wpis RTM po req_id. Zwraca zaktualizowany wpis."""
    for entry in envelope.rtm:
        if entry.req_id == req_id:
            for key, value in updates.items():
                if hasattr(entry, key):
                    if key == "status":
                        # W4 (A4): walidacja statusu - wczesniej dowolna wartosc
                        # byla przyjmowana, wpis znikal ze wszystkich kubelkow
                        # pokrycia w validate_coverage
                        if value not in _VALID_RTM_STATUSES:
                            raise ValueError(
                                f"Nieprawidlowy status RTM '{value}'. "
                                f"Dostepne: {sorted(_VALID_RTM_STATUSES)}"
                            )
                        entry.status = value  # type: ignore
                    elif key == "stacje_adresujace" and isinstance(value, list):
                        for s in value:
                            if s not in entry.stacje_adresujace:
                                entry.stacje_adresujace.append(s)
                    elif key == "artefakty" and isinstance(value, list):
                        for a in value:
                            if a not in entry.artefakty:
                                entry.artefakty.append(a)
                    else:
                        setattr(entry, key, value)
            return entry
    return None


def add_entry(envelope: Envelope, entry_data: dict[str, Any]) -> RTMEntry:
    """Dodaje nowy wpis RTM do koperty. Rzuca ValueError przy duplikacie req_id."""
    existing_ids = {e.req_id for e in envelope.rtm}
    req_id = entry_data.get("req_id", "")
    if not req_id:
        raise ValueError("req_id jest wymagany")
    if req_id in existing_ids:
        raise ValueError(f"Wpis RTM o req_id='{req_id}' juz istnieje")

    entry = RTMEntry(**entry_data)
    envelope.rtm.append(entry)
    return entry
