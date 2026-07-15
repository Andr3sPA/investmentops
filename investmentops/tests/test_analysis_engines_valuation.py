"""Pruebas para el cálculo determinístico de múltiplos de valoración
(investmentops.analysis_engines.valuation).

Cubre la tarea "Implementar el cálculo determinístico de esos múltiplos a
partir del modelo normalizado" (TASKS.md, Fase 1, "Agente de análisis:
valoración"). No prueba P/B ni EV/EBITDA (fuera de alcance, ver
`investmentops/analysis_engines/VALUATION_METRICS.md`), ni la invocación
al proveedor de IA ni el parseo del resultado del agente: esas son
tareas separadas y posteriores.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.valuation import (
    ValuationMetrics,
    calculate_valuation_metrics,
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


def test_calculates_price_to_earnings_and_price_to_sales() -> None:
    metrics = calculate_valuation_metrics(_market_data(), _statement())

    assert isinstance(metrics, ValuationMetrics)
    assert metrics.price_to_earnings == pytest.approx(20.0)  # 3_000_000 / 150_000
    assert metrics.price_to_sales == pytest.approx(3.0)  # 3_000_000 / 1_000_000
    assert metrics.warnings == ()


def test_zero_net_income_returns_none_pe_with_warning() -> None:
    metrics = calculate_valuation_metrics(
        _market_data(), _statement(net_income=0.0)
    )

    assert metrics.price_to_earnings is None
    assert metrics.price_to_sales is not None
    assert len(metrics.warnings) == 1
    assert "price_to_earnings" in metrics.warnings[0]


def test_negative_net_income_returns_none_pe_with_warning() -> None:
    metrics = calculate_valuation_metrics(
        _market_data(), _statement(net_income=-50_000.0)
    )

    assert metrics.price_to_earnings is None
    assert len(metrics.warnings) == 1
    assert "price_to_earnings" in metrics.warnings[0]


def test_zero_revenue_returns_none_ps_with_warning() -> None:
    metrics = calculate_valuation_metrics(
        _market_data(), _statement(revenue=0.0, net_income=100_000.0)
    )

    assert metrics.price_to_sales is None
    assert metrics.price_to_earnings is not None
    assert len(metrics.warnings) == 1
    assert "price_to_sales" in metrics.warnings[0]


def test_both_metrics_uncalculable_produces_two_warnings() -> None:
    metrics = calculate_valuation_metrics(
        _market_data(), _statement(revenue=0.0, net_income=0.0)
    )

    assert metrics.price_to_earnings is None
    assert metrics.price_to_sales is None
    assert len(metrics.warnings) == 2
    assert any("price_to_earnings" in w for w in metrics.warnings)
    assert any("price_to_sales" in w for w in metrics.warnings)


def test_does_not_raise_zero_division_error() -> None:
    """El manejo de casos degenerados nunca debe dejar escapar ZeroDivisionError."""
    try:
        calculate_valuation_metrics(
            _market_data(), _statement(revenue=0.0, net_income=0.0)
        )
    except ZeroDivisionError:
        pytest.fail(
            "No debe lanzarse ZeroDivisionError; debe devolver None con "
            "advertencia."
        )


def test_valuation_metrics_is_immutable() -> None:
    metrics = calculate_valuation_metrics(_market_data(), _statement())

    with pytest.raises(AttributeError):
        metrics.price_to_earnings = 99.0  # type: ignore[misc]


def test_with_no_warnings_has_empty_warnings_tuple() -> None:
    metrics = calculate_valuation_metrics(_market_data(), _statement())

    assert metrics.warnings == ()
