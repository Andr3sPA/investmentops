"""Pruebas para el cálculo de variación de ingresos periodo a periodo
(investmentops.analysis_engines.trends.calculate_revenue_growth).

Cubre la tarea "Implementar el cálculo de variación periodo a periodo de
ingresos" (TASKS.md, Fase 3, "Motor de análisis: evolución de ingresos y
beneficios"), sobre la definición ya fijada en
`investmentops/analysis_engines/TREND_METRICS.md`. No prueba la variación
de beneficios (`net_income_growth`), la detección de tendencia agregada
ni el ensamblado del resultado del motor: son tareas separadas y
posteriores de la misma sección.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.trends import (
    SINGLE_PERIOD_WARNING,
    RevenueGrowthPoint,
    RevenueGrowthResult,
    calculate_revenue_growth,
)
from investmentops.data_layer import FinancialStatement, FinancialStatementSeries


def _statement(
    period_end: date, revenue: float, net_income: float = 100_000.0
) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=net_income,
        debt=100_000.0,
        source="fmp",
        period_end=period_end,
    )


def test_calculates_growth_for_two_consecutive_periods() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_100_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert isinstance(result, RevenueGrowthResult)
    assert len(result.points) == 1
    point = result.points[0]
    assert isinstance(point, RevenueGrowthPoint)
    assert point.period_end == date(2025, 12, 31)
    assert point.previous_period_end == date(2024, 12, 31)
    assert point.revenue_growth == pytest.approx(0.1)
    assert point.classification == "creciente"
    assert point.warning is None
    assert result.warnings == ()


def test_produces_one_point_per_consecutive_pair_across_several_periods() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_200_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
            _statement(date(2023, 12, 31), 900_000.0),
            _statement(date(2022, 12, 31), 950_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert len(result.points) == 3
    assert [p.period_end for p in result.points] == [
        date(2025, 12, 31),
        date(2024, 12, 31),
        date(2023, 12, 31),
    ]
    assert [p.previous_period_end for p in result.points] == [
        date(2024, 12, 31),
        date(2023, 12, 31),
        date(2022, 12, 31),
    ]


def test_classifies_growth_as_creciente_when_positive() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_100_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert result.points[0].classification == "creciente"


def test_classifies_growth_as_decreciente_when_negative() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 900_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert result.points[0].revenue_growth == pytest.approx(-0.1)
    assert result.points[0].classification == "decreciente"


def test_classifies_growth_as_estable_when_exactly_zero() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_000_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert result.points[0].revenue_growth == 0.0
    assert result.points[0].classification == "estable"


def test_uses_abs_of_base_period_so_recovering_losses_reads_as_positive() -> None:
    """Ver TREND_METRICS.md: pasar de -100 a -50 debe leerse como mejora
    (crecimiento positivo), no como caída por dividir entre negativo."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), -50.0),
            _statement(date(2024, 12, 31), -100.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert result.points[0].revenue_growth == pytest.approx(0.5)
    assert result.points[0].classification == "creciente"


def test_base_period_revenue_zero_returns_none_with_warning_for_that_point() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 500_000.0),
            _statement(date(2024, 12, 31), 0.0),
        ],
    )

    result = calculate_revenue_growth(series)

    point = result.points[0]
    assert point.revenue_growth is None
    assert point.classification is None
    assert point.warning is not None
    assert "división por cero" in point.warning
    assert result.warnings == ()


def test_does_not_raise_zero_division_error() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 500_000.0),
            _statement(date(2024, 12, 31), 0.0),
        ],
    )

    try:
        calculate_revenue_growth(series)
    except ZeroDivisionError:
        pytest.fail(
            "No debe lanzarse ZeroDivisionError; debe devolver None con "
            "advertencia."
        )


def test_only_the_affected_pair_is_none_others_still_calculated() -> None:
    """Un periodo base en cero solo afecta al salto que lo usa como base;
    los demás saltos de la serie se calculan con normalidad."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2026, 12, 31), 200_000.0),
            _statement(date(2025, 12, 31), 100_000.0),
            _statement(date(2024, 12, 31), 0.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert len(result.points) == 2
    assert result.points[0].revenue_growth == pytest.approx(1.0)
    assert result.points[0].warning is None
    assert result.points[1].revenue_growth is None
    assert result.points[1].warning is not None


def test_single_period_series_returns_no_points_with_series_level_warning() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31), 1_000_000.0)]
    )

    result = calculate_revenue_growth(series)

    assert result.points == ()
    assert result.warnings == (SINGLE_PERIOD_WARNING,)


def test_empty_series_returns_no_points_with_series_level_warning() -> None:
    series = FinancialStatementSeries(ticker="AAPL", statements=[])

    result = calculate_revenue_growth(series)

    assert result.points == ()
    assert result.warnings == (SINGLE_PERIOD_WARNING,)


def test_revenue_growth_point_is_immutable() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_100_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    with pytest.raises(AttributeError):
        result.points[0].revenue_growth = 99.0  # type: ignore[misc]


def test_revenue_growth_result_is_immutable() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31), 1_000_000.0)]
    )

    result = calculate_revenue_growth(series)

    with pytest.raises(AttributeError):
        result.points = ()  # type: ignore[misc]
