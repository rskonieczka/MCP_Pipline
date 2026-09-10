"""Testy izolacji wieloklientowej: run'y, RAG, pamiec, cross-client access."""
from __future__ import annotations

import pytest

from pipeline_mcp import server, client_registry, rag, client_memory
from pipeline_mcp.config import get_config
from pipeline_mcp.models import ClientIdMismatchError


def _output_for(station: str) -> dict:
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


@pytest.fixture()
def two_clients(isolated_runs):
    """Rejestruje dwoch klientow."""
    config = get_config()
    config.clients_dir().mkdir(parents=True, exist_ok=True)

    client_registry.register_client(
        client_id="client-a",
        display_name="Client A",
        aliases=["alpha"],
    )
    client_registry.register_client(
        client_id="client-b",
        display_name="Client B",
        aliases=["beta"],
    )
    return "client-a", "client-b"


class TestRunIsolation:
    def test_run_is_in_client_directory(self, isolated_runs, two_clients):
        cid_a, _ = two_clients
        result = server.start_run(zamiar="test", client_id=cid_a)
        config = get_config()
        expected_dir = config.runs_dir_for(None, cid_a)
        assert str(expected_dir) in result["manifest_path"]

    def test_runs_in_separate_directories(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        r1 = server.start_run(zamiar="test a", client_id=cid_a)
        r2 = server.start_run(zamiar="test b", client_id=cid_b)
        assert r1["run_id"] != r2["run_id"]
        assert r1["client_id"] == cid_a
        assert r2["client_id"] == cid_b
        # Sprawdz ze manifesty sa w roznych katalogach
        assert cid_a in r1["manifest_path"]
        assert cid_b in r2["manifest_path"]
        assert cid_a not in r2["manifest_path"]
        assert cid_b not in r1["manifest_path"]

    def test_list_runs_filtered_by_client(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        server.start_run(zamiar="test a1", client_id=cid_a)
        server.start_run(zamiar="test a2", client_id=cid_a)
        server.start_run(zamiar="test b1", client_id=cid_b)

        runs_a = server.list_runs(client_id=cid_a)
        runs_b = server.list_runs(client_id=cid_b)

        assert len(runs_a) == 2
        assert len(runs_b) == 1
        assert all(r["client_id"] == cid_a for r in runs_a)
        assert all(r["client_id"] == cid_b for r in runs_b)

    def test_cross_client_access_blocked(self, isolated_runs, two_clients):
        """Proba odczytu run'u klienta A z client_id=B -> RunNotFound (niewidoczny)."""
        from pipeline_mcp.models import RunNotFoundError
        cid_a, cid_b = two_clients
        result = server.start_run(zamiar="test a", client_id=cid_a)
        run_id = result["run_id"]

        # Run klienta A jest niewidoczny dla klienta B (izolacja przez katalog)
        with pytest.raises(RunNotFoundError):
            server.get_run_status(run_id, client_id=cid_b)

    def test_cross_client_execute_blocked(self, isolated_runs, two_clients):
        from pipeline_mcp.models import RunNotFoundError
        cid_a, cid_b = two_clients
        result = server.start_run(zamiar="test a", client_id=cid_a)
        run_id = result["run_id"]

        with pytest.raises(RunNotFoundError):
            server.execute_station(run_id, "inicjuj", _output_for("inicjuj"), client_id=cid_b)


class TestLegacyMode:
    def test_legacy_run_no_client_id(self, isolated_runs):
        """Run bez client_id -> katalog legacy .ai-kb/pipeline-runs/."""
        result = server.start_run(zamiar="legacy test")
        assert result["client_id"] == ""
        config = get_config()
        # Sprawdz ze manifest jest w katalogu legacy
        assert ".ai-kb/pipeline-runs" in result["manifest_path"]
        assert "clients" not in result["manifest_path"]

    def test_legacy_list_runs(self, isolated_runs):
        server.start_run(zamiar="legacy 1")
        server.start_run(zamiar="legacy 2")
        runs = server.list_runs()
        assert len(runs) == 2
        assert all(r["client_id"] == "" for r in runs)


class TestRagIsolation:
    def test_index_and_search_per_client(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        rag.index_client_document(
            "doc1", "Ursa Major to klient A", "Doc A",
            client_id=cid_a,
        )
        rag.index_client_document(
            "doc2", "Orion to klient B", "Doc B",
            client_id=cid_b,
        )

        results_a = rag.search_client_rag("Ursa", cid_a, include_shared=False)
        results_b = rag.search_client_rag("Orion", cid_b, include_shared=False)

        assert len(results_a) == 1
        assert results_a[0]["doc_id"] == "doc1"
        assert len(results_b) == 1
        assert results_b[0]["doc_id"] == "doc2"

        # Cross-client: klient A nie widzi dokumentu B
        cross_a = rag.search_client_rag("Orion", cid_a, include_shared=False)
        assert len(cross_a) == 0

    def test_shared_rag_accessible_by_all(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        rag.index_client_document(
            "shared-doc", "Wspolna dokumentacja", "Shared",
            client_id="",  # shared
        )

        results_a = rag.search_client_rag("Wspolna", cid_a, include_shared=True)
        results_b = rag.search_client_rag("Wspolna", cid_b, include_shared=True)

        assert any(r["scope"] == "shared" for r in results_a)
        assert any(r["scope"] == "shared" for r in results_b)


class TestMemoryIsolation:
    def test_save_and_get_per_client(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        client_memory.save_client_memory(
            topic="decyzja A", content="klient A wybral X",
            client_id=cid_a,
        )
        client_memory.save_client_memory(
            topic="decyzja B", content="klient B wybral Y",
            client_id=cid_b,
        )

        mem_a = client_memory.list_client_memories(cid_a)
        mem_b = client_memory.list_client_memories(cid_b)

        assert len(mem_a) == 1
        assert len(mem_b) == 1
        assert mem_a[0]["topic"] == "decyzja A"
        assert mem_b[0]["topic"] == "decyzja B"

    def test_cross_client_memory_not_visible(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        client_memory.save_client_memory(
            topic="tajne A", content="sekret klienta A",
            client_id=cid_a,
        )

        # Klient B nie widzi pamieci klienta A
        mem_b = client_memory.list_client_memories(cid_b)
        assert len(mem_b) == 0

        # Wyszukiwanie u klienta B nie zwraca pamieci klienta A
        search_b = client_memory.search_client_memories("tajne", cid_b, include_shared=False)
        assert len(search_b) == 0

    def test_shared_memory_accessible(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        client_memory.save_shared_memory(
            topic="wspolny wzorzec", content="uzywamy Python 3.11",
        )

        search_a = client_memory.search_client_memories("wspolny", cid_a, include_shared=True)
        search_b = client_memory.search_client_memories("wspolny", cid_b, include_shared=True)

        assert any(r["scope"] == "shared" for r in search_a)
        assert any(r["scope"] == "shared" for r in search_b)


class TestActiveClientSession:
    def test_set_and_get_active_client(self, isolated_runs, two_clients):
        cid_a, _ = two_clients
        server.set_active_client(cid_a)
        assert server.get_active_client()["client_id"] == cid_a

    def test_active_client_used_in_start_run(self, isolated_runs, two_clients):
        cid_a, _ = two_clients
        server.set_active_client(cid_a)
        result = server.start_run(zamiar="test active")
        assert result["client_id"] == cid_a

    def test_explicit_client_id_overrides_active(self, isolated_runs, two_clients):
        cid_a, cid_b = two_clients
        server.set_active_client(cid_a)
        result = server.start_run(zamiar="test override", client_id=cid_b)
        assert result["client_id"] == cid_b


class TestGetRunStatusContract:
    def test_get_run_status_contains_zamiar(self, isolated_runs):
        """get_run_status musi zawierac pole zamiar (kontrakt API)."""
        result = server.start_run(zamiar="test zamiar field")
        run_id = result["run_id"]
        status = server.get_run_status(run_id)
        assert "zamiar" in status
        assert status["zamiar"] == "test zamiar field"

    def test_get_run_status_contains_zamiar_with_client(self, isolated_runs, two_clients):
        """get_run_status musi zawierac pole zamiar rowniez dla run'ow per-klient."""
        cid_a, _ = two_clients
        result = server.start_run(zamiar="client zamiar", client_id=cid_a)
        run_id = result["run_id"]
        status = server.get_run_status(run_id, client_id=cid_a)
        assert "zamiar" in status
        assert status["zamiar"] == "client zamiar"


class TestRagConcurrency:
    def test_concurrent_indexing_no_lost_updates(self, isolated_runs, two_clients):
        """Rownolegle indeksowanie dokumentow nie powoduje lost update."""
        import threading

        cid_a, _ = two_clients
        num_docs = 20
        errors: list[Exception] = []

        def index_batch(start: int):
            try:
                for i in range(start, start + num_docs // 4):
                    rag.index_client_document(
                        f"doc-{i}", f"content {i}", f"Title {i}",
                        client_id=cid_a,
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for t_idx in range(4):
            t = threading.Thread(target=index_batch, args=(t_idx * num_docs // 4,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Bledy podczas rownoleglego indeksowania: {errors}"

        # Wszystkie dokumenty musza byc w indeksie
        docs = rag.list_rag_documents(cid_a)
        doc_ids = {d["doc_id"] for d in docs}
        expected_ids = {f"doc-{i}" for i in range(num_docs)}
        assert doc_ids == expected_ids, (
            f"Utracone dokumenty: {expected_ids - doc_ids}. "
            f"Oczekiwano {num_docs}, znaleziono {len(doc_ids)}"
        )


class TestMemoryCollisionFix:
    """F2: auto-generowany memory_id nie nadpisuje istniejacej pamieci."""

    def test_same_topic_different_content_no_overwrite(self, isolated_runs, two_clients):
        """Dwa zapisy z tym samym tematem (ale rozna tresc) nie nadpisuja sie."""
        cid_a, _ = two_clients
        e1 = client_memory.save_client_memory(
            topic="Wybor bazy", content="PostgreSQL", client_id=cid_a,
        )
        e2 = client_memory.save_client_memory(
            topic="Wybor bazy", content="MySQL", client_id=cid_a,
        )
        assert e1.memory_id != e2.memory_id, (
            "Auto-generowany memory_id powinien byc unikalny przy kolizji tematu"
        )
        # Obie pamieci istnieja
        mems = client_memory.list_client_memories(cid_a)
        assert len(mems) == 2

    def test_explicit_memory_id_overwrites(self, isolated_runs, two_clients):
        """Jawny memory_id zachowuje semantyke upsert (nadpisuje)."""
        cid_a, _ = two_clients
        client_memory.save_client_memory(
            topic="decyzja", content="A", client_id=cid_a, memory_id="dec-001",
        )
        client_memory.save_client_memory(
            topic="decyzja", content="B", client_id=cid_a, memory_id="dec-001",
        )
        mems = client_memory.list_client_memories(cid_a)
        assert len(mems) == 1
        got = client_memory.get_client_memory("dec-001", cid_a)
        assert got.content == "B"

    def test_shared_memory_same_topic_no_overwrite(self, isolated_runs, two_clients):
        """Shared memory z tym samym tematem nie nadpisuje."""
        client_memory.save_shared_memory(topic="wzorzec", content="A")
        client_memory.save_shared_memory(topic="wzorzec", content="B")
        search = client_memory.search_client_memories("wzorzec", "client-a", include_shared=True)
        shared = [r for r in search if r["scope"] == "shared"]
        assert len(shared) == 2


class TestStartRunClientValidation:
    """F4: start_run waliduje istnienie klienta w rejestrze."""

    def test_start_run_unregistered_client_fails(self, isolated_runs):
        from pipeline_mcp.models import ClientNotFoundError
        with pytest.raises(ClientNotFoundError):
            server.start_run(zamiar="test", client_id="nieistniejacy")

    def test_start_run_registered_client_succeeds(self, isolated_runs, two_clients):
        cid_a, _ = two_clients
        result = server.start_run(zamiar="test", client_id=cid_a)
        assert result["client_id"] == cid_a

    def test_start_run_legacy_no_client_id_succeeds(self, isolated_runs):
        """Tryb legacy (brak client_id) nie wymaga rejestracji."""
        result = server.start_run(zamiar="legacy")
        assert result["client_id"] == ""


class TestDeleteClientMemgraphField:
    """F5: delete_client zwraca pole memgraph_deleted."""

    def test_delete_returns_memgraph_field(self, isolated_runs):
        client_registry.register_client(
            client_id="acme", display_name="ACME"
        )
        result = client_registry.delete_client("acme")
        assert "memgraph_deleted" in result
        # Memgraph wylaczony w testach -> False
        assert result["memgraph_deleted"] is False
