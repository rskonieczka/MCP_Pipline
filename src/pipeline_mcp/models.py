"""Modele Pydantic dla struktur danych pipeline'u."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Typy wyliczeniowe ---

Sciezka = Literal["szybki", "pelny", "doglebny"]
Klasyfikacja = Literal["trywialne", "rutynowe", "zlozone"]
StationStatus = Literal["zakonczona", "w_trakcie", "zablokowana", "pominieta"]
RunStatus = Literal["w_trakcie", "zakonczony", "zablokowany"]
GateDecision = Literal["przejdz", "powrot", "eskalacja"]
ValidationStatus = Literal["gotowy", "wnioskowane", "niekompletne"]
SourceType = Literal[
    "user_provided", "verified_source", "agent_inference", "hypothesis", "unavailable"
]
ClientStatus = Literal["aktywny", "zarchiwizowany"]


# --- Podstawowe struktury ---


class Relacja(BaseModel):
    """Relacja miedzy encjami w run'ie (zapisywana do Memgraph)."""

    zrodlo: str
    cel: str
    typ: str
    pola: list[str] = Field(default_factory=list)


class Walidacja(BaseModel):
    """Walidacja kompletnosci przed przejsciem do stacji nastepnej."""

    stacja_docelowa: str = ""
    pola_wymagane: list[str] = Field(default_factory=list)
    pola_obecne: list[str] = Field(default_factory=list)
    pola_brakujace: list[str] = Field(default_factory=list)
    status: ValidationStatus = "gotowy"
    akcja_naprawcza: str = ""


class Stan(BaseModel):
    """Skumulowane pola kluczowe z wszystkich poprzednich stacji."""

    zamiar: str = ""
    klasyfikacja: str = ""
    punkt_wejscia: str = ""
    client_id: str = ""


RTMStatus = Literal[
    "nieadresowane", "adresowane", "zrealizowane", "weryfikowane", "niespelnione"
]


class RTMEntry(BaseModel):
    """Wpis Requirements Traceability Matrix - sledzenie wymagania przez pipeline."""

    req_id: str
    opis: str = ""
    zrodlo: str = "zamiar"
    stacje_adresujace: list[str] = Field(default_factory=list)
    stacja_weryfikujaca: str = ""
    # U6: stacja, ktora oznaczyla wymaganie jako niespelnione (nie nadpisuje
    # stacja_weryfikujaca, aby zachowac informacje o pierwotnej weryfikacji)
    stacja_niespelnienia: str = ""
    status: RTMStatus = "nieadresowane"  # type: ignore
    artefakty: list[str] = Field(default_factory=list)
    checkpoint_weryfikacji: str = ""


class Envelope(BaseModel):
    """Koperta - jedyny formalny noznik danych miedzy stacjami."""

    run_id: str
    sciezka: Sciezka = "pelny"
    stacja_aktualna: str = ""
    stacja_poprzednia: str | None = None
    stan: Stan = Field(default_factory=Stan)
    pola_stacji: dict[str, dict[str, Any]] = Field(default_factory=dict)
    walidacja: Walidacja = Field(default_factory=Walidacja)
    relacje: list[Relacja] = Field(default_factory=list)
    rtm: list[RTMEntry] = Field(default_factory=list)
    # U8: wejscie uzytkownika z start_run (kontekst, zrodla, tryb_inicjacji) -
    # nie w pola_stacji, bo _wejscie nie jest nazwa stacji
    wejscie: dict[str, Any] = Field(default_factory=dict)
    # MT: identyfikator klienta dla izolacji wieloklientowej (pusty = tryb legacy)
    client_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Manifest ---


class StacjaManifest(BaseModel):
    """Wpis stacji w manifeście."""

    stacja: str
    status: StationStatus = "w_trakcie"
    timestamp: str | None = None
    checkpoint: str | None = None


class GateHistoryEntry(BaseModel):
    """Wpis historii iteracji bramki (U4)."""

    iteracja: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    audit_status: str = ""
    loop_target: str = ""
    gate_decision: str = ""


class Manifest(BaseModel):
    """Manifest run'u - indeks stacji, statusy, sciezka, iteracja bramki."""

    run_id: str
    zamiar: str = ""
    sciezka: Sciezka = "pelny"
    iteracja_bramki: int = 0
    status_runu: RunStatus = "w_trakcie"
    timestamp_start: str = Field(default_factory=lambda: datetime.now().isoformat())
    timestamp_end: str | None = None
    stacje: list[StacjaManifest] = Field(default_factory=list)
    # U4: historia iteracji bramki (pusta przy starcie, aktualizowana przez evaluate_gate)
    historia_bramki: list[GateHistoryEntry] = Field(default_factory=list)
    # MT: identyfikator klienta dla izolacji wieloklientowej (pusty = tryb legacy)
    client_id: str = ""


