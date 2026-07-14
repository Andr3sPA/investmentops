"""Pruebas para el mecanismo de selección de proveedor/modelo por agente
(investmentops.ai_providers.selection).

Cubre la tarea "Definir el mecanismo de selección de proveedor/modelo por
agente vía configuración local" (TASKS.md, Fase 1, "Interfaz de
proveedores de IA"). No prueba ninguna implementación concreta de
`AIProvider` (ej. `AnthropicAIProvider`): esta resolución solo decide qué
proveedor/modelo le corresponden a un agente, sin instanciar nada.
"""

import pytest

from investmentops.ai_providers.selection import (
    AgentProviderSelection,
    AgentProviderSelectionError,
    resolve_agent_provider,
)


def test_agent_explicitly_mapped_to_a_provider_uses_that_provider() -> None:
    config = {
        "agents": {"financial_health": "anthropic"},
        "ai_providers": {
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"}
        },
    }

    selection = resolve_agent_provider("financial_health", config)

    assert isinstance(selection, AgentProviderSelection)
    assert selection.agent_id == "financial_health"
    assert selection.provider == "anthropic"
    assert selection.model == "claude-sonnet-5"


def test_agent_not_present_in_agents_falls_back_to_default_provider() -> None:
    config = {
        "agents": {},
        "ai_providers": {"default": {"provider": "ollama", "model": "llama3"}},
    }

    selection = resolve_agent_provider("valuation", config)

    assert selection.provider == "ollama"
    assert selection.model == "llama3"


def test_agent_mapped_literally_to_default_falls_back_to_default_provider() -> None:
    """Ej. `financial_health = "default"` en config.example.toml."""
    config = {
        "agents": {"financial_health": "default"},
        "ai_providers": {"default": {"provider": "anthropic", "model": "claude-sonnet-5"}},
    }

    selection = resolve_agent_provider("financial_health", config)

    assert selection.provider == "anthropic"
    assert selection.model == "claude-sonnet-5"


def test_missing_agents_section_falls_back_to_default_provider() -> None:
    config = {"ai_providers": {"default": {"provider": "gemini", "model": "gemini-pro"}}}

    selection = resolve_agent_provider("financial_health", config)

    assert selection.provider == "gemini"
    assert selection.model == "gemini-pro"


def test_missing_model_resolves_to_none() -> None:
    config = {
        "agents": {},
        "ai_providers": {"default": {"provider": "anthropic"}},
    }

    selection = resolve_agent_provider("valuation", config)

    assert selection.provider == "anthropic"
    assert selection.model is None


def test_raises_when_no_provider_can_be_resolved() -> None:
    config: dict = {"agents": {}, "ai_providers": {}}

    with pytest.raises(AgentProviderSelectionError, match="No se pudo resolver"):
        resolve_agent_provider("financial_health", config)


def test_raises_when_agent_maps_to_default_but_default_has_no_provider() -> None:
    config = {
        "agents": {"financial_health": "default"},
        "ai_providers": {"default": {"model": "claude-sonnet-5"}},
    }

    with pytest.raises(AgentProviderSelectionError, match="financial_health"):
        resolve_agent_provider("financial_health", config)


def test_agent_provider_selection_error_is_a_runtime_error() -> None:
    assert issubclass(AgentProviderSelectionError, RuntimeError)


def test_agent_provider_selection_is_immutable() -> None:
    selection = AgentProviderSelection(
        agent_id="financial_health", provider="anthropic", model="claude-sonnet-5"
    )

    with pytest.raises(AttributeError):
        selection.provider = "openai"  # type: ignore[misc]
