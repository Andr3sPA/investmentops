"""Pruebas para el proveedor concreto de Anthropic
(investmentops.ai_providers.anthropic_provider).

Cubre las tareas "Implementar al menos una integración concreta... que
cumpla la interfaz" e "Implementar manejo de error básico cuando el
proveedor de IA no responde o devuelve un formato inesperado" (TASKS.md,
Fase 1, "Interfaz de proveedores de IA"). Como este cliente hace llamadas
HTTP reales a la API de Anthropic, todas las pruebas simulan (mockean)
`requests.post` en vez de depender de una llamada de red real o de una
API key válida.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from investmentops.ai_providers import AIProvider, AIProviderError, AIProviderResponse
from investmentops.ai_providers.anthropic_provider import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    AnthropicAIProvider,
)


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def _success_payload(text: str = "La empresa muestra una liquidez estable.") -> dict:
    return {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }


def test_provider_satisfies_ai_provider_protocol() -> None:
    provider = AnthropicAIProvider(api_key="fake-key")

    assert isinstance(provider, AIProvider)


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_returns_ai_provider_response_for_valid_prompt(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response(_success_payload())

    provider = AnthropicAIProvider(api_key="fake-key")
    result = provider.complete("interpreta estos ratios", data={"current_ratio": 1.5})

    assert isinstance(result, AIProviderResponse)
    assert result.content == "La empresa muestra una liquidez estable."
    assert result.provider == "anthropic"
    assert result.model == "claude-sonnet-5"
    assert mock_post.call_count == 1


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_sends_api_key_and_prompt_with_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response(_success_payload())

    provider = AnthropicAIProvider(api_key="my-secret-key", model="claude-sonnet-5")
    provider.complete("interpreta estos ratios", data={"current_ratio": 1.5})

    call = mock_post.call_args
    assert call.kwargs["headers"]["x-api-key"] == "my-secret-key"
    body = call.kwargs["json"]
    assert body["model"] == "claude-sonnet-5"
    message_content = body["messages"][0]["content"]
    assert "interpreta estos ratios" in message_content
    assert "current_ratio" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_accepts_data_as_optional(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response(_success_payload())

    provider = AnthropicAIProvider(api_key="fake-key")
    result = provider.complete("prompt sin datos adicionales")

    body = mock_post.call_args.kwargs["json"]
    assert body["messages"][0]["content"] == "prompt sin datos adicionales"
    assert result.content == "La empresa muestra una liquidez estable."


def test_complete_rejects_empty_prompt() -> None:
    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="no puede estar vacío"):
        provider.complete("   ")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_on_network_failure(mock_post: Mock) -> None:
    mock_post.side_effect = requests.ConnectionError("boom")

    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="No se pudo contactar"):
        provider.complete("cualquier prompt")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_on_unauthorized(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response({}, status_code=401)

    provider = AnthropicAIProvider(api_key="bad-key")

    with pytest.raises(AIProviderError, match="rechazó"):
        provider.complete("cualquier prompt")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_on_rate_limit(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response({}, status_code=429)

    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="límite de tasa"):
        provider.complete("cualquier prompt")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_on_server_error(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response({}, status_code=500)

    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="error \\(500\\)"):
        provider.complete("cualquier prompt")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_on_invalid_json(mock_post: Mock) -> None:
    bad_response = Mock()
    bad_response.status_code = 200
    bad_response.json.side_effect = ValueError("not json")
    mock_post.return_value = bad_response

    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="no se pudo"):
        provider.complete("cualquier prompt")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_when_content_is_missing(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response({"model": "claude-sonnet-5", "content": []})

    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="sin contenido"):
        provider.complete("cualquier prompt")


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_complete_raises_when_no_text_blocks_present(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response(
        {"model": "claude-sonnet-5", "content": [{"type": "image", "source": {}}]}
    )

    provider = AnthropicAIProvider(api_key="fake-key")

    with pytest.raises(AIProviderError, match="sin texto"):
        provider.complete("cualquier prompt")


def test_constructor_raises_without_api_key() -> None:
    with pytest.raises(AIProviderError, match="Falta la API key"):
        AnthropicAIProvider(config={"ai_providers": {"anthropic": {}}})


def test_constructor_reads_api_key_base_url_and_model_from_config() -> None:
    config = {
        "ai_providers": {
            "anthropic": {
                "api_key": "from-config",
                "base_url": "https://example.test/v1",
            },
            "default": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        }
    }

    provider = AnthropicAIProvider(config=config)

    assert provider._api_key == "from-config"
    assert provider._base_url == "https://example.test/v1"
    assert provider._model == "claude-haiku-4-5"


def test_constructor_uses_defaults_when_not_configured() -> None:
    provider = AnthropicAIProvider(
        config={"ai_providers": {"anthropic": {"api_key": "k"}}}
    )

    assert provider._base_url == DEFAULT_BASE_URL
    assert provider._model == DEFAULT_MODEL
