"""Pruebas para la invocación al proveedor de IA del agente de estrategia
'growth' (investmentops.analysis_engines.growth.invoke_growth_agent).

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
para el agente 'growth', enviando los datos normalizados ya existentes
junto con el prompt" (TASKS.md, Fase 6, "Motores de análisis por
estrategia"). No prueba el parseo de la respuesta del modelo a la
estructura final del agente: eso es una tarea separada y posterior. Como
`invoke_growth_agent` termina invocando a `AnthropicAIProvider.complete`,
todas las pruebas mockean `requests.post` en vez de depender de una
llamada de red real.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderError, AIProviderResponse
from investmentops.analysis_engines.growth import AGENT_ID, invoke_growth_agent
from investmentops.analysis_engines.prompts import PromptError
from investmentops.analysis_engines.trends import assemble_trend_analysis
from investmentops.data_layer import FinancialStatement, FinancialStatementSeries


def _statement(period_end: date, revenue: float, net_income: float) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=net_income,
        debt=100_000.0,
        source="fmp",
        period_end=period_end,
    )


def _series() -> FinancialStatementSeries:
    return FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_300_000.0, 260_000.0),
            _statement(date(2024, 12, 31), 1_200_000.0, 240_000.0),
        ],
    )


def _config(**overrides: object) -> dict:
    config: dict = {
        "agents": {"growth": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_response(text: str = "Lectura de growth investing.") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


def test_agent_id_is_growth() -> None:
    assert AGENT_ID == "growth"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_returns_ai_provider_response(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    trend_result = assemble_trend_analysis(_series())

    result = invoke_growth_agent(trend_result, config=_config())

    assert isinstance(result, AIProviderResponse)
    assert result.content == "Lectura de growth investing."
    assert result.provider == "anthropic"
    assert mock_post.call_count == 1


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_the_agent_prompt(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    trend_result = assemble_trend_analysis(_series())

    invoke_growth_agent(trend_result, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "growth investing" in message_content.lower()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_trend_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    trend_result = assemble_trend_analysis(_series())

    invoke_growth_agent(trend_result, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "revenue_trend" in message_content
    assert "net_income_trend" in message_content
    assert "revenue_growth_by_period" in message_content
    assert "net_income_growth_by_period" in message_content
    assert "2025-12-31" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_does_not_recalculate_sends_precalculated_values(mock_post: Mock) -> None:
    """Confirma que se envían los valores ya calculados por
    assemble_trend_analysis tal cual, sin volver a derivarlos aquí."""
    mock_post.return_value = _mock_response()
    trend_result = assemble_trend_analysis(_series())

    invoke_growth_agent(trend_result, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "creciente" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_includes_warnings_in_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    single_period_series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[_statement(date(2025, 12, 31), 1_000_000.0, 100_000.0)],
    )
    trend_result = assemble_trend_analysis(single_period_series)

    invoke_growth_agent(trend_result, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "único periodo" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_uses_configured_model(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    trend_result = assemble_trend_analysis(_series())
    config = _config(
        ai_providers={
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        }
    )

    invoke_growth_agent(trend_result, config=config)

    assert mock_post.call_args.kwargs["json"]["model"] == "claude-haiku-4-5"


def test_invoke_raises_when_resolved_provider_is_not_supported() -> None:
    trend_result = assemble_trend_analysis(_series())
    config = _config(
        agents={"growth": "gemini"},
        ai_providers={"default": {"provider": "gemini"}},
    )

    with pytest.raises(AIProviderError, match="No hay una integración concreta"):
        invoke_growth_agent(trend_result, config=config)


def test_invoke_raises_when_no_provider_can_be_resolved() -> None:
    from investmentops.ai_providers.selection import AgentProviderSelectionError

    trend_result = assemble_trend_analysis(_series())
    config: dict = {"agents": {}, "ai_providers": {}}

    with pytest.raises(AgentProviderSelectionError, match="No se pudo resolver"):
        invoke_growth_agent(trend_result, config=config)


def test_invoke_raises_prompt_error_when_prompt_load_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirma que un fallo al cargar el prompt se propaga como `PromptError`."""
    import investmentops.analysis_engines.growth as growth_module

    def _broken_load_prompt(agent_id: str) -> str:
        raise PromptError(f"No se encontró el prompt de '{agent_id}' (simulado).")

    monkeypatch.setattr(growth_module, "load_prompt", _broken_load_prompt)

    trend_result = assemble_trend_analysis(_series())

    with pytest.raises(PromptError, match="simulado"):
        invoke_growth_agent(trend_result, config=_config())