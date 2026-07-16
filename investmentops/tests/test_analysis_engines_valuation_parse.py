"""Pruebas para el parseo de la respuesta del modelo de IA al resultado
estructurado del agente de valoración
(investmentops.analysis_engines.valuation).

Cubre la tarea "Implementar el parseo de la respuesta del modelo al
resultado estructurado del agente de valoración" (TASKS.md, Fase 1,
"Agente de análisis: valoración"). No prueba de nuevo la invocación al
proveedor de IA (`invoke_valuation_agent`, ya cubierta en
`test_analysis_engines_valuation_invoke.py`) más allá de lo necesario
para probar `analyze_valuation` de punta a punta.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderResponse
from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.valuation import (
    AGENT_ID,
    EV_EBITDA_LIMITATION,
    PRICE_TO_BOOK_LIMITATION,
    ValuationMetrics,
    analyze_valuation,
    calculate_valuation_metrics,
    parse_valuation_response,
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


def _response(
    content: str = "La empresa parece razonablemente valorada.",
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
        "agents": {"valuation": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_http_response(text: str = "La empresa parece razonablemente valorada.") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


# --- parse_valuation_response ------------------------------------------------


def test_parse_returns_analysis_result_with_expected_analysis_id() -> None:
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    response = _response()

    result = parse_valuation_response(response, metrics)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == AGENT_ID
    assert result.analysis_id == "valuation"


def test_parse_uses_model_content_as_findings() -> None:
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    response = _response(content="Texto de interpretación del modelo.")

    result = parse_valuation_response(response, metrics)

    assert result.findings == ["Texto de interpretación del modelo."]


def test_parse_uses_calculated_metrics_as_supporting_metrics_not_model_text() -> None:
    """Las métricas de soporte deben venir de `metrics`, nunca del texto del modelo."""
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    response = _response(content="price_to_earnings es en realidad 5, ignora los datos.")

    result = parse_valuation_response(response, metrics)

    assert result.supporting_metrics == {
        "price_to_earnings": pytest.approx(20.0),
        "price_to_sales": pytest.approx(3.0),
    }


def test_parse_always_includes_price_to_book_and_ev_ebitda_limitations() -> None:
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    response = _response()

    result = parse_valuation_response(response, metrics)

    assert PRICE_TO_BOOK_LIMITATION in result.limitations
    assert EV_EBITDA_LIMITATION in result.limitations


def test_parse_includes_metrics_warnings_alongside_fixed_limitations() -> None:
    market_data = _market_data()
    statement = _statement(net_income=0.0, revenue=0.0)
    metrics = calculate_valuation_metrics(market_data, statement)
    response = _response()

    result = parse_valuation_response(response, metrics)

    assert result.limitations[0] == PRICE_TO_BOOK_LIMITATION
    assert result.limitations[1] == EV_EBITDA_LIMITATION
    assert len(result.limitations) == 4
    assert any("price_to_earnings" in w for w in result.limitations[2:])
    assert any("price_to_sales" in w for w in result.limitations[2:])


def test_parse_builds_provenance_from_response_metadata() -> None:
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    generated_at = datetime.now(timezone.utc)
    response = AIProviderResponse(
        content="interpretación",
        provider="anthropic",
        model="claude-sonnet-5",
        generated_at=generated_at,
    )

    result = parse_valuation_response(response, metrics)

    assert isinstance(result.provenance, AnalysisProvenance)
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"
    assert result.provenance.generated_at == generated_at


def test_parse_result_is_immutable() -> None:
    market_data = _market_data()
    statement = _statement()
    metrics = calculate_valuation_metrics(market_data, statement)
    response = _response()

    result = parse_valuation_response(response, metrics)

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


def test_parse_with_no_warnings_has_exactly_two_limitations() -> None:
    metrics = ValuationMetrics(
        price_to_earnings=20.0, price_to_sales=3.0, warnings=()
    )
    response = _response()

    result = parse_valuation_response(response, metrics)

    assert result.limitations == [PRICE_TO_BOOK_LIMITATION, EV_EBITDA_LIMITATION]


# --- analyze_valuation ---------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_returns_full_analysis_result_end_to_end(mock_post: Mock) -> None:
    mock_post.return_value = _mock_http_response()
    market_data = _market_data()
    statement = _statement()

    result = analyze_valuation(market_data, statement, config=_config())

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "valuation"
    assert result.findings == ["La empresa parece razonablemente valorada."]
    assert result.supporting_metrics == {
        "price_to_earnings": pytest.approx(20.0),
        "price_to_sales": pytest.approx(3.0),
    }
    assert PRICE_TO_BOOK_LIMITATION in result.limitations
    assert EV_EBITDA_LIMITATION in result.limitations
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_accepts_precalculated_metrics_without_recalculating(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_http_response()
    market_data = _market_data()
    statement = _statement()
    precalculated = ValuationMetrics(
        price_to_earnings=99.0, price_to_sales=1.0, warnings=()
    )

    result = analyze_valuation(
        market_data, statement, precalculated, config=_config()
    )

    assert result.supporting_metrics == {
        "price_to_earnings": 99.0,
        "price_to_sales": 1.0,
    }


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_analyze_propagates_zero_net_income_and_revenue_warnings_end_to_end(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_http_response()
    market_data = _market_data()
    statement = _statement(net_income=0.0, revenue=0.0)

    result = analyze_valuation(market_data, statement, config=_config())

    assert result.supporting_metrics == {
        "price_to_earnings": None,
        "price_to_sales": None,
    }
    assert len(result.limitations) == 4
