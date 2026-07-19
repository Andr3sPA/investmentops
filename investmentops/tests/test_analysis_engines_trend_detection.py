"""Pruebas para la detección simple de tendencia agregada por serie
(investmentops.analysis_engines.trends.detect_revenue_trend /
detect_net_income_trend).

Cubre la tarea "Implementar la detección simple de tendencia (creciente,
decreciente, estable) para cada serie" (TASKS.md, Fase 3, "Motor de
análisis: evolución de ingresos y beneficios"), sobre la definición ya
fijada en `investmentops/analysis_engines/TREND_METRICS.md`. No prueba de
nuevo `calculate_revenue_growth`/`calculate_net_income_growth` (ya
cubiertos en `test_analysis_engines_trends.py`/
`test_analysis_engines_trends_net_income.py`): construye directamente los
`RevenueGrowthResult`/`NetIncomeGrowthResult` de entrada. No prueba el
ensamblado del resultado estructurado del motor (hallazgos, métricas de
soporte, advertencias por huecos): tarea separada y posterior de la misma
sección.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.trends import (
    NO_NET_INCOME_TREND_WARNING,
    NO_REVENUE_TREND_WARNING,
    NetIncomeGrowthPoint,
    NetIncomeGrowthResult,
    RevenueGrowthPoint,
    RevenueGrowthResult,
    SeriesTrend,
    detect_net_income_trend,
    detect_revenue_trend,
)


def _revenue_point(
    classification: str | None,
    period_end: date = date(2025, 12, 31),
    previous_period_end: date = date(2024, 12, 31),
    revenue_growth: float | None = 0.1,
    warning: str | None = None,
) -> RevenueGrowthPoint:
    return RevenueGrowthPoint(
        period_end=period_end,
        previous_period_end=previous_period_end,
        revenue_growth=revenue_growth,
        classification=classification,
        warning=warning,
    )


def _net_income_point(
    classification: str | None,
    period_end: date = date(2025, 12, 31),
    previous_period_end: date = date(2024, 12, 31),
    net_income_growth: float | None = 0.1,
    warning: str | None = None,
) -> NetIncomeGrowthPoint:
    return NetIncomeGrowthPoint(
        period_end=period_end,
        previous_period_end=previous_period_end,
        net_income_growth=net_income_growth,
        classification=classification,
        warning=warning,
    )


# --- detect_revenue_trend ----------------------------------------------------


def test_detects_consistently_creciente_trend() -> None:
    result = RevenueGrowthResult(
        points=(
            _revenue_point("creciente"),
            _revenue_point("creciente"),
            _revenue_point("creciente"),
        ),
        warnings=(),
    )

    trend = detect_revenue_trend(result)

    assert isinstance(trend, SeriesTrend)
    assert trend.trend == "creciente"
    assert trend.warning is None


def test_detects_consistently_decreciente_trend() -> None:
    result = RevenueGrowthResult(
        points=(
            _revenue_point("decreciente"),
            _revenue_point("decreciente"),
        ),
        warnings=(),
    )

    trend = detect_revenue_trend(result)

    assert trend.trend == "decreciente"
    assert trend.warning is None


def test_detects_consistently_estable_trend() -> None:
    result = RevenueGrowthResult(
        points=(
            _revenue_point("estable"),
            _revenue_point("estable"),
        ),
        warnings=(),
    )

    trend = detect_revenue_trend(result)

    assert trend.trend == "estable"
    assert trend.warning is None


def test_detects_mixed_trend_when_classifications_differ() -> None:
    result = RevenueGrowthResult(
        points=(
            _revenue_point("creciente"),
            _revenue_point("decreciente"),
            _revenue_point("creciente"),
        ),
        warnings=(),
    )

    trend = detect_revenue_trend(result)

    assert trend.trend == "mixta"
    assert trend.warning is None


def test_single_point_series_uses_that_point_classification() -> None:
    result = RevenueGrowthResult(points=(_revenue_point("creciente"),), warnings=())

    trend = detect_revenue_trend(result)

    assert trend.trend == "creciente"


def test_ignores_degenerate_points_without_classification() -> None:
    """Un salto con periodo base en 0 (classification=None) no debe romper
    una tendencia por lo demás consistente."""
    result = RevenueGrowthResult(
        points=(
            _revenue_point("creciente"),
            _revenue_point(None, revenue_growth=None, warning="división por cero"),
            _revenue_point("creciente"),
        ),
        warnings=(),
    )

    trend = detect_revenue_trend(result)

    assert trend.trend == "creciente"
    assert trend.warning is None


def test_returns_none_with_warning_when_no_points_at_all() -> None:
    """Serie de un solo periodo o vacía: `points == ()`."""
    result = RevenueGrowthResult(points=(), warnings=("La serie tiene un único periodo",))

    trend = detect_revenue_trend(result)

    assert trend.trend is None
    assert trend.warning == NO_REVENUE_TREND_WARNING


def test_returns_none_with_warning_when_all_points_are_degenerate() -> None:
    result = RevenueGrowthResult(
        points=(
            _revenue_point(None, revenue_growth=None, warning="división por cero"),
            _revenue_point(None, revenue_growth=None, warning="división por cero"),
        ),
        warnings=(),
    )

    trend = detect_revenue_trend(result)

    assert trend.trend is None
    assert trend.warning == NO_REVENUE_TREND_WARNING


def test_series_trend_is_immutable() -> None:
    result = RevenueGrowthResult(points=(_revenue_point("creciente"),), warnings=())

    trend = detect_revenue_trend(result)

    with pytest.raises(AttributeError):
        trend.trend = "decreciente"  # type: ignore[misc]


# --- detect_net_income_trend --------------------------------------------------


def test_detects_consistently_creciente_trend_for_net_income() -> None:
    result = NetIncomeGrowthResult(
        points=(
            _net_income_point("creciente"),
            _net_income_point("creciente"),
        ),
        warnings=(),
    )

    trend = detect_net_income_trend(result)

    assert trend.trend == "creciente"
    assert trend.warning is None


def test_detects_mixed_trend_for_net_income() -> None:
    result = NetIncomeGrowthResult(
        points=(
            _net_income_point("estable"),
            _net_income_point("decreciente"),
        ),
        warnings=(),
    )

    trend = detect_net_income_trend(result)

    assert trend.trend == "mixta"


def test_ignores_degenerate_points_for_net_income() -> None:
    result = NetIncomeGrowthResult(
        points=(
            _net_income_point("decreciente"),
            _net_income_point(None, net_income_growth=None, warning="división por cero"),
            _net_income_point("decreciente"),
        ),
        warnings=(),
    )

    trend = detect_net_income_trend(result)

    assert trend.trend == "decreciente"
    assert trend.warning is None


def test_returns_none_with_warning_when_no_points_for_net_income() -> None:
    result = NetIncomeGrowthResult(points=(), warnings=("La serie tiene un único periodo",))

    trend = detect_net_income_trend(result)

    assert trend.trend is None
    assert trend.warning == NO_NET_INCOME_TREND_WARNING


def test_returns_none_with_warning_when_all_points_degenerate_for_net_income() -> None:
    result = NetIncomeGrowthResult(
        points=(
            _net_income_point(None, net_income_growth=None, warning="división por cero"),
        ),
        warnings=(),
    )

    trend = detect_net_income_trend(result)

    assert trend.trend is None
    assert trend.warning == NO_NET_INCOME_TREND_WARNING


def test_net_income_and_revenue_warnings_are_distinct_messages() -> None:
    """Confirma que cada métrica tiene su propio texto de advertencia,
    no un mensaje genérico compartido que confunda ingresos con beneficios."""
    assert NO_REVENUE_TREND_WARNING != NO_NET_INCOME_TREND_WARNING
    assert "ingresos" in NO_REVENUE_TREND_WARNING
    assert "beneficios" in NO_NET_INCOME_TREND_WARNING
