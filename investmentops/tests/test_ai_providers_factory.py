"""Pruebas para la fábrica de instancias concretas de `AIProvider`
(investmentops.ai_providers.factory).

Cubre la pieza faltante identificada en `investmentops/ai_providers/
EXTENDING.md` ("Quién decide qué clase concreta instanciar") y necesaria
para la tarea "Implementar la invocación al proveedor de IA configurado
con esas métricas + el prompt" (TASKS.md, Fase 1, "Agente de análisis:
salud financiera"). No prueba ninguna llamada de red real: usa
`AnthropicAIProvider` solo para confirmar el tipo de instancia devuelta,
sin invocar `.complete(...)`.
"""

import pytest

from investmentops.ai_providers.anthropic_provider import AnthropicAIProvider
from investmentops.ai_providers.contracts import AIProvider, AIProviderError
from investmentops.ai_providers.factory import build_ai_provider


def test_build_ai_provider_returns_anthropic_instance_for_anthropic() -> None:
    provider = build_ai_provider(
        "anthropic",
        config={"ai_providers": {"anthropic": {"api_key": "fake-key"}}},
    )

    assert isinstance(provider, AnthropicAIProvider)
    assert isinstance(provider, AIProvider)


def test_build_ai_provider_raises_for_unsupported_provider() -> None:
    with pytest.raises(AIProviderError, match="No hay una integración concreta"):
        build_ai_provider("gemini", config={})


def test_build_ai_provider_error_message_lists_supported_providers() -> None:
    with pytest.raises(AIProviderError, match="anthropic"):
        build_ai_provider("ollama", config={})


def test_build_ai_provider_propagates_construction_errors() -> None:
    """Si falta la API key, el error debe venir de la propia clase concreta."""
    with pytest.raises(AIProviderError, match="Falta la API key"):
        build_ai_provider(
            "anthropic", config={"ai_providers": {"anthropic": {}}}
        )
