"""Testy krytycznych sciezek pipeline'u: run_id, petla bramki, eskalacja."""
from __future__ import annotations

from pathlib import Path

from pipeline_mcp import server
from pipeline_mcp.manifest import load_manifest
from pipeline_mcp.routing import get_post_gate_station


def _output_for(station: str) -> dict:
    """Minimalne wyjscie kontraktowe stacji."""
    outputs = {
        "inicjuj": {"klasyfikacja": "rutynowe", "punkt_wejscia": "x",
                    "uzasadnienie": "u", "ryzyka": []},
        "zmienne": {"variables": ["v"], "analysis_object": {"name": "obiekt"}},
        "analiza": {"wnioski": "w", "ograniczenia": "o", "raport_streszczenie": "r"},
        "dobierz": {"rekomendacja": "r", "porownanie": "p"},
        "planuj": {"kroki": ["k1"], "zasoby": ["z"]},
        "realizuj": {"zmiany": ["z1"], "status": "ok"},
        "weryfikacja": {"werdykty": ["ok"]},
        "sprawdzenie": {"status_audytu": "zgodny", "werdykt": "ok"},
        "utrwal": {"typ_wiedzy": "t", "status": "ok"},
    }
    return outputs.get(station, {"status": "ok"})


def _run_until_sprawdzenie(zamiar: str) -> str:
    """Przechodzi sciezke pelna do stacji sprawdzenie wlacznie."""
    run_id = server.start_run(zamiar=zamiar)["run_id"]
    for st in ["inicjuj", "zmienne", "analiza", "dobierz", "planuj",
               "realizuj", "weryfikacja", "sprawdzenie"]:
        server.execute_station(run_id, st, _output_for(st))
    return run_id


# --- run_id ---


def test_run_id_sanityzacja_separatorow(isolated_runs):
    result = server.start_run(zamiar="fix /etc/passwd bug")
    assert "/" not in result["run_id"]
    assert Path(result["manifest_path"]).parent.parent == isolated_runs


def test_run_id_fallback_dla_interpunkcji(isolated_runs):
    result = server.start_run(zamiar=". , ?")
    assert result["run_id"].endswith("-run")


def test_run_id_unikalnosc_bez_nadpisania(isolated_runs):
    r1 = server.start_run(zamiar="analiza projektu alpha")
    server.execute_station(r1["run_id"], "inicjuj", _output_for("inicjuj"))
    r2 = server.start_run(zamiar="analiza projektu alpha")
    assert r1["run_id"] != r2["run_id"]
    m1 = load_manifest(Path(r1["manifest_path"]))
    assert any(s.stacja == "inicjuj" and s.status == "zakonczona" for s in m1.stacje)


# --- petla bramki ---


def test_petla_bramki_ponowne_wykonanie(isolated_runs):
    run_id = _run_until_sprawdzenie("test petli bramki")
    gate = server.quality_gate(run_id, "niezgodny", {}, "dobierz")
    assert gate["gate_decision"] == "powrot"
    assert gate["next_station"] == "dobierz"

    # Po powrocie stacje petli sa resetowane - ponowne wykonanie bez bledu
    result = server.execute_station(run_id, "dobierz", _output_for("dobierz"))
    assert result["status"] == "zakonczona"
    assert result["next_station"] == "planuj"
    # Checkpoint iteracji nie nadpisuje oryginalu
    assert result["checkpoint_path"].endswith("_iter1.yaml")

    # get_next_station podaza za petla
    nx = server.get_next_station(run_id)
    assert nx["next_station"] == "planuj"


def test_eskalacja_blokuje_run(isolated_runs):
    run_id = _run_until_sprawdzenie("test eskalacji bramki")
    for i in (1, 2):
        gate = server.quality_gate(run_id, "niezgodny", {}, "dobierz")
        assert gate["gate_decision"] == "powrot"
        server.execute_station(run_id, "dobierz", _output_for("dobierz"))
        server.execute_station(run_id, "planuj", _output_for("planuj"))
        server.execute_station(run_id, "realizuj", _output_for("realizuj"))
        server.execute_station(run_id, "weryfikacja", _output_for("weryfikacja"))
        server.execute_station(run_id, "sprawdzenie", _output_for("sprawdzenie"))

    gate = server.quality_gate(run_id, "niezgodny", {})
    assert gate["gate_decision"] == "eskalacja"
    status = server.get_run_status(run_id)
    assert status["status_runu"] == "zablokowany"


def test_bramka_zgodna_pelny_przechodzi_do_utrwal(isolated_runs):
    run_id = _run_until_sprawdzenie("test bramki zgodnej")
    gate = server.quality_gate(run_id, "zgodny")
    assert gate["gate_decision"] == "przejdz"
    assert gate["next_station"] == "utrwal"


def test_post_gate_szybka_konczy_sciezke(isolated_runs):
    assert get_post_gate_station("szybki") is None
    run_id = server.start_run(zamiar="zadanie trywialne test")["run_id"]
    server.execute_station(run_id, "inicjuj", {"klasyfikacja": "trywialne"})
    for st in ["zmienne", "analiza", "dobierz", "sprawdzenie"]:
        server.execute_station(run_id, st, _output_for(st))
    gate = server.quality_gate(run_id, "zgodny")
    assert gate["gate_decision"] == "przejdz"
    assert gate["next_station"] is None


def test_petla_bramki_szybka_wraca_do_dobierz(isolated_runs):
    run_id = server.start_run(zamiar="szybka petla test")["run_id"]
    server.execute_station(run_id, "inicjuj", {"klasyfikacja": "trywialne"})
    for st in ["zmienne", "analiza", "dobierz", "sprawdzenie"]:
        server.execute_station(run_id, st, _output_for(st))
    # infer_loop_target nie moze zwrocic 'planuj' (brak w sciezce szybkiej)
    gate = server.quality_gate(run_id, "niezgodny", {"Kompletnosc": "niezgodny"})
    assert gate["next_station"] == "dobierz"


# --- start_run wejscie / close_run ---


def test_start_run_zapisuje_kontekst(isolated_runs):
    r = server.start_run(zamiar="zadanie z kontekstem", kontekst="wazny kontekst",
                         zrodla=["doc.md"])
    env = server.get_envelope(r["run_id"])
    assert env["pola_stacji"]["_wejscie"]["kontekst"] == "wazny kontekst"
    assert env["pola_stacji"]["_wejscie"]["zrodla"] == ["doc.md"]
    # Wejscie przezywa wykonanie stacji inicjuj
    server.execute_station(r["run_id"], "inicjuj", _output_for("inicjuj"))
    env2 = server.get_envelope(r["run_id"])
    assert env2["pola_stacji"]["_wejscie"]["kontekst"] == "wazny kontekst"


def test_close_run_idempotentny(isolated_runs):
    run_id = server.start_run(zamiar="test zamykania")["run_id"]
    server.execute_station(run_id, "inicjuj", _output_for("inicjuj"))
    first = server.close_run(run_id)
    assert first["status"] == "zakonczony"
    m1 = load_manifest(isolated_runs / run_id / "manifest.yaml")
    second = server.close_run(run_id)
    assert second.get("already_closed") is True
    m2 = load_manifest(isolated_runs / run_id / "manifest.yaml")
    assert m1.timestamp_end == m2.timestamp_end
