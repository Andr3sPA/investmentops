"""Pruebas para el contrato de "AI provider" (investmentops.ai_providers).

Cubre la tarea "Definir el contrato de 'AI provider' (entrada: prompt +
datos estructurados; salida: respuesta del modelo + metadatos de
proveedor/modelo usado), común para Gemini, Claude, OpenAI y Ollama."
(TASKS.md, Fase 1, "Contratos e interfaces"). No prueba ninguna
integración concreta: eso corresponde a tareas posteriores (ver
TASKS.md, "Interfaz de proveedores de IA").
"""

from datetime import datetime, timezone

import pytest

from investmentops.ai_providers import (
    AIProvider,
    AIProviderError,
    AIProviderResponse,
)


class _DummyProvider:
    """Proveedor de IA mínimo de prueba que cumple el contrato `AIProvider`."""

    def complete(self, prompt: str, data=None) -> AIProviderResponse:
        return AIProviderResponse(
            content=f"interpretación para: {prompt}",
            provider="dummy_provider",
            model="dummy-model",
            generated_at=datetime.now(timezone.utc),
        )


class _FailingProvider:
    """Proveedor de IA mínimo de prueba que señala un fallo mediante el contrato."""

    def complete(self, prompt: str, data=None) -> AIProviderResponse:
        raise AIProviderError("El proveedor de IA no respondió")


def test_dummy_provider_satisfies_ai_provider_protocol() -> None:
    provider = _DummyProvider()

    assert isinstance(provider, AIProvider)


def test_complete_returns_ai_provider_response_with_metadata() -> None:
    provider = _DummyProvider()

    response = provider.complete("interpreta estos ratios", data={"current_ratio": 1.5})

    assert isinstance(response, AIProviderResponse)
    assert response.content == "interpretación para: interpreta estos ratios"
    assert response.provider == "dummy_provider"
    assert response.model == "dummy-model"
    assert isinstance(response.generated_at, datetime)


def test_complete_accepts_data_as_optional() -> None:
    provider = _DummyProvider()

    response = provider.complete("prompt sin datos adicionales")

    assert response.content == "interpretación para: prompt sin datos adicionales"


def test_failing_provider_raises_ai_provider_error() -> None:
    provider = _FailingProvider()

    with pytest.raises(AIProviderError, match="no respondió"):
        provider.complete("cualquier prompt")


def test_ai_provider_error_is_a_runtime_error() -> None:
    assert issubclass(AIProviderError, RuntimeError)


def test_ai_provider_response_is_immutable() -> None:
    response = AIProviderResponse(
        content="texto",
        provider="dummy_provider",
        model="dummy-model",
        generated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(AttributeError):
        response.content = "otro texto"  # type: ignore[misc]
