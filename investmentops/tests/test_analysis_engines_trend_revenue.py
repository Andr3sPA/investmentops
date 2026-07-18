"""Pruebas para el cálculo determinístico de variación periodo a periodo
de ingresos (investmentops.analysis_engines.trend.calculate_revenue_growth).

Cubre la tarea "Implementar el cálculo de variación periodo a periodo de
ingresos" (TASKS.md, Fase 3, "Motor de análisis: evolución de ingresos y
beneficios"), siguiendo la definición ya fijada en
`investmentops/analysis_engines/TREND_METRICS.md`. No prueba variación de
beneficios, clasificación de tendencia, ni el ensamblado del resultado
estructurado del motor: esas son tareas separadas y posteriores de la
misma sección.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.trend import (
    PeriodGrowth,
    RevenueGrowthResult,
    calculate_revenue_growth,
)
from investmentops.data_layer import FinancialStatement, FinancialStatementSeries


def _statement(period_end: date, revenue: float) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=100_000.0,
        debt=400_000.0,
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
    assert len(result.values) == 1
    assert result.values[0] == PeriodGrowth(
        period_end=date(2025, 12, 31),
        previous_period_end=date(2024, 12, 31),
        growth=pytest.approx(0.1),
    )
    assert result.warnings == ()


def test_calculates_one_growth_value_per_consecutive_pair() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_200_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
            _statement(date(2023, 12, 31), 800_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert len(result.values) == 2
    assert result.values[0].growth == pytest.approx(0.2)
    assert result.values[1].growth == pytest.approx(0.25)
    assert result.warnings == ()


def test_handles_negative_base_period_with_correct_sign() -> None:
    """Usa abs() en el denominador: una mejora desde un periodo negativo
    debe reflejarse con un signo positivo."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), -50_000.0),
            _statement(date(2024, 12, 31), -100_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    # (-50000 - -100000) / abs(-100000) = 50000 / 100000 = 0.5 (mejora)
    assert result.values[0].growth == pytest.approx(0.5)


def test_zero_base_revenue_returns_none_growth_with_warning() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 500_000.0),
            _statement(date(2024, 12, 31), 0.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert result.values[0].growth is None
    assert len(result.warnings) == 1
    assert "2024-12-31" in result.warnings[0]
    assert "2025-12-31" in result.warnings[0]
    assert "división por cero" in result.warnings[0]


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


def test_single_period_series_returns_empty_values_with_warning() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31), 1_000_000.0)]
    )

    result = calculate_revenue_growth(series)

    assert result.values == ()
    assert len(result.warnings) == 1
    assert "menos de dos periodos" in result.warnings[0]


def test_multiple_zero_base_gaps_each_produce_their_own_warning() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 500_000.0),
            _statement(date(2024, 12, 31), 0.0),
            _statement(date(2023, 12, 31), 0.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert len(result.values) == 2
    assert result.values[0].growth is None
    assert result.values[1].growth is None
    assert len(result.warnings) == 2


def test_period_growth_is_immutable() -> None:
    growth = PeriodGrowth(
        period_end=date(2025, 12, 31),
        previous_period_end=date(2024, 12, 31),
        growth=0.1,
    )

    with pytest.raises(AttributeError):
        growth.growth = 0.99  # type: ignore[misc]


def test_revenue_growth_result_preserves_series_order() -> None:
    """El primer elemento de `values` corresponde al salto más reciente,
    mismo orden que la propia serie de entrada."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_200_000.0),
            _statement(date(2024, 12, 31), 1_000_000.0),
            _statement(date(2023, 12, 31), 800_000.0),
        ],
    )

    result = calculate_revenue_growth(series)

    assert result.values[0].period_end == date(2025, 12, 31)
    assert result.values[0].previous_period_end == date(2024, 12, 31)
    assert result.values[1].period_end == date(2024, 12, 31)
    assert result.values[1].previous_period_end == date(2023, 12, 31)
