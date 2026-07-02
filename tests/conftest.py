"""Wspolne fixture'y testow pipeline-mcp.

Izoluje katalog persystencji w tmp_path i wylacza Memgraph,
resetujac singleton konfiguracji miedzy testami.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_runs(tmp_path, monkeypatch):
    """Izolowany katalog run'ow + wylaczony Memgraph + swiezy singleton Config."""
    import pipeline_mcp.config as config_mod
    import pipeline_mcp.memgraph as memgraph_mod

    monkeypatch.setenv("PIPELINE_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("PIPELINE_MEMGRAPH_ENABLED", "0")
    config_mod._config = None
    memgraph_mod._driver = None
    memgraph_mod._driver_checked = False
    yield tmp_path / "runs"
    config_mod._config = None
    memgraph_mod._driver = None
    memgraph_mod._driver_checked = False
