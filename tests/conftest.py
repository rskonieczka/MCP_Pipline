"""Wspolne fixture'y testow pipeline-mcp.

Izoluje katalog persystencji w tmp_path i wylacza Memgraph,
resetujac singleton konfiguracji miedzy testami.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_runs(tmp_path, monkeypatch):
    """Izolowany katalog run'ow + klienci + wylaczony Memgraph + swiezy singleton Config."""
    import pipeline_mcp.config as config_mod
    import pipeline_mcp.memgraph as memgraph_mod
    import pipeline_mcp.server as server_mod

    # MT: PIPELINE_WORKSPACE izoluje katalog .ai-kb (klienci, wiedza, RAG, pamiec)
    monkeypatch.setenv("PIPELINE_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("PIPELINE_RUNS_DIR", str(tmp_path / ".ai-kb" / "pipeline-runs"))
    monkeypatch.setenv("PIPELINE_MEMGRAPH_ENABLED", "0")
    config_mod._config = None
    memgraph_mod._driver = None
    memgraph_mod._driver_checked = False
    # MT: reset aktywnego klienta miedzy testami
    server_mod._active_client_id = ""
    yield tmp_path / ".ai-kb" / "pipeline-runs"
    config_mod._config = None
    memgraph_mod._driver = None
    memgraph_mod._driver_checked = False
    server_mod._active_client_id = ""
