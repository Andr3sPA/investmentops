"""Pruebas para la invocación al proveedor de IA del agente de salud
financiera (investmentops.analysis_engines.financial_health.invoke_financial_health_agent).

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
con esas métricas + el prompt" (TASKS.md, Fase 1, "Agente de análisis:
salud financiera"). No prueba el parseo de la respuesta del modelo a la
estructura final del agente (`AnalysisResult`): eso es una tarea separada
y posterior. Como `invoke_financial_health_agent` termina invocando a
`AnthropicAIProvider.complete`, todas las pruebas mockean
`requests.post` en vez de depender de una llamada de red real.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderError, AIProviderResponse
from investmentops.analysis_engines.financial_health import (
    calculate_financial_health_metrics,
    invoke_financial_health_agent,
)
from investmentops.analysis_engines.prompts import PromptError
from investmentops.data_layer import FinancialStatement


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


def _config(**overrides: object) -> dict:
    config: dict = {
        "agents": {"financial_health": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_response(text: str = "La empresa muestra un margen saludable.") -> Mock:
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
    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)

    result = invoke_financial_health_agent(statement, metrics, config=_config())

    assert isinstance(result, AIProviderResponse)
    assert result.content == "La empresa muestra un margen saludable."
    assert result.provider == "anthropic"
    assert mock_post.call_count == 1


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_the_agent_prompt(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)

    invoke_financial_health_agent(statement, metrics, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "salud financiera" in message_content.lower()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_sends_statement_and_metrics_as_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)

    invoke_financial_health_agent(statement, metrics, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "net_margin" in message_content
    assert "debt_to_revenue" in message_content
    assert "revenue" in message_content
    assert "period_end" in message_content
    assert "2025-12-31" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_includes_zero_revenue_warning_in_data(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    statement = _statement(revenue=0.0, net_income=0.0, debt=100_000.0)
    metrics = calculate_financial_health_metrics(statement)

    invoke_financial_health_agent(statement, metrics, config=_config())

    message_content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "división por cero" in message_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_invoke_uses_configured_model(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response()
    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)
    config = _config(
        ai_providers={
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        }
    )

    invoke_financial_health_agent(statement, metrics, config=config)

    assert mock_post.call_args.kwargs["json"]["model"] == "claude-haiku-4-5"


def test_invoke_raises_when_resolved_provider_is_not_supported() -> None:
    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)
    config = _config(
        agents={"financial_health": "gemini"},
        ai_providers={"default": {"provider": "gemini"}},
    )

    with pytest.raises(AIProviderError, match="No hay una integración concreta"):
        invoke_financial_health_agent(statement, metrics, config=config)


def test_invoke_raises_when_no_provider_can_be_resolved() -> None:
    from investmentops.ai_providers.selection import AgentProviderSelectionError

    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)
    config: dict = {"agents": {}, "ai_providers": {}}

    with pytest.raises(AgentProviderSelectionError, match="No se pudo resolver"):
        invoke_financial_health_agent(statement, metrics, config=config)


def test_invoke_raises_prompt_error_when_prompts_dir_has_no_financial_health_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirma que un fallo al cargar el prompt se propaga como `PromptError`
    y no como una excepción genérica, aunque la resolución de proveedor y
    la construcción del `AIProvider` ocurran después en el flujo normal."""
    import investmentops.analysis_engines.financial_health as fh_module

    def _broken_load_prompt(agent_id: str) -> str:
        raise PromptError(f"No se encontró el prompt de '{agent_id}' (simulado).")

    monkeypatch.setattr(fh_module, "load_prompt", _broken_load_prompt)

    statement = _statement()
    metrics = calculate_financial_health_metrics(statement)

    with pytest.raises(PromptError, match="simulado"):
        invoke_financial_health_agent(statement, metrics, config=_config())