# --- Wyniki narzedzi ---


class QualityGateResult(BaseModel):
    run_id: str
    gate_decision: GateDecision
    iteracja_bramki: int
    next_station: str | None = None
    loop_target: str | None = None
    max_iteracje: int = 2
    komunikat: str = ""


class ContractValidationResult(BaseModel):
    stacja_docelowa: str
    pola_wymagane: list[str]
    pola_obecne: list[str]
    pola_brakujace: list[str]
    pola_wnioskowane: list[str]
    status: ValidationStatus
    akcja_naprawcza: str


class AutoPilotStatus(BaseModel):
    run_id: str
    status: Literal["uruchomiony", "zakonczony", "zatrzymany", "zablokowany"]
    stacja_aktualna: str
    stacje_wykonane: list[str]
    stacje_pozostale: list[str]
    iteracja_bramki: int
    bledy: list[str]


# --- Klient (multi-tenant) ---


class ClientContext(BaseModel):
    """Kontekst zarejestrowanego klienta w systemie wieloklientowym."""

    client_id: str
    display_name: str
    status: ClientStatus = "aktywny"
    registered: str = Field(default_factory=lambda: datetime.now().isoformat())
    aliases: list[str] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)
    id_fragments: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClientMatch(BaseModel):
    """Pojedyncze dopasowanie klienta z algorytmu resolve_client."""

    client_id: str
    display_name: str
    confidence: int  # 0-100
    matched_on: str  # "client_id", "external_id:nip", "alias", "id_fragment", "fuzzy_name"


class ResolveResult(BaseModel):
    """Wynik rozpoznawania klienta z niejednoznacznego identyfikatora."""

    query: str
    normalized: str
    matches: list[ClientMatch] = Field(default_factory=list)
    auto_resolved: bool = False
    needs_confirmation: bool = False
    suggested_action: str = ""


class ClientMemoryEntry(BaseModel):
    """Wpis pamieci AI per-klient."""

    memory_id: str
    topic: str
    content: str
    scope: Literal["client", "shared"] = "client"
    client_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = Field(default_factory=list)


class SharedKnowledgeEntry(BaseModel):
    """Wpis wiedzy wspoldzielonej (cross-client)."""

    knowledge_id: str
    category: Literal["decision", "pattern", "pitfall"]
    title: str
    content: str
    source: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = Field(default_factory=list)


# --- Wyjatki ---


class PipelineError(Exception):
    """Bazowy wyjatek pipeline'u."""

    code: str = "PIPELINE_ERROR"


class RunNotFoundError(PipelineError):
    code = "RUN_NOT_FOUND"


class StationNotFoundError(PipelineError):
    code = "STATION_NOT_FOUND"


class StationAlreadyDoneError(PipelineError):
    code = "STATION_ALREADY_DONE"


class ContractIncompleteError(PipelineError):
    code = "CONTRACT_INCOMPLETE"


class GateMaxIterationsError(PipelineError):
    code = "GATE_MAX_ITERATIONS"


class CheckpointNotFoundError(PipelineError):
    code = "CHECKPOINT_NOT_FOUND"


class MemgraphUnavailableError(PipelineError):
    code = "MEMGRAPH_UNAVAILABLE"


class LLMNotConfiguredError(PipelineError):
    code = "LLM_NOT_CONFIGURED"


class InvalidPathError(PipelineError):
    code = "INVALID_PATH"


class RunClosedError(PipelineError):
    code = "RUN_CLOSED"


class SkillNotFoundError(PipelineError):
    code = "SKILL_NOT_FOUND"


class LLMOutputParseError(PipelineError):
    code = "LLM_OUTPUT_PARSE_ERROR"


class ClientNotFoundError(PipelineError):
    code = "CLIENT_NOT_FOUND"


class ClientAlreadyExistsError(PipelineError):
    code = "CLIENT_ALREADY_EXISTS"


class AmbiguousClientError(PipelineError):
    code = "AMBIGUOUS_CLIENT"


class ClientIdMismatchError(PipelineError):
    code = "CLIENT_ID_MISMATCH"


class InvalidClientIdError(PipelineError):
    code = "INVALID_CLIENT_ID"
