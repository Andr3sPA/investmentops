"""Pruebas para la invocación al proveedor de IA del agente de estrategia
'value' (investmentops.analysis_engines.value.invoke_value_agent).

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
para el agente 'value', enviando los datos normalizados ya existentes
(sin nuevas fuentes ni cálculos adicionales) junto con el prompt"
(TASKS.md, Fase 6, "Motores de análisis por estrategia"). No prueba el
parseo de la respuesta del modelo a la estructura final del agente: eso
es una tarea separada y posterior. Como `invoke_value_agent` termina
invocando a `AnthropicAIProvider.complete`, todas las pruebas mockean
`requests.post` en vez de depender de una llamada de red real.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderError, AIProviderResponse
from investmentops.analysis_engines.financial_health import (
    FinancialHealthMetrics,
    calculate_financial_health_metrics,
)
from investmentops.analysis_engines.prompts import PromptError
from investmentops.analysis_engines.valuation import (
    ValuationMetrics,
    calculate_valuation_metrics,
)
from investmentops.analysis_engines.value import AGENT_ID, invoke_value_agent
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
        "agents": {"value": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_response(text: str = "Lectura de value investing.") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


def test_agent_id_is_value() -> None:
    assert AGENT_ID == "value"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_returns_ai_provider_response(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)

    result = invoke_value_agent(
        market_data, statement, valuation_metrics, health_metrics, config=_config()
    )

    assert isinstance(result, AIProviderResponse)
    assert result.content == "Lectura de value investing."
    assert result.provider == "anthropic"
    assert mock_post.call_count == 1


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_the_agent_prompt(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)

    invoke_value_agent(
        market_data, statement, valuation_metrics, health_metrics, config=_config()
    )

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "value investing" in message_content.lower()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_valuation_and_health_metrics_as_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)

    invoke_value_agent(
        market_data, statement, valuation_metrics, health_metrics, config=_config()
    )

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "price_to_earnings" in message_content
    assert "price_to_sales" in message_content
    assert "net_margin" in message_content
    assert "debt_to_revenue" in message_content
    assert "market_cap" in message_content
    assert "revenue" in message_content
    assert "period_end" in message_content
    assert "as_of" in message_content
    assert "2025-12-31" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_does_not_recalculate_metrics_sends_precalculated_values(
    mock_post: Mock,
) -> None:
    """Confirma que se envían las métricas ya calculadas tal cual, sin
    volver a derivarlas dentro de esta función."""
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    precalculated_valuation = ValuationMetrics(
        price_to_earnings=99.0, price_to_sales=1.0, warnings=()
    )
    precalculated_health = FinancialHealthMetrics(
        net_margin=0.5, debt_to_revenue=0.01, warnings=()
    )

    invoke_value_agent(
        market_data,
        statement,
        precalculated_valuation,
        precalculated_health,
        config=_config(),
    )

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "99.0" in message_content
    assert "0.5" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_includes_warnings_in_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement(net_income=0.0, revenue=0.0)
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)

    invoke_value_agent(
        market_data, statement, valuation_metrics, health_metrics, config=_config()
    )

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "price_to_earnings" in message_content
    assert "división por cero" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_uses_configured_model(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)
    config = _config(
        ai_providers={
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        }
    )

    invoke_value_agent(
        market_data, statement, valuation_metrics, health_metrics, config=config
    )

    assert mock_post.call_args.kwargs["json"]["model"] == "claude-haiku-4-5"


def test_invoke_raises_when_resolved_provider_is_not_supported() -> None:
    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)
    config = _config(
        agents={"value": "gemini"},
        ai_providers={"default": {"provider": "gemini"}},
    )

    with pytest.raises(AIProviderError, match="No hay una integración concreta"):
        invoke_value_agent(
            market_data, statement, valuation_metrics, health_metrics, config=config
        )


def test_invoke_raises_when_no_provider_can_be_resolved() -> None:
    from investmentops.ai_providers.selection import AgentProviderSelectionError

    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)
    config: dict = {"agents": {}, "ai_providers": {}}

    with pytest.raises(AgentProviderSelectionError, match="No se pudo resolver"):
        invoke_value_agent(
            market_data, statement, valuation_metrics, health_metrics, config=config
        )


def test_invoke_raises_prompt_error_when_prompt_load_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirma que un fallo al cargar el prompt se propaga como `PromptError`."""
    import investmentops.analysis_engines.value as value_module

    def _broken_load_prompt(agent_id: str) -> str:
        raise PromptError(f"No se encontró el prompt de '{agent_id}' (simulado).")

    monkeypatch.setattr(value_module, "load_prompt", _broken_load_prompt)

    market_data = _market_data()
    statement = _statement()
    valuation_metrics = calculate_valuation_metrics(market_data, statement)
    health_metrics = calculate_financial_health_metrics(statement)

    with pytest.raises(PromptError, match="simulado"):
        invoke_value_agent(
            market_data, statement, valuation_metrics, health_metrics, config=_config()
        )