"""Testy rejestru klientow: normalizacja, dopasowanie, rejestracja, izolacja.

Pokrywa scenariusze uzytkownika:
    UrsaMajor, ursamajor, ursa major, ursa, 262-977-6197, 6197
"""
from __future__ import annotations

import pytest

from pipeline_mcp import client_registry
from pipeline_mcp.config import get_config
from pipeline_mcp.models import ClientAlreadyExistsError, ClientNotFoundError


@pytest.fixture()
def setup_ursa_major(isolated_runs):
    """Rejestruje klienta Ursa Major Inc. z aliasami i NIP."""
    config = get_config()
    clients_dir = config.clients_dir()
    clients_dir.mkdir(parents=True, exist_ok=True)

    context = client_registry.register_client(
        client_id="ursa-major-inc",
        display_name="Ursa Major Inc.",
        aliases=["UrsaMajor", "ursamajor", "ursa major", "ursa"],
        external_ids={"nip": "2629776197", "phone": "262-977-6197"},
        id_fragments=["6197", "9776197"],
        metadata={"industry": "IT"},
    )
    return context


class TestNormalize:
    def test_normalize_case_and_spaces(self):
        assert client_registry.normalize("UrsaMajor") == "ursamajor"
        assert client_registry.normalize("ursa major") == "ursamajor"
        assert client_registry.normalize("ursamajor") == "ursamajor"

    def test_normalize_hyphens(self):
        assert client_registry.normalize("262-977-6197") == "2629776197"

    def test_normalize_accents(self):
        assert client_registry.normalize("Zółw") == "zolw"

    def test_normalize_punctuation(self):
        assert client_registry.normalize("S.A.") == "sa"
        assert client_registry.normalize("Sp. z o.o.") == "spzoo"


class TestValidateClientId:
    def test_valid_slug(self):
        client_registry.validate_client_id("ursa-major-inc")
        client_registry.validate_client_id("acme")
        client_registry.validate_client_id("client123")

    def test_empty_rejected(self):
        with pytest.raises(Exception):
            client_registry.validate_client_id("")

    def test_uppercase_rejected(self):
        with pytest.raises(Exception):
            client_registry.validate_client_id("UrsaMajor")

    def test_spaces_rejected(self):
        with pytest.raises(Exception):
            client_registry.validate_client_id("ursa major")

    def test_path_traversal_rejected(self):
        with pytest.raises(Exception):
            client_registry.validate_client_id("../etc")
        with pytest.raises(Exception):
            client_registry.validate_client_id("a/b")


class TestRegisterClient:
    def test_register_success(self, isolated_runs):
        ctx = client_registry.register_client(
            client_id="acme-corp",
            display_name="ACME Corp",
            aliases=["acme", "ACME"],
        )
        assert ctx.client_id == "acme-corp"
        assert ctx.display_name == "ACME Corp"
        assert ctx.status == "aktywny"
        assert ctx.aliases == ["acme", "ACME"]

    def test_register_duplicate_fails(self, isolated_runs):
        client_registry.register_client(
            client_id="acme-corp", display_name="ACME Corp"
        )
        with pytest.raises(ClientAlreadyExistsError):
            client_registry.register_client(
                client_id="acme-corp", display_name="ACME Corp 2"
            )

    def test_load_client(self, isolated_runs):
        client_registry.register_client(
            client_id="acme-corp", display_name="ACME Corp"
        )
        loaded = client_registry.load_client("acme-corp")
        assert loaded is not None
        assert loaded.client_id == "acme-corp"

    def test_load_nonexistent_returns_none(self, isolated_runs):
        assert client_registry.load_client("nonexistent") is None


