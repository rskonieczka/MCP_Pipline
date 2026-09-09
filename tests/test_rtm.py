"""Testy Requirements Traceability Matrix (RTM) - sledzenie wymagan przez pipeline.

Zakres:
- Ekstrakcja wymagan po stacji zmienne
- Auto-aktualizacja statusow po realizuj/weryfikacja/sprawdzenie
- Narzedzia MCP: get_rtm, add_rtm_entry, update_rtm, validate_rtm_coverage
- Kompatybilnosc wsteczna (brak pola rtm w starych checkpointach)
- Integracja z update_envelope (sekcja rtm)
"""
from __future__ import annotations

from pipeline_mcp import server
from pipeline_mcp.models import Envelope, RTMEntry
from pipeline_mcp.rtm import (
    extract_requirements_from_zmienne,
    auto_update_rtm,
    validate_coverage,
    update_entry,
    add_entry,
)
from pipeline_mcp.envelope import create_envelope, get_envelope_summary
from pipeline_mcp.memgraph import _label_for_id


# --- Helper: wyjscie stacji zmienne z wymaganiami ---


def _zmienne_output_with_requirements() -> dict:
    return {
        "variables": [
            {"name": "REQ-001", "type": "requirement", "value": "System musi obslugiwac RTM"},
            {"name": "REQ-002", "type": "requirement", "value": "RTM integruje sie z Memgraph"},
            {"name": "FACT-001", "type": "fact", "value": "Istnieje 13 stacji"},
            {"name": "REQ-003", "type": "requirement", "value": "Walidacja pokrycia wymagan"},
        ],
        "relations": [],
        "sources_used": [],
        "missing_data_resolution": {},
        "analysis_object": {"name": "Pipeline MCP Server"},
    }


def _inicjuj_output() -> dict:
    return {"klasyfikacja": "rutynowe", "punkt_wejscia": "zmienne",
            "uzasadnienie": "test", "ryzyka": []}


def _realizuj_output() -> dict:
    return {
        "kroki_wykonane": ["REQ-001 zaimplementowane", "REQ-002 dodane"],
        "kroki_pominiete": [],
        "kroki_zablokowane": [],
        "zmiany": ["zm1", "zm2"],
        "status": "zakonczony",
    }


def _weryfikacja_output() -> dict:
    return {
        "werdykty": [
            {"status": "potwierdzony", "twierdzenie": "REQ-001 dziala poprawnie",
             "uzasadnienie": "test passed"},
            {"status": "obalony", "twierdzenie": "REQ-002 nie dziala",
             "uzasadnienie": "test failed"},
        ],
        "konflikty_zrodel": [],
        "braki_dowodowe": [],
        "podsumowanie": "1 potwierdzony, 1 obalony",
    }


def _sprawdzenie_output_niezgodny() -> dict:
    return {
        "status_audytu": "niezgodny",
        "ocena_calkowita": 60,
        "werdykt": "Niezgodny",
        "wymiary": {"Zgodnosc": "niezgodny", "Kompletnosc": "zgodny"},
        "poprawiona_odpowiedz": "Poprawka",
    }


# --- 1. Model RTMEntry ---


def test_rtm_entry_default(isolated_runs):
    entry = RTMEntry(req_id="REQ-001", opis="Test")
    assert entry.req_id == "REQ-001"
    assert entry.status == "nieadresowane"
    assert entry.stacje_adresujace == []
    assert entry.artefakty == []
    assert entry.stacja_weryfikujaca == ""
    assert entry.zrodlo == "zamiar"


