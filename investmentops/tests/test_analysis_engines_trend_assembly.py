"""Pruebas para el ensamblado del resultado estructurado del motor de
evolución de ingresos y beneficios
(investmentops.analysis_engines.trends.assemble_trend_analysis).

Cubre la tarea "Ensamblar el resultado estructurado del motor (hallazgos,
métricas de soporte, advertencias si hay huecos en la serie)" (TASKS.md,
Fase 3, "Motor de análisis: evolución de ingresos y beneficios"). No
prueba de nuevo `calculate_revenue_growth`/`calculate_net_income_growth`
(ya cubiertos en `test_analysis_engines_trends.py`/
`test_analysis_engines_trends_net_income.py`) ni
`detect_revenue_trend`/`detect_net_income_trend` (ya cubiertos en
`test_analysis_engines_trend_detection.py`) más allá de lo necesario para
confirmar que `assemble_trend_analysis` los encadena correctamente.
"""

from datetime import date

import pytest

from investmentops.analysis_engines.trends import (
    AGENT_ID,
    NET_INCOME_SINGLE_PERIOD_WARNING,
    NO_NET_INCOME_TREND_WARNING,
    NO_REVENUE_TREND_WARNING,
    SINGLE_PERIOD_WARNING,
    TrendAnalysisResult,
    assemble_trend_analysis,
)
from investmentops.data_layer import FinancialStatement, FinancialStatementSeries


def _statement(
    period_end: date, revenue: float, net_income: float
) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=net_income,
        debt=100_000.0,
        source="fmp",
        period_end=period_end,
    )


def _annual_growing_series() -> FinancialStatementSeries:
    """Serie anual, regular (365/366 días), consistentemente creciente."""
    return FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_300_000.0, 260_000.0),
            _statement(date(2024, 12, 31), 1_200_000.0, 240_000.0),
            _statement(date(2023, 12, 31), 1_100_000.0, 220_000.0),
            _statement(date(2022, 12, 31), 1_000_000.0, 200_000.0),
        ],
    )


# --- Estructura básica del resultado -----------------------------------------


def test_returns_trend_analysis_result_with_expected_analysis_id() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    assert isinstance(result, TrendAnalysisResult)
    assert result.analysis_id == AGENT_ID
    assert result.analysis_id == "trend_analysis"


def test_result_is_immutable() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


# --- Hallazgos -----------------------------------------------------------------


def test_findings_include_one_entry_for_revenue_and_one_for_net_income() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    assert len(result.findings) == 2
    assert any("ingresos" in finding for finding in result.findings)
    assert any("beneficios" in finding for finding in result.findings)


def test_findings_describe_growing_trend_for_consistently_growing_series() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    assert any("creciente" in finding for finding in result.findings)


def test_findings_indicate_missing_data_for_single_period_series() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31), 1_000_000.0, 100_000.0)]
    )

    result = assemble_trend_analysis(series)

    assert all("No hay suficientes datos" in finding for finding in result.findings)


# --- Métricas de soporte --------------------------------------------------------


def test_supporting_metrics_include_aggregate_trends() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    assert result.supporting_metrics["revenue_trend"] == "creciente"
    assert result.supporting_metrics["net_income_trend"] == "creciente"


def test_supporting_metrics_include_growth_by_period_keyed_by_iso_date() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    revenue_by_period = result.supporting_metrics["revenue_growth_by_period"]
    net_income_by_period = result.supporting_metrics["net_income_growth_by_period"]

    assert "2025-12-31" in revenue_by_period
    assert "2025-12-31" in net_income_by_period
    assert revenue_by_period["2025-12-31"] == pytest.approx(1_300_000.0 / 1_200_000.0 - 1)
    assert net_income_by_period["2025-12-31"] == pytest.approx(260_000.0 / 240_000.0 - 1)
    assert len(revenue_by_period) == 3
    assert len(net_income_by_period) == 3


def test_supporting_metrics_growth_by_period_is_empty_for_single_period_series() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31), 1_000_000.0, 100_000.0)]
    )

    result = assemble_trend_analysis(series)

    assert result.supporting_metrics["revenue_growth_by_period"] == {}
    assert result.supporting_metrics["net_income_growth_by_period"] == {}
    assert result.supporting_metrics["revenue_trend"] is None
    assert result.supporting_metrics["net_income_trend"] is None


# --- Advertencias / limitaciones ------------------------------------------------


def test_limitations_include_single_period_warnings_for_short_series() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31), 1_000_000.0, 100_000.0)]
    )

    result = assemble_trend_analysis(series)

    assert SINGLE_PERIOD_WARNING in result.limitations
    assert NET_INCOME_SINGLE_PERIOD_WARNING in result.limitations
    assert NO_REVENUE_TREND_WARNING in result.limitations
    assert NO_NET_INCOME_TREND_WARNING in result.limitations


def test_limitations_include_per_point_warnings_for_zero_base_period() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 500_000.0, 50_000.0),
            _statement(date(2024, 12, 31), 0.0, 0.0),
        ],
    )

    result = assemble_trend_analysis(series)

    assert any("revenue_growth" in warning for warning in result.limitations)
    assert any("net_income_growth" in warning for warning in result.limitations)


def test_limitations_are_empty_for_a_clean_consistent_series() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    assert result.limitations == []


# --- Detección de huecos ---------------------------------------------------------


def test_no_gap_warnings_for_regular_annual_series() -> None:
    result = assemble_trend_analysis(_annual_growing_series())

    assert not any("hueco irregular" in warning for warning in result.limitations)


def test_gap_warning_for_irregular_interval_in_otherwise_regular_series() -> None:
    """Serie mayormente anual, con un salto de dos años en vez de uno."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_300_000.0, 260_000.0),
            _statement(date(2024, 12, 31), 1_200_000.0, 240_000.0),
            # Falta el periodo de 2023-12-31: salto de 2 años en vez de 1.
            _statement(date(2022, 12, 31), 1_000_000.0, 200_000.0),
        ],
    )

    result = assemble_trend_analysis(series)

    gap_warnings = [w for w in result.limitations if "hueco irregular" in w]
    assert len(gap_warnings) == 1
    assert "2024-12-31" in gap_warnings[0]
    assert "2022-12-31" in gap_warnings[0]


def test_no_gap_detection_attempted_for_series_with_fewer_than_three_periods() -> None:
    """Con menos de 3 periodos no hay base para estimar periodicidad
    esperada; no debe reportarse ninguna advertencia de huecos."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_300_000.0, 260_000.0),
            _statement(date(2020, 12, 31), 900_000.0, 150_000.0),
        ],
    )

    result = assemble_trend_analysis(series)

    assert not any("hueco irregular" in warning for warning in result.limitations)


def test_gap_warning_for_duplicated_or_out_of_order_period() -> None:
    """Un salto con brecha cero o negativa siempre se marca como hueco,
    independientemente de la mediana de la serie."""
    series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            _statement(date(2025, 12, 31), 1_300_000.0, 260_000.0),
            _statement(date(2025, 12, 31), 1_250_000.0, 250_000.0),
            _statement(date(2023, 12, 31), 1_100_000.0, 220_000.0),
        ],
    )

    result = assemble_trend_analysis(series)

    gap_warnings = [w for w in result.limitations if "hueco irregular" in w]
    assert len(gap_warnings) == 1
    assert "brecha de 0 días" in gap_warnings[0]