class TestResolveClient:
    """Testy scenariuszy uzytkownika: 7 wariantow tego samego klienta."""

    def test_resolve_alias_ursamajor_camelcase(self, setup_ursa_major):
        result = client_registry.resolve_client("UrsaMajor")
        assert len(result.matches) == 1
        assert result.matches[0].client_id == "ursa-major-inc"
        assert result.matches[0].confidence == 95
        assert result.matches[0].matched_on == "alias"
        assert result.auto_resolved is False
        assert result.needs_confirmation is True

    def test_resolve_alias_ursamajor_lowercase(self, setup_ursa_major):
        result = client_registry.resolve_client("ursamajor")
        assert len(result.matches) == 1
        assert result.matches[0].client_id == "ursa-major-inc"
        assert result.matches[0].confidence == 95

    def test_resolve_alias_ursa_major_with_space(self, setup_ursa_major):
        result = client_registry.resolve_client("ursa major")
        assert len(result.matches) == 1
        assert result.matches[0].client_id == "ursa-major-inc"
        assert result.matches[0].confidence == 95

    def test_resolve_alias_ursa_short(self, setup_ursa_major):
        result = client_registry.resolve_client("ursa")
        assert len(result.matches) == 1
        assert result.matches[0].client_id == "ursa-major-inc"
        assert result.matches[0].confidence == 95

    def test_resolve_external_id_nip_auto(self, setup_ursa_major):
        result = client_registry.resolve_client("262-977-6197")
        assert len(result.matches) == 1
        assert result.matches[0].client_id == "ursa-major-inc"
        assert result.matches[0].confidence == 100
        assert result.matches[0].matched_on == "external_id:nip"
        assert result.auto_resolved is True
        assert result.needs_confirmation is False

    def test_resolve_external_id_phone_auto(self, setup_ursa_major):
        result = client_registry.resolve_client("2629776197")
        assert len(result.matches) == 1
        assert result.matches[0].confidence == 100
        assert result.auto_resolved is True

    def test_resolve_id_fragment_6197(self, setup_ursa_major):
        result = client_registry.resolve_client("6197")
        assert len(result.matches) == 1
        assert result.matches[0].client_id == "ursa-major-inc"
        assert result.matches[0].confidence == 80
        assert result.matches[0].matched_on == "id_fragment"
        assert result.auto_resolved is False
        assert result.needs_confirmation is True

    def test_resolve_no_match(self, setup_ursa_major):
        result = client_registry.resolve_client("nonexistent-company")
        assert len(result.matches) == 0
        assert result.auto_resolved is False
        assert result.needs_confirmation is False
        assert "Zarejestruj" in result.suggested_action or "register" in result.suggested_action.lower()

    def test_resolve_ambiguous_multiple_aliases(self, isolated_runs):
        """Dwoch klientow z tym samym aliasem -> niejednoznacznosc."""
        client_registry.register_client(
            client_id="ursa-major-inc",
            display_name="Ursa Major Inc.",
            aliases=["ursa"],
        )
        client_registry.register_client(
            client_id="ursa-minor-llc",
            display_name="Ursa Minor LLC",
            aliases=["ursa"],
        )
        result = client_registry.resolve_client("ursa")
        assert len(result.matches) == 2
        assert result.auto_resolved is False
        assert result.needs_confirmation is True
        assert "2 klientow" in result.suggested_action or "wybor" in result.suggested_action.lower()

    def test_resolve_exact_client_id_auto(self, setup_ursa_major):
        result = client_registry.resolve_client("ursa-major-inc")
        assert len(result.matches) == 1
        assert result.matches[0].confidence == 100
        assert result.matches[0].matched_on == "client_id"
        assert result.auto_resolved is True

    def test_resolve_fuzzy_never_auto_resolves(self, isolated_runs):
        """Fuzzy match (L5) nigdy nie auto-rozpoznaje, nawet przy sim=1.0.

        Klient z display_name bez odpowiadajacego aliasu - dopasowanie
        fuzzy po nazwie wyswietlanej musi wymagac potwierdzenia.
        """
        client_registry.register_client(
            client_id="acme",
            display_name="Acme Corporation",
            aliases=[],  # brak aliasu "acmecorporation"
        )
        result = client_registry.resolve_client("acmecorporation")
        assert len(result.matches) == 1
        assert result.matches[0].matched_on == "fuzzy_name"
        assert result.matches[0].confidence <= 79
        assert result.auto_resolved is False
        assert result.needs_confirmation is True


class TestArchiveDeleteClient:
    def test_archive_client(self, isolated_runs):
        client_registry.register_client(
            client_id="acme", display_name="ACME"
        )
        ctx = client_registry.archive_client("acme")
        assert ctx.status == "zarchiwizowany"

    def test_archived_client_not_in_resolve(self, isolated_runs):
        client_registry.register_client(
            client_id="acme", display_name="ACME", aliases=["acme"]
        )
        client_registry.archive_client("acme")
        result = client_registry.resolve_client("acme")
        assert len(result.matches) == 0

    def test_delete_client(self, isolated_runs):
        client_registry.register_client(
            client_id="acme", display_name="ACME"
        )
        result = client_registry.delete_client("acme")
        assert result["deleted"] is True
        assert client_registry.load_client("acme") is None

    def test_delete_nonexistent_fails(self, isolated_runs):
        with pytest.raises(ClientNotFoundError):
            client_registry.delete_client("nonexistent")

    def test_delete_client_path_traversal_rejected(self, isolated_runs):
        """Path traversal w client_id musi byc odrzucony przed shutil.rmtree."""
        with pytest.raises(Exception):
            client_registry.delete_client("../../..")

    def test_delete_client_path_traversal_slash_rejected(self, isolated_runs):
        """Slash w client_id musi byc odrzucony."""
        with pytest.raises(Exception):
            client_registry.delete_client("a/b")

    def test_delete_client_reports_rag_and_memory_deleted(self, isolated_runs):
        """delete_client zwraca rag_deleted/memory_deleted=True gdy katalogi istnialy."""
        client_registry.register_client(
            client_id="acme", display_name="ACME"
        )
        # Utworz katalogi rag i memory z danymi
        config = get_config()
        rag_dir = config.client_rag_dir("acme")
        rag_dir.mkdir(parents=True, exist_ok=True)
        (rag_dir / "index.yaml").write_text("documents: []")

        mem_dir = config.client_memory_dir("acme")
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "test.yaml").write_text("memory_id: test")

        result = client_registry.delete_client("acme")
        assert result["deleted"] is True
        assert result["rag_deleted"] is True
        assert result["memory_deleted"] is True

    def test_delete_client_reports_false_when_no_rag_memory(self, isolated_runs):
        """delete_client zwraca rag_deleted/memory_deleted=False gdy katalogi nie istnialy."""
        client_registry.register_client(
            client_id="acme", display_name="ACME"
        )
        result = client_registry.delete_client("acme")
        assert result["deleted"] is True
        assert result["rag_deleted"] is False
        assert result["memory_deleted"] is False


