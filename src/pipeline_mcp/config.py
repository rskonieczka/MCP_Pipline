"""Konfiguracja serwera z zmiennych srodowiskowych."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# Polozenie tego pliku - uzywane do autodetekcji workspace (patrz _detect_workspace).
# Dla editable install: <workspace>/src/pipeline_mcp/config.py
_THIS_FILE = Path(__file__).resolve()


def _detect_workspace() -> Path | None:
    """Wykrywa workspace pakietu z polozenia editable-install.

    Dla editable install struktura to: <workspace>/src/pipeline_mcp/<plik>.
    Zwraca <workspace>, jesli istnieje tam pyproject.toml (potwierdzenie, ze to
    katalog projektu). W przeciwnym razie None (instalacja systemowa/site-packages
    - wtedy fallback do os.getcwd()).

    Pozwala to serwerowi MCP dzialac poprawnie niezaleznie od cwd procesu rodzica
    (Windsurf/Devin), bo workspace jest wnioskowany z polozenia kodu pakietu.
    """
    if (
        _THIS_FILE.parent.name == "pipeline_mcp"
        and _THIS_FILE.parent.parent.name == "src"
    ):
        ws = _THIS_FILE.parents[2]
        if (ws / "pyproject.toml").exists():
            return ws
    return None


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _env_int(key: str, default: int) -> int:
    """Odczyt int z env; nieprawidlowa wartosc nie wywala serwera przy starcie."""
    try:
        return int(os.environ.get(key, "") or default)
    except ValueError:
        return default


@dataclass
class Config:
    """Konfiguracja serwera wczytywana z env vars.

    PIPELINE_RUNS_DIR moze byc wzgledna (np. .ai-kb/pipeline-runs) -
    wtedy jest rozwiazywana wzgledem cwd procesu (workspace).
    Moze tez byc absolutna (np. /home/user/projekt/.ai-kb/pipeline-runs).
    """

    # Podstawowe
    # Surowa wartosc z env (wzgledna lub absolutna). Domyslnie wzgledna wzgledem cwd.
    runs_dir_raw: str = field(
        default_factory=lambda: _env("PIPELINE_RUNS_DIR", ".ai-kb/pipeline-runs")
    )
    auto_pilot: bool = field(
        default_factory=lambda: _env_bool("PIPELINE_AUTO_PILOT", False)
    )
    log_level: str = field(default_factory=lambda: _env("PIPELINE_LOG_LEVEL", "INFO"))

    # MT: domyslny klient dla sesji bez jawnego client_id (pusty = tryb legacy)
    default_client_id: str = field(
        default_factory=lambda: _env("PIPELINE_DEFAULT_CLIENT_ID", "")
    )

    # LLM (auto-pilot)
    llm_provider: str = field(
        default_factory=lambda: _env("PIPELINE_LLM_PROVIDER", "openai")
    )
    llm_model: str = field(
        default_factory=lambda: _env("PIPELINE_LLM_MODEL", "gpt-4o")
    )
    llm_api_key: str = field(default_factory=lambda: _env("PIPELINE_LLM_API_KEY", ""))
    llm_base_url: str = field(
        default_factory=lambda: _env("PIPELINE_LLM_BASE_URL", "")
    )
    llm_max_tokens: int = field(
        default_factory=lambda: _env_int("PIPELINE_LLM_MAX_TOKENS", 4096)
    )
    llm_system_prompt: str = field(
        default_factory=lambda: _env(
            "PIPELINE_LLM_SYSTEM_PROMPT",
            "Mysl i odpowiadaj wylacznie po polsku. Zachowaj profesjonalny, techniczny styl.",
        )
    )

    # Memgraph (opcjonalne)
    memgraph_url: str = field(
        default_factory=lambda: _env("MEMGRAPH_URL", "bolt://localhost:7687")
    )
    memgraph_user: str = field(default_factory=lambda: _env("MEMGRAPH_USER", ""))
    memgraph_password: str = field(
        default_factory=lambda: _env("MEMGRAPH_PASSWORD", "")
    )
    memgraph_enabled: bool = field(
        default_factory=lambda: _env_bool("PIPELINE_MEMGRAPH_ENABLED", True)
    )

    @property
    def runs_dir(self) -> Path:
        """Zwraca katalog run'ow rozwiazany wzgledem workspace.

        Jesli PIPELINE_RUNS_DIR jest wzgledna, rozwiazuje ja wzgledem workspace
        wykrytego z polozenia editable-install pakietu (patrz _detect_workspace).
        Jesli autodetekcja zawiedzie (instalacja systemowa), fallback do os.getcwd().
        Jesli absolutna, uzywa jak jest.
        """
        path = Path(self.runs_dir_raw)
        if not path.is_absolute():
            ws = _detect_workspace()
            base = ws if ws is not None else Path.cwd()
            path = base / path
        return path.resolve()

    def _workspace_base(self, workspace: str | None) -> Path:
        """Rozwiazuje bazowy katalog workspace."""
        if workspace is not None:
            ws_path = Path(workspace).expanduser()
            if not ws_path.is_absolute():
                ws_path = Path.cwd() / ws_path
            return ws_path.resolve()
        # MT: PIPELINE_WORKSPACE nadpisuje autodetekcje (przydatne dla testow)
        env_ws = _env("PIPELINE_WORKSPACE")
        if env_ws:
            ws_path = Path(env_ws).expanduser()
            if not ws_path.is_absolute():
                ws_path = Path.cwd() / ws_path
            return ws_path.resolve()
        ws = _detect_workspace()
        return ws if ws is not None else Path.cwd()

    def runs_dir_for(self, workspace: str | None = None, client_id: str = "") -> Path:
        """Zwraca katalog run'ow dla danego workspace'a i klienta.

        Args:
            workspace: Sciezka do workspace'a (absolutna lub wzgledna).
                       Jesli None, uzywa domyslnego runs_dir.
            client_id: Identyfikator klienta. Jesli niepusty, zwraca
                       <workspace>/.ai-kb/clients/<client_id>/pipeline-runs/.
                       Jesli pusty, zwraca <workspace>/.ai-kb/pipeline-runs/ (legacy).

        Returns:
            Katalog run'ow.
        """
        if workspace is None and not client_id:
            return self.runs_dir

        base = self._workspace_base(workspace)

        if client_id:
            return base / ".ai-kb" / "clients" / client_id / "pipeline-runs"

        return base / ".ai-kb" / "pipeline-runs"

    def ensure_runs_dir(self, workspace: str | None = None, client_id: str = "") -> Path:
        """Tworzy katalog persystencji jesli nie istnieje. Zwraca sciezke."""
        runs_dir = self.runs_dir_for(workspace, client_id)
        runs_dir.mkdir(parents=True, exist_ok=True)
        return runs_dir

    def run_dir(self, run_id: str, workspace: str | None = None, client_id: str = "") -> Path:
        """Zwraca sciezke katalogu run'u."""
        return self.runs_dir_for(workspace, client_id) / run_id

    def manifest_path(self, run_id: str, workspace: str | None = None, client_id: str = "") -> Path:
        """Zwraca sciezke manifestu run'u."""
        return self.run_dir(run_id, workspace, client_id) / "manifest.yaml"

    def checkpoint_path(
        self, run_id: str, station: str, suffix: str = "", workspace: str | None = None,
        client_id: str = "",
    ) -> Path:
        """Zwraca sciezke checkpointu stacji."""
        return self.run_dir(run_id, workspace, client_id) / f"stan_{station}{suffix}.yaml"

    def envelope_final_path(self, run_id: str, workspace: str | None = None, client_id: str = "") -> Path:
        """Zwraca sciezke ostatecznej koperty."""
        return self.run_dir(run_id, workspace, client_id) / "envelope_final.yaml"

    # MT: sciezki per-klient

    def clients_dir(self, workspace: str | None = None) -> Path:
        """Zwraca katalog wszystkich klientow."""
        base = self._workspace_base(workspace)
        return base / ".ai-kb" / "clients"

    def client_dir(self, client_id: str, workspace: str | None = None) -> Path:
        """Zwraca katalog pojedynczego klienta."""
        return self.clients_dir(workspace) / client_id

    def client_context_path(self, client_id: str, workspace: str | None = None) -> Path:
        """Zwraca sciezke pliku context.yaml klienta."""
        return self.client_dir(client_id, workspace) / "context.yaml"

    def client_rag_dir(self, client_id: str, workspace: str | None = None) -> Path:
        """Zwraca katalog RAG per-klient."""
        return self.client_dir(client_id, workspace) / "rag"

    def client_memory_dir(self, client_id: str, workspace: str | None = None) -> Path:
        """Zwraca katalog pamieci AI per-klient."""
        return self.client_dir(client_id, workspace) / "memory"

    # MT: sciezki wspoldzielone

    def shared_knowledge_dir(self, workspace: str | None = None) -> Path:
        """Zwraca katalog wiedzy wspoldzielonej."""
        base = self._workspace_base(workspace)
        return base / ".ai-kb" / "shared-knowledge"

    def shared_rag_dir(self, workspace: str | None = None) -> Path:
        """Zwraca katalog wspoldzielonego RAG."""
        return self.shared_knowledge_dir(workspace) / "rag"

    def shared_memory_dir(self, workspace: str | None = None) -> Path:
        """Zwraca katalog wspoldzielonej pamieci AI."""
        return self.shared_knowledge_dir(workspace) / "memory"


# Singleton konfiguracji
_config: Config | None = None


def get_config() -> Config:
    """Zwraca singleton konfiguracji."""
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_runs_dir()
    return _config
