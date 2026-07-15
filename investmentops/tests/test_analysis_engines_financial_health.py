"""Pruebas para el cálculo determinístico de métricas de salud financiera
(investmentops.analysis_engines.financial_health).

Cubre la tarea "Implementar el cálculo determinístico de ratios de
liquidez, endeudamiento y rentabilidad a partir del modelo normalizado"
(TASKS.md, Fase 1, "Agente de análisis: salud financiera"). No prueba
liquidez (fuera de alcance, ver
`investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`), ni la
invocación al proveedor de IA ni el parseo del resultado del agente: esas
son tareas separadas y posteriores.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.financial_health import (
    FinancialHealthMetrics,
    calculate_financial_health_metrics,
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


def test_calculates_net_margin_and_debt_to_revenue() -> None:
    metrics = calculate_financial_health_metrics(_statement())

    assert isinstance(metrics, FinancialHealthMetrics)
    assert metrics.net_margin == pytest.approx(0.15)
    assert metrics.debt_to_revenue == pytest.approx(0.4)
    assert metrics.warnings == ()


def test_supports_negative_net_income() -> None:
    """Una empresa con pérdidas debe reflejarse en un net_margin negativo."""
    metrics = calculate_financial_health_metrics(
        _statement(revenue=500_000.0, net_income=-50_000.0, debt=300_000.0)
    )

    assert metrics.net_margin == pytest.approx(-0.1)
    assert metrics.debt_to_revenue == pytest.approx(0.6)
    assert metrics.warnings == ()


def test_zero_revenue_returns_none_ratios_with_warning() -> None:
    metrics = calculate_financial_health_metrics(
        _statement(revenue=0.0, net_income=0.0, debt=100_000.0)
    )

    assert metrics.net_margin is None
    assert metrics.debt_to_revenue is None
    assert len(metrics.warnings) == 1
    assert "revenue" in metrics.warnings[0]
    assert "división por cero" in metrics.warnings[0]


def test_zero_revenue_does_not_raise_zero_division_error() -> None:
    """El manejo de revenue == 0 nunca debe dejar escapar ZeroDivisionError."""
    try:
        calculate_financial_health_metrics(_statement(revenue=0.0))
    except ZeroDivisionError:
        pytest.fail("No debe lanzarse ZeroDivisionError; debe devolver None con advertencia.")


def test_financial_health_metrics_is_immutable() -> None:
    metrics = calculate_financial_health_metrics(_statement())

    with pytest.raises(AttributeError):
        metrics.net_margin = 0.99  # type: ignore[misc]


def test_zero_debt_gives_zero_debt_to_revenue() -> None:
    """Una empresa sin deuda debe reflejarse con un ratio de 0, no None."""
    metrics = calculate_financial_health_metrics(
        _statement(revenue=1_000_000.0, net_income=100_000.0, debt=0.0)
    )

    assert metrics.debt_to_revenue == 0.0
    assert metrics.warnings == ()