class TestUpdateClient:
    def test_update_aliases(self, isolated_runs):
        client_registry.register_client(
            client_id="acme", display_name="ACME", aliases=["acme"]
        )
        ctx = client_registry.update_client(
            "acme", {"aliases": ["acme", "acme-corp", "ACME"]}
        )
        assert "acme-corp" in ctx.aliases

    def test_update_nonexistent_fails(self, isolated_runs):
        with pytest.raises(ClientNotFoundError):
            client_registry.update_client("nonexistent", {"aliases": []})

    def test_update_path_traversal_rejected(self, isolated_runs):
        """Path traversal w client_id przy update musi byc odrzucony."""
        with pytest.raises(Exception):
            client_registry.update_client("../../..", {"aliases": []})

    def test_archive_path_traversal_rejected(self, isolated_runs):
        """Path traversal w client_id przy archive musi byc odrzucony."""
        with pytest.raises(Exception):
            client_registry.archive_client("../../..")

    def test_load_path_traversal_rejected(self, isolated_runs):
        """Path traversal w client_id przy load musi byc odrzucony."""
        with pytest.raises(Exception):
            client_registry.load_client("../../..")


class TestMemgraphNodeIds:
    """F1: ID wezlow Memgraph zawieraja client_id dla izolacji."""

    def test_run_node_id_includes_client_id(self):
        from pipeline_mcp.memgraph import _run_node_id
        assert _run_node_id("run-1", "client-a") == "run:client-a:run-1"
        assert _run_node_id("run-1", "") == "run:run-1"

    def test_station_node_id_includes_client_id(self):
        from pipeline_mcp.memgraph import _station_node_id
        assert _station_node_id("run-1", "inicjuj", "client-a") == "stacja:client-a:run-1:inicjuj"
        assert _station_node_id("run-1", "inicjuj", "") == "stacja:run-1:inicjuj"

    def test_req_node_id_includes_client_id(self):
        from pipeline_mcp.memgraph import _req_node_id
        assert _req_node_id("run-1", "REQ-001", "client-a") == "wymaganie:client-a:run-1:REQ-001"
        assert _req_node_id("run-1", "REQ-001", "") == "wymaganie:run-1:REQ-001"

    def test_different_clients_different_node_ids(self):
        """Dwoch klientow z tym samym run_id ma rozne node IDs."""
        from pipeline_mcp.memgraph import _run_node_id, _station_node_id
        id_a = _run_node_id("2026-09-10-test", "client-a")
        id_b = _run_node_id("2026-09-10-test", "client-b")
        assert id_a != id_b
        st_a = _station_node_id("2026-09-10-test", "inicjuj", "client-a")
        st_b = _station_node_id("2026-09-10-test", "inicjuj", "client-b")
        assert st_a != st_b


class TestDeleteClientRunCount:
    """F5: delete_client liczy tylko katalogi run'ow (nie pliki)."""

    def test_run_count_counts_only_dirs(self, isolated_runs):
        client_registry.register_client(
            client_id="acme", display_name="ACME"
        )
        config = get_config()
        runs_dir = config.runs_dir_for(None, "acme")
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / "run-1").mkdir()
        (runs_dir / "run-2").mkdir()
        # Plik nie bedacy katalogiem - nie powinien byc policzony jako run
        (runs_dir / ".DS_Store").write_text("noise")

        result = client_registry.delete_client("acme")
        assert result["runs_deleted"] == 2
