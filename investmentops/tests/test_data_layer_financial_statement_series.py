"""Pruebas para el modelo de dominio "Serie de estados financieros
normalizados" (investmentops.data_layer.FinancialStatementSeries).

Cubre la tarea "Extender el modelo 'Estados financieros normalizados'
para incluir series temporales (no solo el dato más reciente)"
(TASKS.md, Fase 3, "Normalización"). No prueba la transformación desde
datos crudos históricos (`fetch_historical`) ni el cacheo de series:
esas son tareas separadas y posteriores de la misma sección.
"""

from datetime import date

import pytest

from investmentops.data_layer import FinancialStatement, FinancialStatementSeries


def _statement(period_end: date, revenue: float = 1_000_000.0) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=period_end,
    )


def test_series_holds_ticker_and_ordered_statements() -> None:
    latest = _statement(date(2025, 12, 31))
    older = _statement(date(2024, 12, 31), revenue=900_000.0)

    series = FinancialStatementSeries(ticker="AAPL", statements=[latest, older])

    assert series.ticker == "AAPL"
    assert series.statements == [latest, older]
    assert series.statements[0].period_end == date(2025, 12, 31)
    assert series.statements[1].period_end == date(2024, 12, 31)


def test_series_is_immutable() -> None:
    series = FinancialStatementSeries(
        ticker="AAPL", statements=[_statement(date(2025, 12, 31))]
    )

    with pytest.raises(AttributeError):
        series.ticker = "MSFT"  # type: ignore[misc]


def test_series_supports_a_single_statement() -> None:
    """No se exige un mínimo de periodos: una serie de un solo punto es válida."""
    statement = _statement(date(2025, 12, 31))

    series = FinancialStatementSeries(ticker="AAPL", statements=[statement])

    assert len(series.statements) == 1


def test_series_supports_multiple_statements_in_given_order() -> None:
    """Confirma que el orden (más reciente primero, como ya devuelve FMP)
    se preserva tal cual se entregue, sin reordenar ni validar."""
    points = [
        _statement(date(2025, 12, 31)),
        _statement(date(2024, 12, 31)),
        _statement(date(2023, 12, 31)),
    ]

    series = FinancialStatementSeries(ticker="AAPL", statements=points)

    assert [s.period_end for s in series.statements] == [
        date(2025, 12, 31),
        date(2024, 12, 31),
        date(2023, 12, 31),
    ]


def test_series_preserves_source_of_each_point() -> None:
    """El `source` de cada punto se conserva vía `FinancialStatement.source`,
    sin necesidad de un campo de procedencia adicional en la serie."""
    points = [
        _statement(date(2025, 12, 31)),
        _statement(date(2024, 12, 31)),
    ]

    series = FinancialStatementSeries(ticker="AAPL", statements=points)

    assert all(statement.source == "fmp" for statement in series.statements)
