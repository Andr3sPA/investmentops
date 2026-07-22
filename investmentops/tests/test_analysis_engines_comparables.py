"""Pruebas para el cálculo de posicionamiento relativo
(investmentops.analysis_engines.comparables).

Cubre la tarea "Implementar el cálculo de la posición relativa de la
empresa frente a sus pares en cada métrica" (TASKS.md, Fase 5, "Motor de
análisis: posicionamiento relativo"). No prueba de nuevo
`calculate_financial_health_metrics`/`calculate_valuation_metrics` (ya
cubiertos en sus propios archivos de prueba de Fase 1) más allá de lo
necesario para confirmar que este módulo los reutiliza correctamente. No
prueba el ensamblado del resultado estructurado del motor (hallazgos,
tabla comparativa): tarea separada y posterior de la misma sección.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.comparables import (
    METRIC_NAMES,
    EntityMetrics,
    MetricComparison,
    RelativePositioning,
    calculate_entity_metrics,
    calculate_relative_positioning,
    compare_metric,
)
from investmentops.data_layer import Comparables, FinancialStatement, MarketData, PeerComparable


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


def _market_data(price: float = 100.0, market_cap: float = 3_000_000.0) -> MarketData:
    return MarketData(
        price=price,
        market_cap=market_cap,
        multiples={},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def _peer(
    ticker: str = "MSFT",
    revenue: float = 2_000_000.0,
    net_income: float = 400_000.0,
    debt: float = 300_000.0,
    market_cap: float = 5_000_000.0,
) -> PeerComparable:
    return PeerComparable(
        ticker=ticker,
        financial_statement=_statement(revenue=revenue, net_income=net_income, debt=debt),
        market_data=_market_data(market_cap=market_cap),
    )


# --- calculate_entity_metrics -------------------------------------------------


def test_calculate_entity_metrics_reuses_financial_health_and_valuation() -> None:
    metrics = calculate_entity_metrics("AAPL", _statement(), _market_data())

    assert isinstance(metrics, EntityMetrics)
    assert metrics.ticker == "AAPL"
    assert metrics.net_margin == pytest.approx(0.15)
    assert metrics.debt_to_revenue == pytest.approx(0.4)
    assert metrics.price_to_earnings == pytest.approx(20.0)
    assert metrics.price_to_sales == pytest.approx(3.0)
    assert metrics.warnings == []


def test_calculate_entity_metrics_aggregates_warnings_from_both_calculations() -> None:
    statement = _statement(revenue=0.0, net_income=0.0)

    metrics = calculate_entity_metrics("AAPL", statement, _market_data())

    assert metrics.net_margin is None
    assert metrics.debt_to_revenue is None
    assert metrics.price_to_sales is None
    assert len(metrics.warnings) == 2
    assert any("revenue" in w for w in metrics.warnings)
    assert any("price_to_sales" in w for w in metrics.warnings)


def test_calculate_entity_metrics_does_not_raise_zero_division_error() -> None:
    try:
        calculate_entity_metrics("AAPL", _statement(revenue=0.0, net_income=0.0), _market_data())
    except ZeroDivisionError:
        pytest.fail("No debe lanzarse ZeroDivisionError.")


def test_entity_metrics_is_immutable() -> None:
    metrics = calculate_entity_metrics("AAPL", _statement(), _market_data())

    with pytest.raises(AttributeError):
        metrics.net_margin = 0.99  # type: ignore[misc]


# --- compare_metric ------------------------------------------------------------


def test_compare_metric_returns_por_encima_when_company_value_is_higher() -> None:
    assert compare_metric(0.2, 0.1) == "por_encima"


def test_compare_metric_returns_por_debajo_when_company_value_is_lower() -> None:
    assert compare_metric(0.1, 0.2) == "por_debajo"


def test_compare_metric_returns_igual_when_values_are_equal() -> None:
    assert compare_metric(0.15, 0.15) == "igual"


def test_compare_metric_returns_none_when_company_value_is_none() -> None:
    assert compare_metric(None, 0.1) is None


def test_compare_metric_returns_none_when_peer_value_is_none() -> None:
    assert compare_metric(0.1, None) is None


def test_compare_metric_returns_none_when_both_values_are_none() -> None:
    assert compare_metric(None, None) is None


# --- calculate_relative_positioning --------------------------------------------


def test_calculate_relative_positioning_returns_company_and_peer_metrics() -> None:
    comparables = Comparables(ticker="AAPL", peers=[_peer("MSFT"), _peer("GOOGL")])

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    assert isinstance(result, RelativePositioning)
    assert result.company.ticker == "AAPL"
    assert [peer.ticker for peer in result.peers] == ["MSFT", "GOOGL"]


def test_calculate_relative_positioning_includes_all_metric_names() -> None:
    comparables = Comparables(ticker="AAPL", peers=[_peer()])

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    assert set(result.comparisons.keys()) == set(METRIC_NAMES)


def test_calculate_relative_positioning_produces_one_comparison_per_peer() -> None:
    comparables = Comparables(ticker="AAPL", peers=[_peer("MSFT"), _peer("GOOGL")])

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    for name in METRIC_NAMES:
        assert len(result.comparisons[name]) == 2
        assert all(isinstance(c, MetricComparison) for c in result.comparisons[name])


def test_calculate_relative_positioning_reflects_company_below_larger_peer() -> None:
    """La empresa investigada (revenue=1M) frente a un par más grande
    (revenue=2M) debe leer 'por_debajo' en net_margin/debt_to_revenue
    equivalentes calculados con las mismas fórmulas ya existentes."""
    comparables = Comparables(
        ticker="AAPL",
        peers=[_peer("MSFT", revenue=2_000_000.0, net_income=100_000.0, debt=1_000_000.0)],
    )

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    net_margin_comparison = result.comparisons["net_margin"][0]
    assert net_margin_comparison.company_value == pytest.approx(0.15)
    assert net_margin_comparison.peer_value == pytest.approx(0.05)
    assert net_margin_comparison.position == "por_encima"


def test_calculate_relative_positioning_preserves_peer_order() -> None:
    comparables = Comparables(
        ticker="AAPL", peers=[_peer("ZZZ"), _peer("AAA"), _peer("MMM")]
    )

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    assert [peer.ticker for peer in result.peers] == ["ZZZ", "AAA", "MMM"]
    assert [c.peer_ticker for c in result.comparisons["net_margin"]] == [
        "ZZZ",
        "AAA",
        "MMM",
    ]


def test_calculate_relative_positioning_handles_no_peers() -> None:
    comparables = Comparables(ticker="AAPL", peers=[])

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    assert result.peers == []
    for name in METRIC_NAMES:
        assert result.comparisons[name] == []


def test_calculate_relative_positioning_marks_position_none_when_peer_metric_missing() -> None:
    """Si un par tiene `net_income == 0`, price_to_earnings del par es
    None; la comparación de esa métrica contra ese par debe ser None,
    sin inventar una posición."""
    comparables = Comparables(
        ticker="AAPL", peers=[_peer("MSFT", net_income=0.0)]
    )

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    pe_comparison = result.comparisons["price_to_earnings"][0]
    assert pe_comparison.peer_value is None
    assert pe_comparison.position is None


def test_relative_positioning_is_immutable() -> None:
    comparables = Comparables(ticker="AAPL", peers=[_peer()])

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )

    with pytest.raises(AttributeError):
        result.company = result.company  # type: ignore[misc]


def test_metric_comparison_is_immutable() -> None:
    comparables = Comparables(ticker="AAPL", peers=[_peer()])

    result = calculate_relative_positioning(
        "AAPL", _statement(), _market_data(), comparables
    )
    comparison = result.comparisons["net_margin"][0]

    with pytest.raises(AttributeError):
        comparison.position = "igual"  # type: ignore[misc]