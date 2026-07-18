"""Pruebas para el cálculo determinístico de variación periodo a periodo
de ingresos (investmentops.analysis_engines.trend.calculate_revenue_growth).

Cubre la tarea "Implementar el cálculo de variación periodo a periodo de
ingresos" (TASKS.md, Fase 3, "Motor de análisis: evolución de ingresos y
beneficios"). No prueba variación de beneficios, clasificación de
tendencia, ni el ensamblado del resultado estructurado del motor: esas
son tareas separadas y posteriores de la misma sección (ver
`investmentops/analysis_engines/TREND_METRICS.md`).
"""

from datetime import date

import pytest

from investmentops.analysis_engines.trend import (
    PeriodRevenueGrowth,
    calculate_revenue_growth,
)
from investmentops.data_layer import FinancialStatement, FinancialStatementSeries


def _statement(
    period_end: date,
    revenue: float,
    net_income: float = 100_000.0,
    debt: float = 50_000.0,
) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=net_income,
        debt=debt,
        source="fmp",
        period_end=period_end,
    )


def test_calculates_growth_for_two_consecutive_periods() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=1_100_000.0),
            _statement(date(2024, 12, 31), revenue=1_000_000.0),
        ],
    )

    results = calculate_revenue_growth(series)

    assert len(results) == 1
    assert isinstance(results[0], PeriodRevenueGrowth)
    assert results[0].period_end == date(2025, 12, 31)
    assert results[0].previous_period_end == date(2024, 12, 31)
    assert results[0].revenue_growth == pytest.approx(0.1)
    assert results[0].warning is None


def test_calculates_negative_growth_for_declining_revenue() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=800_000.0),
            _statement(date(2024, 12, 31), revenue=1_000_000.0),
        ],
    )

    results = calculate_revenue_growth(series)

    assert results[0].revenue_growth == pytest.approx(-0.2)


def test_produces_one_result_per_consecutive_pair_for_longer_series() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=1_200_000.0),
            _statement(date(2024, 12, 31), revenue=1_000_000.0),
            _statement(date(2023, 12, 31), revenue=900_000.0),
            _statement(date(2022, 12, 31), revenue=800_000.0),
        ],
    )

    results = calculate_revenue_growth(series)

    assert len(results) == 3
    assert [r.period_end for r in results] == [
        date(2025, 12, 31),
        date(2024, 12, 31),
        date(2023, 12, 31),
    ]
    assert [r.previous_period_end for r in results] == [
        date(2024, 12, 31),
        date(2023, 12, 31),
        date(2022, 12, 31),
    ]


def test_uses_absolute_value_of_base_period_when_negative() -> None:
    """Un periodo base negativo que mejora (menos pérdida) debe dar un
    resultado positivo, no negativo por dividir entre un número negativo."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=-50_000.0),
            _statement(date(2024, 12, 31), revenue=-100_000.0),
        ],
    )

    results = calculate_revenue_growth(series)

    # (-50000 - -100000) / abs(-100000) = 50000 / 100000 = 0.5
    assert results[0].revenue_growth == pytest.approx(0.5)


def test_zero_base_revenue_returns_none_with_warning() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=500_000.0),
            _statement(date(2024, 12, 31), revenue=0.0),
        ],
    )

    results = calculate_revenue_growth(series)

    assert results[0].revenue_growth is None
    assert results[0].warning is not None
    assert "2024-12-31" in results[0].warning
    assert "división por cero" in results[0].warning


def test_zero_base_revenue_does_not_raise_zero_division_error() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=500_000.0),
            _statement(date(2024, 12, 31), revenue=0.0),
        ],
    )

    try:
        calculate_revenue_growth(series)
    except ZeroDivisionError:
        pytest.fail(
            "No debe lanzarse ZeroDivisionError; debe devolver None con "
            "advertencia."
        )


def test_only_the_degenerate_pair_gets_a_warning_in_a_longer_series() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=1_000_000.0),
            _statement(date(2024, 12, 31), revenue=0.0),
            _statement(date(2023, 12, 31), revenue=900_000.0),
        ],
    )

    results = calculate_revenue_growth(series)

    assert results[0].revenue_growth is None
    assert results[0].warning is not None
    assert results[1].revenue_growth == pytest.approx(0.0)
    assert results[1].warning is None


def test_returns_empty_list_for_series_with_single_statement() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[_statement(date(2025, 12, 31), revenue=1_000_000.0)],
    )

    results = calculate_revenue_growth(series)

    assert results == []


def test_returns_empty_list_for_series_with_no_statements() -> None:
    series = FinancialStatementSeries(ticker="AAPL", statements=[])

    results = calculate_revenue_growth(series)

    assert results == []


def test_period_revenue_growth_is_immutable() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), revenue=1_100_000.0),
            _statement(date(2024, 12, 31), revenue=1_000_000.0),
        ],
    )

    result = calculate_revenue_growth(series)[0]

    with pytest.raises(AttributeError):
        result.revenue_growth = 0.99  # type: ignore[misc]
