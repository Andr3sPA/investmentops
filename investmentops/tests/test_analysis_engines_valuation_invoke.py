"""Pruebas para la invocación al proveedor de IA del agente de valoración
(investmentops.analysis_engines.valuation.invoke_valuation_agent).

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
con esos múltiplos + el prompt" (TASKS.md, Fase 1, "Agente de análisis:
valoración"). No prueba el parseo de la respuesta del modelo a la
estructura final del agente (`AnalysisResult`): eso es una tarea separada
y posterior. Como `invoke_valuation_agent` termina invocando a
`AnthropicAIProvider.complete`, todas las pruebas mockean
`requests.post` en vez de depender de una llamada de red real.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderError, AIProviderResponse
from investmentops.analysis_engines.prompts import PromptError
from investmentops.analysis_engines.valuation import (
    calculate_valuation_metrics,
    invoke_valuation_agent,
)
from investmentops.data_layer import FinancialStatement, MarketData


def _statement(
    revenue: float = 1_000_000.0,
    net_income: float = 150_000.0,
    debt: float = 400_000.0,
) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=net_income,
        debt=debt,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def _market_data(
    price: float = 100.0,
    market_cap: float = 3_000_000.0,
) -> MarketData:
    return MarketData(
        price=price,
        market_cap=market_cap,
        multiples={},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def _config(**overrides: object) -> dict:
    config: dict = {
        "agents": {"valuation": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_response(text: str = "La empresa parece razonablemente valorada.") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_returns_ai_provider_response(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)

    result = invoke_valuation_agent(market_data, statement, metrics, config=_config())

    assert isinstance(result, AIProviderResponse)
    assert result.content == "La empresa parece razonablemente valorada."
    assert result.provider == "anthropic"
    assert mock_post.call_count == 1


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_the_agent_prompt(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)

    invoke_valuation_agent(market_data, statement, metrics, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "valoración" in message_content.lower()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_market_data_statement_and_metrics_as_data(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)

    invoke_valuation_agent(market_data, statement, metrics, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "price_to_earnings" in message_content
    assert "price_to_sales" in message_content
    assert "market_cap" in message_content
    assert "revenue" in message_content
    assert "period_end" in message_content
    assert "as_of" in message_content
    assert "2025-12-31" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_includes_zero_net_income_warning_in_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement(net_income=0.0)
    metrics = calculate_valuation_metrics(market_data, statement)

    invoke_valuation_agent(market_data, statement, metrics, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "price_to_earnings" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_uses_configured_model(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    config = _config(
        ai_providers={
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        }
    )

    invoke_valuation_agent(market_data, statement, metrics, config=config)

    assert mock_post.call_args.kwargs["json"]["model"] == "claude-haiku-4-5"


def test_invoke_raises_when_resolved_provider_is_not_supported() -> None:
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    config = _config(
        agents={"valuation": "gemini"},
        ai_providers={"default": {"provider": "gemini"}},
    )

    with pytest.raises(AIProviderError, match="No hay una integración concreta"):
        invoke_valuation_agent(market_data, statement, metrics, config=config)


def test_invoke_raises_when_no_provider_can_be_resolved() -> None:
    from investmentops.ai_providers.selection import AgentProviderSelectionError

    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    config: dict = {"agents": {}, "ai_providers": {}}

    with pytest.raises(AgentProviderSelectionError, match="No se pudo resolver"):
        invoke_valuation_agent(market_data, statement, metrics, config=config)


def test_invoke_raises_prompt_error_when_prompt_load_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirma que un fallo al cargar el prompt se propaga como `PromptError`."""
    import investmentops.analysis_engines.valuation as valuation_module

    def _broken_load_prompt(agent_id: str) -> str:
        raise PromptError(f"No se encontró el prompt de '{agent_id}' (simulado).")

    monkeypatch.setattr(valuation_module, "load_prompt", _broken_load_prompt)

    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)

    with pytest.raises(PromptError, match="simulado"):
        invoke_valuation_agent(market_data, statement, metrics, config=_config())
