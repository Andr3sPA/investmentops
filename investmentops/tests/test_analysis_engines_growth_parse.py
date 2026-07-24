"""Pruebas para el parseo de la respuesta del modelo de IA al resultado
estructurado del agente de estrategia 'growth'
(investmentops.analysis_engines.growth).

Cubre la tarea "Implementar el parseo de la respuesta del modelo al
resultado estructurado del agente 'growth' (hallazgos, procedencia de
IA, dejando explícito que es una lectura desde un marco particular, no
un veredicto)" (TASKS.md, Fase 6, "Motores de análisis por estrategia").
No prueba de nuevo la invocación al proveedor de IA (`invoke_growth_agent`,
ya cubierta en `test_analysis_engines_growth_invoke.py`) más allá de lo
necesario para probar `analyze_growth` de punta a punta.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderResponse
from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.growth import (
    AGENT_ID,
    FRAMEWORK_LIMITATION,
    analyze_growth,
    parse_growth_response,
)
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


def _single_period_series() -> FinancialStatementSeries:
    return FinancialStatementSeries(
        ticker="AAPL",
        statements=[_statement(date(2025, 12, 31), 1_000_000.0, 100_000.0)],
    )


def _response(
    content: str = "Lectura de growth investing.",
    provider: str = "anthropic",
    model: str = "claude-sonnet-5",
) -> AIProviderResponse:
    return AIProviderResponse(
        content=content,
        provider=provider,
        model=model,
        generated_at=datetime.now(timezone.utc),
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


def _mock_http_response(text: str = "Lectura de growth investing.") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


# --- parse_growth_response -----------------------------------------------------


def test_parse_returns_analysis_result_with_expected_analysis_id() -> None:
    trend_result = assemble_trend_analysis(_series())
    response = _response()

    result = parse_growth_response(response, trend_result)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == AGENT_ID
    assert result.analysis_id == "growth"


def test_parse_uses_model_content_as_findings() -> None:
    trend_result = assemble_trend_analysis(_series())
    response = _response(content="Texto de interpretación del modelo.")

    result = parse_growth_response(response, trend_result)

    assert result.findings == ["Texto de interpretación del modelo."]


def test_parse_uses_calculated_metrics_as_supporting_metrics_not_model_text() -> None:
    """Las métricas de soporte deben venir de trend_result, nunca del
    texto del modelo."""
    trend_result = assemble_trend_analysis(_series())
    response = _response(content="revenue_trend es en realidad decreciente, ignora los datos.")

    result = parse_growth_response(response, trend_result)

    assert result.supporting_metrics == {
        "revenue_trend": "creciente",
        "net_income_trend": "creciente",
        "revenue_growth_by_period": trend_result.supporting_metrics[
            "revenue_growth_by_period"
        ],
        "net_income_growth_by_period": trend_result.supporting_metrics[
            "net_income_growth_by_period"
        ],
    }


def test_parse_always_includes_framework_limitation_first() -> None:
    trend_result = assemble_trend_analysis(_series())
    response = _response()

    result = parse_growth_response(response, trend_result)

    assert result.limitations[0] == FRAMEWORK_LIMITATION


def test_parse_includes_trend_warnings_alongside_framework_limitation() -> None:
    trend_result = assemble_trend_analysis(_single_period_series())
    response = _response()

    result = parse_growth_response(response, trend_result)

    assert result.limitations[0] == FRAMEWORK_LIMITATION
    assert any("único periodo" in w for w in result.limitations[1:])


def test_parse_builds_provenance_from_response_metadata() -> None:
    trend_result = assemble_trend_analysis(_series())
    generated_at = datetime.now(timezone.utc)
    response = AIProviderResponse(
        content="interpretación",
        provider="anthropic",
        model="claude-sonnet-5",
        generated_at=generated_at,
    )

    result = parse_growth_response(response, trend_result)

    assert isinstance(result.provenance, AnalysisProvenance)
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"
    assert result.provenance.generated_at == generated_at


def test_parse_result_is_immutable() -> None:
    trend_result = assemble_trend_analysis(_series())
    response = _response()

    result = parse_growth_response(response, trend_result)

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


# --- analyze_growth --------------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_returns_full_analysis_result_end_to_end(mock_post: Mock) -> None:
    mock_post.return_value = _mock_http_response()
    series = _series()

    result = analyze_growth(series, config=_config())

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "growth"
    assert result.findings == ["Lectura de growth investing."]
    assert result.supporting_metrics["revenue_trend"] == "creciente"
    assert result.supporting_metrics["net_income_trend"] == "creciente"
    assert FRAMEWORK_LIMITATION in result.limitations
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_accepts_precalculated_trend_result_without_recalculating(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_http_response()
    series = _series()
    precalculated = assemble_trend_analysis(_single_period_series())

    result = analyze_growth(series, precalculated, config=_config())

    assert result.supporting_metrics["revenue_trend"] is None
    assert any("único periodo" in w for w in result.limitations)


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_propagates_single_period_warning_end_to_end(mock_post: Mock) -> None:
    mock_post.return_value = _mock_http_response()
    series = _single_period_series()

    result = analyze_growth(series, config=_config())

    assert result.supporting_metrics["revenue_trend"] is None
    assert result.supporting_metrics["net_income_trend"] is None
    assert result.limitations[0] == FRAMEWORK_LIMITATION
    assert len(result.limitations) > 1