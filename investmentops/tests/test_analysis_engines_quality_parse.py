"""Pruebas para el parseo de la respuesta del modelo de IA al resultado
estructurado del agente de estrategia 'calidad'
(investmentops.analysis_engines.quality).

Cubre la tarea "Implementar el parseo de la respuesta del modelo al
resultado estructurado del agente 'calidad' (hallazgos, procedencia de
IA, dejando explícito que es una lectura desde un marco particular, no
un veredicto)" (TASKS.md, Fase 6, "Motores de análisis por estrategia").
No prueba de nuevo la invocación al proveedor de IA
(`invoke_quality_agent`, ya cubierta previamente) más allá de lo
necesario para probar `analyze_quality` de punta a punta. Mismo patrón
de pruebas ya usado en `test_analysis_engines_value_parse.py`/
`test_analysis_engines_growth_parse.py`.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderResponse
from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.financial_health import (
    FinancialHealthMetrics,
    calculate_financial_health_metrics,
)
from investmentops.analysis_engines.quality import (
    AGENT_ID,
    FRAMEWORK_LIMITATION,
    analyze_quality,
    parse_quality_response,
)
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


def _response(
    content: str = "Lectura de quality investing.",
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
        "agents": {"quality": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_http_response(text: str = "Lectura de quality investing.") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


# --- parse_quality_response -----------------------------------------------------


def test_parse_returns_analysis_result_with_expected_analysis_id() -> None:
    statement = _statement()
    health_metrics = calculate_financial_health_metrics(statement)
    response = _response()

    result = parse_quality_response(response, health_metrics)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == AGENT_ID
    assert result.analysis_id == "quality"


def test_parse_uses_model_content_as_findings() -> None:
    statement = _statement()
    health_metrics = calculate_financial_health_metrics(statement)
    response = _response(content="Texto de interpretación del modelo.")

    result = parse_quality_response(response, health_metrics)

    assert result.findings == ["Texto de interpretación del modelo."]


def test_parse_uses_calculated_metrics_as_supporting_metrics_not_model_text() -> None:
    """Las métricas de soporte deben venir de health_metrics, nunca del
    texto del modelo."""
    statement = _statement()
    health_metrics = calculate_financial_health_metrics(statement)
    response = _response(content="net_margin es en realidad 0.99, ignora los datos.")

    result = parse_quality_response(response, health_metrics)

    assert result.supporting_metrics == {
        "net_margin": pytest.approx(0.15),
        "debt_to_revenue": pytest.approx(0.4),
    }


def test_parse_always_includes_framework_limitation_first() -> None:
    statement = _statement()
    health_metrics = calculate_financial_health_metrics(statement)
    response = _response()

    result = parse_quality_response(response, health_metrics)

    assert result.limitations[0] == FRAMEWORK_LIMITATION


def test_parse_includes_metrics_warnings_alongside_framework_limitation() -> None:
    statement = _statement(revenue=0.0, net_income=0.0)
    health_metrics = calculate_financial_health_metrics(statement)
    response = _response()

    result = parse_quality_response(response, health_metrics)

    assert result.limitations[0] == FRAMEWORK_LIMITATION
    assert any("división por cero" in w for w in result.limitations[1:])


def test_parse_builds_provenance_from_response_metadata() -> None:
    statement = _statement()
    health_metrics = calculate_financial_health_metrics(statement)
    generated_at = datetime.now(timezone.utc)
    response = AIProviderResponse(
        content="interpretación",
        provider="anthropic",
        model="claude-sonnet-5",
        generated_at=generated_at,
    )

    result = parse_quality_response(response, health_metrics)

    assert isinstance(result.provenance, AnalysisProvenance)
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"
    assert result.provenance.generated_at == generated_at


def test_parse_result_is_immutable() -> None:
    statement = _statement()
    health_metrics = calculate_financial_health_metrics(statement)
    response = _response()

    result = parse_quality_response(response, health_metrics)

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


def test_parse_with_no_warnings_has_a_single_limitation() -> None:
    health_metrics = FinancialHealthMetrics(
        net_margin=0.15, debt_to_revenue=0.4, warnings=()
    )
    response = _response()

    result = parse_quality_response(response, health_metrics)

    assert result.limitations == [FRAMEWORK_LIMITATION]


# --- analyze_quality ---------------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_returns_full_analysis_result_end_to_end(mock_post: Mock) -> None:
    mock_post.return_value = _mock_http_response()
    statement = _statement()

    result = analyze_quality(statement, config=_config())

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "quality"
    assert result.findings == ["Lectura de quality investing."]
    assert result.supporting_metrics == {
        "net_margin": pytest.approx(0.15),
        "debt_to_revenue": pytest.approx(0.4),
    }
    assert FRAMEWORK_LIMITATION in result.limitations
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_accepts_precalculated_metrics_without_recalculating(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_http_response()
    statement = _statement()
    precalculated = FinancialHealthMetrics(
        net_margin=0.99, debt_to_revenue=0.01, warnings=()
    )

    result = analyze_quality(statement, precalculated, config=_config())

    assert result.supporting_metrics == {
        "net_margin": 0.99,
        "debt_to_revenue": 0.01,
    }


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_propagates_zero_revenue_warning_end_to_end(mock_post: Mock) -> None:
    mock_post.return_value = _mock_http_response()
    statement = _statement(revenue=0.0, net_income=0.0, debt=50_000.0)

    result = analyze_quality(statement, config=_config())

    assert result.supporting_metrics == {"net_margin": None, "debt_to_revenue": None}
    assert result.limitations[0] == FRAMEWORK_LIMITATION
    assert len(result.limitations) > 1