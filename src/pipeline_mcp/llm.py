"""Abstrakcja dostawcy LLM dla trybu auto-pilot."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from .config import get_config
from .models import LLMNotConfiguredError

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """Protokol dostawcy LLM."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Wywoluje LLM i zwraca tekst odpowiedzi."""
        ...


class OpenAIProvider:
    """Dostawca OpenAI (lub OpenAI-compatible jak Ollama)."""

    def __init__(self, model: str, api_key: str, base_url: str = "", max_tokens: int = 4096):
        try:
            import openai
        except ImportError as e:
            raise LLMNotConfiguredError(
                "Pakiet openai nie zainstalowany. Zainstaluj: pip install openai"
            ) from e

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, prompt: str, system: str = "") -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider:
    """Dostawca Anthropic."""

    def __init__(self, model: str, api_key: str, max_tokens: int = 4096):
        try:
            import anthropic
        except ImportError as e:
            raise LLMNotConfiguredError(
                "Pakiet anthropic nie zainstalowany. Zainstaluj: pip install anthropic"
            ) from e

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, prompt: str, system: str = "") -> str:
        response = self.client.messages.create(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
        )
        return response.content[0].text if response.content else ""


class LocalProvider:
    """Dostawca lokalny (Ollama / OpenAI-compatible endpoint)."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434/v1", max_tokens: int = 4096):
        try:
            import openai
        except ImportError as e:
            raise LLMNotConfiguredError(
                "Pakiet openai nie zainstalowany (wymagany dla lokalnego endpointu). "
                "Zainstaluj: pip install openai"
            ) from e

        self.client = openai.OpenAI(base_url=base_url, api_key="local")
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, prompt: str, system: str = "") -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


def get_provider() -> LLMProvider:
    """Zwraca dostawce LLM na podstawie konfiguracji."""
    config = get_config()

    if not config.llm_api_key and config.llm_provider != "local":
        raise LLMNotConfiguredError(
            f"PIPELINE_LLM_API_KEY nie ustawiony dla dostawcy '{config.llm_provider}'. "
            "Ustaw klucz API lub uzyj dostawcy 'local'."
        )

    if config.llm_provider == "openai":
        return OpenAIProvider(
            model=config.llm_model,
            api_key=config.llm_api_key,
            max_tokens=config.llm_max_tokens,
        )
    elif config.llm_provider == "anthropic":
        return AnthropicProvider(
            model=config.llm_model,
            api_key=config.llm_api_key,
            max_tokens=config.llm_max_tokens,
        )
    elif config.llm_provider == "local":
        base_url = config.llm_base_url or "http://localhost:11434/v1"
        return LocalProvider(
            model=config.llm_model,
            base_url=base_url,
            max_tokens=config.llm_max_tokens,
        )
    else:
        raise LLMNotConfiguredError(
            f"Nieznany dostawca LLM: '{config.llm_provider}'. "
            "Dostepne: openai, anthropic, local"
        )


def is_configured() -> bool:
    """Sprawdza czy LLM jest skonfigurowany."""
    config = get_config()
    if config.llm_provider == "local":
        return True
    return bool(config.llm_api_key)