def test_envelope_rtm_default_empty(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    assert env.rtm == []


# --- 2. Ekstrakcja wymagan ---


def test_extract_requirements_filters_only_requirement_type(isolated_runs):
    output = _zmienne_output_with_requirements()
    entries = extract_requirements_from_zmienne(output)
    assert len(entries) == 3
    req_ids = {e.req_id for e in entries}
    assert req_ids == {"REQ-001", "REQ-002", "REQ-003"}
    assert all(e.opis != "" for e in entries)
    assert all(e.zrodlo == "zmienne" for e in entries)


def test_extract_requirements_empty_variables(isolated_runs):
    entries = extract_requirements_from_zmienne({"variables": []})
    assert entries == []


def test_extract_requirements_no_variables_key(isolated_runs):
    entries = extract_requirements_from_zmienne({})
    assert entries == []


def test_extract_requirements_non_list_variables(isolated_runs):
    entries = extract_requirements_from_zmienne({"variables": "not a list"})
    assert entries == []


def test_extract_requirements_fallback_id(isolated_runs):
    """Brak id/name -> auto-generowany REQ-NNN."""
    output = {
        "variables": [
            {"type": "requirement", "value": "Anonimowe wymaganie"},
        ]
    }
    entries = extract_requirements_from_zmienne(output)
    assert len(entries) == 1
    assert entries[0].req_id == "REQ-001"


# --- 3. Auto-aktualizacja RTM ---


def test_auto_update_after_zmienne_creates_entries(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    assert len(env.rtm) == 3
    assert all(e.status == "adresowane" for e in env.rtm)
    assert all("zmienne" in e.stacje_adresujace for e in env.rtm)


def test_auto_update_after_zmienne_deduplikacja(isolated_runs):
    """Ponowne wywolanie zmienne nie duplikuje wpisow RTM."""
    env = create_envelope("test", "zamiar", "pelny")
    output = _zmienne_output_with_requirements()
    auto_update_rtm(env, "zmienne", output)
    auto_update_rtm(env, "zmienne", output)
    assert len(env.rtm) == 3


def test_auto_update_after_realizuj_marks_zrealizowane(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    auto_update_rtm(env, "realizuj", _realizuj_output())
    # REQ-001 i REQ-002 sa w kroki_wykonane
    req1 = [e for e in env.rtm if e.req_id == "REQ-001"][0]
    req2 = [e for e in env.rtm if e.req_id == "REQ-002"][0]
    req3 = [e for e in env.rtm if e.req_id == "REQ-003"][0]
    assert req1.status == "zrealizowane"
    assert req2.status == "zrealizowane"
    assert req3.status == "adresowane"  # nie bylo w krokach
    assert "realizuj" in req1.stacje_adresujace
    assert "realizuj" in req2.stacje_adresujace


def test_auto_update_after_weryfikacja_marks_weryfikowane_i_niespelnione(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    auto_update_rtm(env, "realizuj", _realizuj_output())
    auto_update_rtm(env, "weryfikacja", _weryfikacja_output())
    req1 = [e for e in env.rtm if e.req_id == "REQ-001"][0]
    req2 = [e for e in env.rtm if e.req_id == "REQ-002"][0]
    assert req1.status == "weryfikowane"
    assert req1.stacja_weryfikujaca == "weryfikacja"
    assert req2.status == "niespelnione"


def test_auto_update_after_sprawdzenie_niezgodny_downgrades(isolated_runs):
    """Wymiar Zgodnosc=niezgodny -> weryfikowane staja sie niespelnione."""
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    auto_update_rtm(env, "realizuj", _realizuj_output())
    auto_update_rtm(env, "weryfikacja", _weryfikacja_output())
    # Reset REQ-001 na weryfikowane (bylo potwierdzone)
    req1 = [e for e in env.rtm if e.req_id == "REQ-001"][0]
    req1.status = "weryfikowane"
    auto_update_rtm(env, "sprawdzenie", _sprawdzenie_output_niezgodny())
    assert req1.status == "niespelnione"
    # U6: stacja_weryfikujaca zachowana, stacja_niespelnienia ustawiona
    assert req1.stacja_weryfikujaca == "weryfikacja"
    assert req1.stacja_niespelnienia == "sprawdzenie"


def test_auto_update_after_sprawdzenie_zgodny_no_change(isolated_runs):
    """Wymiar Zgodnosc=zgodny -> brak zmian."""
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    auto_update_rtm(env, "realizuj", _realizuj_output())
    req1 = [e for e in env.rtm if e.req_id == "REQ-001"][0]
    status_before = req1.status
    auto_update_rtm(env, "sprawdzenie", {
        "status_audytu": "zgodny",
        "wymiary": {"Zgodnosc": "zgodny"},
    })
    assert req1.status == status_before


def test_auto_update_other_stations_no_op(isolated_runs):
    """Stacje nie-RTM (inicjuj, analiza, dobierz, planuj, utrwal) nie modyfikuja RTM."""
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    count_before = len(env.rtm)
    auto_update_rtm(env, "analiza", {"wnioski": "test"})
    auto_update_rtm(env, "dobierz", {"rekomendacja": "test"})
    auto_update_rtm(env, "planuj", {"kroki": ["k1"]})
    assert len(env.rtm) == count_before


# --- 4. Walidacja pokrycia ---


def test_validate_coverage_empty_rtm(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    coverage = validate_coverage(env)
    assert coverage["total"] == 0
    assert coverage["status"] == "brak_wymagan"
    assert coverage["pokrycie_procent"] == 100.0


def test_validate_coverage_full_pipeline(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    auto_update_rtm(env, "realizuj", _realizuj_output())
    auto_update_rtm(env, "weryfikacja", _weryfikacja_output())
    coverage = validate_coverage(env)
    assert coverage["total"] == 3
    assert coverage["weryfikowane"] == 1
    assert coverage["niespelnione"] == 1
    assert coverage["adresowane"] == 1  # REQ-003 nie zrealizowane
    assert coverage["status"] == "niekompletne"
    assert "REQ-002" in coverage["niespelnione_ids"]


def test_validate_coverage_all_met(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    # Wszystkie jako weryfikowane
    for entry in env.rtm:
        entry.status = "weryfikowane"
    coverage = validate_coverage(env)
    assert coverage["status"] == "kompletne"
    assert coverage["pokrycie_procent"] == 100.0


# --- 5. Narzedzia MCP: get_rtm, add_rtm_entry, update_rtm, validate_rtm_coverage ---


def _run_with_rtm() -> str:
    """Tworzy run i wykonuje inicjuj + zmienne z wymaganiami."""
    run_id = server.start_run(zamiar="Test RTM funkcjonalny")["run_id"]
    server.execute_station(run_id, "inicjuj", _inicjuj_output())
    server.execute_station(
        run_id, "zmienne", _zmienne_output_with_requirements(),
        skip_validation=True,
    )
    return run_id


def test_get_rtm_after_zmienne(isolated_runs):
    run_id = _run_with_rtm()
    result = server.get_rtm(run_id)
    assert result["run_id"] == run_id
    assert len(result["rtm"]) == 3
    assert all(e["status"] == "adresowane" for e in result["rtm"])
    assert "coverage" in result
    assert result["coverage"]["total"] == 3


def test_get_rtm_empty_for_new_run(isolated_runs):
    run_id = server.start_run(zamiar="Pusty run")["run_id"]
    result = server.get_rtm(run_id)
    assert result["rtm"] == []
    assert result["coverage"]["status"] == "brak_wymagan"


def test_add_rtm_entry_manual(isolated_runs):
    run_id = _run_with_rtm()
    result = server.add_rtm_entry(
        run_id, "REQ-999", "Manualnie dodane wymaganie",
        zrodlo="agent_inference", stacje_adresujace=["analiza"],
    )
    assert result["entry"]["req_id"] == "REQ-999"
    assert result["entry"]["zrodlo"] == "agent_inference"
    assert result["entry"]["stacje_adresujace"] == ["analiza"]
    assert result["coverage"]["total"] == 4

    # Wpis widoczny w get_rtm (checkpoint nadpisany)
    rtm = server.get_rtm(run_id)
    assert any(e["req_id"] == "REQ-999" for e in rtm["rtm"])
    assert len(rtm["rtm"]) == 4


def test_add_rtm_entry_duplicate_rejected(isolated_runs):
    run_id = _run_with_rtm()
    try:
        server.add_rtm_entry(run_id, "REQ-001", "Duplikat")
        assert False, "Should raise"
    except Exception as e:
        assert "istnieje" in str(e).lower() or "juz" in str(e).lower()


def test_update_rtm_status(isolated_runs):
    run_id = _run_with_rtm()
    result = server.update_rtm(run_id, "REQ-001", {"status": "zrealizowane"})
    assert result["entry"]["status"] == "zrealizowane"

    # Widoczne w get_rtm
    rtm = server.get_rtm(run_id)
    req1 = [e for e in rtm["rtm"] if e["req_id"] == "REQ-001"][0]
    assert req1["status"] == "zrealizowane"


def test_update_rtm_add_stacje_adresujace(isolated_runs):
    run_id = _run_with_rtm()
    result = server.update_rtm(
        run_id, "REQ-001", {"stacje_adresujace": ["realizuj", "weryfikacja"]}
    )
    assert "realizuj" in result["entry"]["stacje_adresujace"]
    assert "weryfikacja" in result["entry"]["stacje_adresujace"]
    assert "zmienne" in result["entry"]["stacje_adresujace"]  # oryginalne


def test_update_rtm_add_artefakty(isolated_runs):
    run_id = _run_with_rtm()
    result = server.update_rtm(
        run_id, "REQ-001", {"artefakty": ["pola_stacji.realizuj.zmiany"]}
    )
    assert "pola_stacji.realizuj.zmiany" in result["entry"]["artefakty"]


def test_update_rtm_nonexistent_raises(isolated_runs):
    run_id = _run_with_rtm()
    try:
        server.update_rtm(run_id, "REQ-NONEXIST", {"status": "zrealizowane"})
        assert False, "Should raise"
    except Exception as e:
        assert "nie istnieje" in str(e).lower()


def test_validate_rtm_coverage_tool(isolated_runs):
    run_id = _run_with_rtm()
    result = server.validate_rtm_coverage(run_id)
    assert result["run_id"] == run_id
    assert result["coverage"]["total"] == 3
    assert result["coverage"]["status"] == "w_trakcie"
    assert result["coverage"]["adresowane"] == 3


# --- 6. Auto-aktualizacja przez execute_station (E2E) ---


def test_execute_station_auto_updates_rtm_realizuj(isolated_runs):
    run_id = _run_with_rtm()
    server.execute_station(
        run_id, "realizuj", _realizuj_output(), skip_validation=True
    )
    rtm = server.get_rtm(run_id)
    req1 = [e for e in rtm["rtm"] if e["req_id"] == "REQ-001"][0]
    assert req1["status"] == "zrealizowane"
    assert "realizuj" in req1["stacje_adresujace"]


def test_execute_station_auto_updates_rtm_weryfikacja(isolated_runs):
    run_id = _run_with_rtm()
    server.execute_station(run_id, "realizuj", _realizuj_output(),
                           skip_validation=True)
    server.execute_station(run_id, "weryfikacja", _weryfikacja_output(),
                           skip_validation=True)
    rtm = server.get_rtm(run_id)
    req1 = [e for e in rtm["rtm"] if e["req_id"] == "REQ-001"][0]
    req2 = [e for e in rtm["rtm"] if e["req_id"] == "REQ-002"][0]
    assert req1["status"] == "weryfikowane"
    assert req2["status"] == "niespelnione"


def test_execute_station_auto_updates_rtm_sprawdzenie(isolated_runs):
    run_id = _run_with_rtm()
    server.execute_station(run_id, "realizuj", _realizuj_output(),
                           skip_validation=True)
    server.execute_station(run_id, "weryfikacja", _weryfikacja_output(),
                           skip_validation=True)
    server.execute_station(run_id, "sprawdzenie",
                           _sprawdzenie_output_niezgodny(),
                           skip_validation=True)
    rtm = server.get_rtm(run_id)
    req1 = [e for e in rtm["rtm"] if e["req_id"] == "REQ-001"][0]
    # REQ-001 bylo weryfikowane -> sprawdzenie z Zgodnosc=niezgodny -> niespelnione
    assert req1["status"] == "niespelnione"
    # U6: stacja_weryfikujaca zachowana, stacja_niespelnienia ustawiona
    assert req1["stacja_weryfikujaca"] == "weryfikacja"
    assert req1["stacja_niespelnienia"] == "sprawdzenie"


def test_envelope_summary_includes_rtm_count(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    summary = get_envelope_summary(env)
    assert summary["rtm_count"] == 3


# --- 7. update_envelope z sekcja rtm ---


def test_update_envelope_rtm_section_merge(isolated_runs):
    run_id = _run_with_rtm()
    server.update_envelope(
        run_id, "rtm",
        {"rtm": [{"req_id": "REQ-MAN", "opis": "Manual przez envelope"}]},
        merge=True,
    )
    rtm = server.get_rtm(run_id)
    ids = {e["req_id"] for e in rtm["rtm"]}
    assert "REQ-MAN" in ids
    assert "REQ-001" in ids  # oryginalne zachowane


def test_update_envelope_rtm_section_replace(isolated_runs):
    run_id = _run_with_rtm()
    server.update_envelope(
        run_id, "rtm",
        {"rtm": [{"req_id": "REQ-ONLY", "opis": "Zastapione"}]},
        merge=False,
    )
    rtm = server.get_rtm(run_id)
    assert len(rtm["rtm"]) == 1
    assert rtm["rtm"][0]["req_id"] == "REQ-ONLY"


# --- 8. Kompatybilnosc wsteczna ---


def test_old_checkpoint_without_rtm_loads(isolated_runs):
    """Stare checkpointy bez pola rtm laduja poprawnie z rtm=[] (default)."""
    import yaml
    old_data = {
        "run_id": "old-run",
        "sciezka": "pelny",
        "stacja_aktualna": "inicjuj",
        "stacja_poprzednia": None,
        "stan": {"zamiar": "stary", "klasyfikacja": "rutynowe", "punkt_wejscia": "zmienne"},
        "pola_stacji": {"inicjuj": {"klasyfikacja": "rutynowe"}},
        "walidacja": {"stacja_docelowa": "zmienne", "status": "gotowy"},
        "relacje": [],
        "timestamp": "2026-01-01T00:00:00",
    }
    env = Envelope(**old_data)
    assert env.rtm == []


# --- 9. Memgraph label ---


def test_memgraph_label_wymaganie():
    assert _label_for_id("wymaganie:run1:REQ-001") == "Wymaganie"


def test_memgraph_label_unknown_prefix():
    assert _label_for_id("unknown:xxx") == ""


# --- 10. update_entry i add_entry (bezposrednio) ---


def test_update_entry_direct(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    add_entry(env, {"req_id": "R1", "opis": "test"})
    updated = update_entry(env, "R1", {"status": "zrealizowane"})
    assert updated is not None
    assert updated.status == "zrealizowane"


def test_update_entry_nonexistent_returns_none(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    result = update_entry(env, "NONEXIST", {"status": "zrealizowane"})
    assert result is None


def test_add_entry_requires_req_id(isolated_runs):
    env = create_envelope("test", "zamiar", "pelny")
    try:
        add_entry(env, {"opis": "brak req_id"})
        assert False, "Should raise"
    except ValueError:
        pass


# --- 11. U1: RTM false-positive przy pustym opisie ---


def test_u1_empty_opis_not_false_positive_realizuj(isolated_runs):
    """U1: wymaganie z pustym opisem nie moze byc false-positive dopasowane
    w _update_after_realizuj (pusty string 'in' dowolny tekst = True)."""
    env = create_envelope("test", "zamiar", "pelny")
    # Dodaj wymaganie z pustym opisem
    auto_update_rtm(env, "zmienne", {
        "variables": [{"id": "REQ-EMPTY", "type": "requirement", "value": ""}],
    })
    req = [e for e in env.rtm if e.req_id == "REQ-EMPTY"][0]
    assert req.opis == ""
    assert req.status == "adresowane"
    # Wykonaj realizuj - wymaganie z pustym opisem nie powinno byc zrealizowane
    auto_update_rtm(env, "realizuj", {"kroki_wykonane": ["naprawiono bug w auth"]})
    assert req.status == "adresowane"  # nie zrealizowane - pusty opis nie dopasowany


def test_u1_empty_opis_not_false_positive_weryfikacja(isolated_runs):
    """U1: wymaganie z pustym opisem nie moze byc false-positive dopasowane
    w _update_after_weryfikacja."""
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", {
        "variables": [{"id": "REQ-EMPTY2", "type": "requirement", "value": ""}],
    })
    req = [e for e in env.rtm if e.req_id == "REQ-EMPTY2"][0]
    assert req.opis == ""
    # Wykonaj weryfikacje - pusty opis nie powinien dopasowac
    auto_update_rtm(env, "weryfikacja", {
        "werdykty": [{"status": "potwierdzony", "twierdzenie": "wszystko dziala"}],
    })
    assert req.stacja_weryfikujaca == ""  # nie dopasowane


# --- 12. U6: stacja_niespelnienia nie nadpisuje stacja_weryfikujaca ---


def test_u6_stacja_niespelnienia_preserves_weryfikujaca(isolated_runs):
    """U6: _update_after_sprawdzenie ustawia stacja_niespelnienia,
    nie nadpisuje stacja_weryfikujaca."""
    env = create_envelope("test", "zamiar", "pelny")
    auto_update_rtm(env, "zmienne", _zmienne_output_with_requirements())
    auto_update_rtm(env, "realizuj", _realizuj_output())
    auto_update_rtm(env, "weryfikacja", _weryfikacja_output())
    req1 = [e for e in env.rtm if e.req_id == "REQ-001"][0]
    assert req1.stacja_weryfikujaca == "weryfikacja"
    assert req1.status == "weryfikowane"
    # Reset na weryfikowane (bylo potwierdzone -> weryfikowane)
    req1.status = "weryfikowane"
    auto_update_rtm(env, "sprawdzenie", _sprawdzenie_output_niezgodny())
    assert req1.status == "niespelnione"
    assert req1.stacja_weryfikujaca == "weryfikacja"  # zachowane
    assert req1.stacja_niespelnienia == "sprawdzenie"  # nowe pole
