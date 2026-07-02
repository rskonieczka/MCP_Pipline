"""Testy synchronicznej petli auto-pilota z fake providerem LLM."""
from __future__ import annotations

import re

import pytest

from pipeline_mcp import auto_pilot, server


class _FakeProvider:
    """Fake LLM: odczytuje stacje z prompta i zwraca poprawny blok KOPERTA."""

    def __init__(self, klasyfikacja: str = "trywialne"):
        self.klasyfikacja = klasyfikacja
        self.calls: list[str] = []

    def complete(self, prompt: str, system: str = "") -> str:
        match = re.search(r"WYKONAJ STACJE '(\w+)'", prompt)
        station = match.group(1) if match else "inicjuj"
        self.calls.append(station)
        pola: dict[str, str] = {
            "inicjuj": f"klasyfikacja: {self.klasyfikacja}\n      punkt_wejscia: x",
            "sprawdzenie": "status_audytu: zgodny\n      werdykt: ok",
        }
        pola_yaml = pola.get(station, "status: ok")
        return (
            "Wynik pracy stacji.\n\n"
            "KOPERTA:\n"
            "  pola_stacji:\n"
            f"    {station}:\n"
            f"      {pola_yaml}\n"
        )


@pytest.fixture()
def fake_llm(monkeypatch):
    provider = _FakeProvider()
    monkeypatch.setattr(auto_pilot, "get_provider", lambda: provider)
    monkeypatch.setattr(auto_pilot, "is_configured", lambda: True)
    return provider


def test_auto_pilot_wykonuje_sciezke_szybka(isolated_runs, fake_llm):
    run_id = server.start_run(zamiar="auto pilot test")["run_id"]
    result = server.auto_pilot_start(run_id)

    assert result["status"] == "zakonczony"
    assert result["stacje_wykonane"] == [
        "inicjuj", "zmienne", "analiza", "dobierz", "sprawdzenie"
    ]
    assert result["bledy"] == []

    status = server.auto_pilot_status(run_id)
    assert status["status"] == "zakonczony"


def test_auto_pilot_zatrzymuje_sie_na_to_station(isolated_runs, fake_llm):
    run_id = server.start_run(zamiar="auto pilot stop test")["run_id"]
    result = server.auto_pilot_start(run_id, to_station="analiza")

    assert result["stacje_wykonane"] == ["inicjuj", "zmienne", "analiza"]
    assert result["status"] == "zatrzymany"


def test_auto_pilot_blad_parsowania_blokuje(isolated_runs, monkeypatch):
    class _RawProvider:
        def complete(self, prompt: str, system: str = "") -> str:
            return "Odpowiedz bez struktury koperty."

    monkeypatch.setattr(auto_pilot, "get_provider", lambda: _RawProvider())
    monkeypatch.setattr(auto_pilot, "is_configured", lambda: True)

    run_id = server.start_run(zamiar="auto pilot parse fail")["run_id"]
    result = server.auto_pilot_start(run_id)

    assert result["status"] == "zablokowany"
    assert any("KOPERTA" in b for b in result["bledy"])
