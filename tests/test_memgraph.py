"""Testy warstwy Memgraph na fake driverze (bez polaczenia z baza)."""
from __future__ import annotations

import pytest

from pipeline_mcp import memgraph


class _FakeSession:
    def __init__(self, calls: list[tuple[str, dict]]):
        self._calls = calls

    def run(self, query: str, **params):
        self._calls.append((query, params))

        class _Result:
            def consume(self):
                return None

        return _Result()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeDriver:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    @property
    def queries(self) -> list[str]:
        return [q for q, _ in self.calls]

    def session(self):
        return _FakeSession(self.calls)


@pytest.fixture()
def fake_driver(monkeypatch):
    driver = _FakeDriver()
    monkeypatch.setattr(memgraph, "_driver", driver)
    monkeypatch.setattr(memgraph, "_driver_checked", True)
    return driver


def test_wezel_bez_labela_poprawna_klauzula(fake_driver):
    ok = memgraph.write_relation("cokolwiek:x", "innecos:y", "dotyczy")
    assert ok is True
    query = fake_driver.queries[-1]
    assert "{{" not in query and "}}" not in query
    assert "MERGE (a {id: $source})" in query


def test_rel_type_injection_odrzucony(fake_driver):
    zly_typ = "X]->(b) MATCH (n) DETACH DELETE n //"
    ok = memgraph.write_relation("run:r1", "stacja:r1:dobierz", zly_typ)
    assert ok is False
    assert fake_driver.queries == []  # zapytanie nie zostalo wykonane


def test_rel_type_normalizacja_myslnika(fake_driver):
    ok = memgraph.write_relation("run:r1", "stacja:r1:dobierz", "nastapila-po")
    assert ok is True
    assert "NASTAPILA_PO" in fake_driver.queries[-1]


def test_wezel_stacji_per_run(fake_driver):
    memgraph.write_station_node("run-a", "dobierz", "zakonczona")
    query, params = fake_driver.calls[-1]
    assert "MERGE (s:Stacja {id: $station_id})" in query
    assert params["station_id"] == "stacja:run-a:dobierz"
