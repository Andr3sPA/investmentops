"""Pruebas para la transformación de la respuesta cruda histórica de FMP
al modelo de dominio "Serie de estados financieros normalizados"
(investmentops.data_layer.normalization.financial_statement_series_from_raw).

Cubre la tarea "Implementar la transformación de la respuesta cruda
histórica al modelo de series temporales" (TASKS.md, Fase 3,
"Normalización"). No prueba de nuevo `financial_statement_from_raw` ni
`market_data_from_raw` (corte único, ya cubiertos en
`test_data_layer_normalization.py`), ni la consulta real a FMP
(`fetch_historical`, ya cubierta en
`test_data_providers_fundamentals_historical.py` y
`test_data_providers_fundamentals_historical_provenance.py`): usa
payloads con la misma forma que ya produce `fetch_historical`, incluyendo
`"source"`/`"queried_at"` por punto.
"""

from datetime import date, datetime, timezone

import pytest

from investmentops.data_layer import FinancialStatement, FinancialStatementSeries
from investmentops.data_layer.normalization import (
    NormalizationError,
    financial_statement_series_from_raw,
)
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


def _raw_historical_data(payload: dict, source: str = "fmp") -> RawProviderData:
    return RawProviderData(
        ticker="AAPL",
        payload=payload,
        metadata=ProviderMetadata(
            source=source,
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        ),
    )


def _income_point(
    period_end: str, revenue: float, net_income: float, source: str = "fmp"
) -> dict:
    return {
        "date": period_end,
        "revenue": revenue,
        "netIncome": net_income,
        "source": source,
        "queried_at": "2026-07-17T00:00:00+00:00",
    }


def _balance_point(period_end: str, debt: float, source: str = "fmp") -> dict:
    return {
        "date": period_end,
        "totalDebt": debt,
        "source": source,
        "queried_at": "2026-07-17T00:00:00+00:00",
    }


def test_builds_series_with_one_statement_per_income_period() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                _income_point("2025-12-31", 1_000_000.0, 150_000.0),
                _income_point("2024-12-31", 900_000.0, 120_000.0),
                _income_point("2023-12-31", 800_000.0, 100_000.0),
            ],
            "balance_sheet_statement": [
                _balance_point("2025-12-31", 400_000.0),
                _balance_point("2024-12-31", 350_000.0),
                _balance_point("2023-12-31", 300_000.0),
            ],
        }
    )

    series = financial_statement_series_from_raw(raw)

    assert isinstance(series, FinancialStatementSeries)
    assert series.ticker == "AAPL"
    assert len(series.statements) == 3
    assert all(isinstance(s, FinancialStatement) for s in series.statements)


def test_preserves_order_from_income_statement() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                _income_point("2025-12-31", 1_000_000.0, 150_000.0),
                _income_point("2024-12-31", 900_000.0, 120_000.0),
            ],
            "balance_sheet_statement": [
                _balance_point("2024-12-31", 350_000.0),
                _balance_point("2025-12-31", 400_000.0),
            ],
        }
    )

    series = financial_statement_series_from_raw(raw)

    assert [s.period_end for s in series.statements] == [
        date(2025, 12, 31),
        date(2024, 12, 31),
    ]


def test_matches_balance_sheet_by_date_not_by_position() -> None:
    """Las listas no vienen alineadas por índice: balance_sheet_statement
    trae los periodos en un orden distinto al de income_statement."""
    raw = _raw_historical_data(
        {
            "income_statement": [
                _income_point("2025-12-31", 1_000_000.0, 150_000.0),
                _income_point("2024-12-31", 900_000.0, 120_000.0),
            ],
            "balance_sheet_statement": [
                _balance_point("2024-12-31", 350_000.0),
                _balance_point("2025-12-31", 400_000.0),
            ],
        }
    )

    series = financial_statement_series_from_raw(raw)

    latest, older = series.statements
    assert latest.period_end == date(2025, 12, 31)
    assert latest.debt == 400_000.0
    assert older.period_end == date(2024, 12, 31)
    assert older.debt == 350_000.0


def test_each_statement_keeps_its_own_values() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                _income_point("2025-12-31", 1_000_000.0, 150_000.0),
                _income_point("2024-12-31", 900_000.0, 120_000.0),
            ],
            "balance_sheet_statement": [
                _balance_point("2025-12-31", 400_000.0),
                _balance_point("2024-12-31", 350_000.0),
            ],
        }
    )

    series = financial_statement_series_from_raw(raw)

    latest, older = series.statements
    assert latest.revenue == 1_000_000.0
    assert latest.net_income == 150_000.0
    assert older.revenue == 900_000.0
    assert older.net_income == 120_000.0


def test_uses_source_from_each_point_not_a_fixed_value() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                _income_point("2025-12-31", 1_000_000.0, 150_000.0, source="example_provider"),
            ],
            "balance_sheet_statement": [
                _balance_point("2025-12-31", 400_000.0, source="example_provider"),
            ],
        },
        source="example_provider",
    )

    series = financial_statement_series_from_raw(raw)

    assert series.statements[0].source == "example_provider"


def test_falls_back_to_metadata_source_when_point_has_no_source() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0},
            ],
            "balance_sheet_statement": [
                _balance_point("2025-12-31", 400_000.0),
            ],
        },
        source="fmp",
    )

    series = financial_statement_series_from_raw(raw)

    assert series.statements[0].source == "fmp"


def test_raises_when_income_statement_missing() -> None:
    raw = _raw_historical_data({"income_statement": [], "balance_sheet_statement": []})

    with pytest.raises(NormalizationError, match="income_statement"):
        financial_statement_series_from_raw(raw)


def test_raises_when_debt_missing_for_a_specific_period() -> None:
    """Si un periodo de income_statement no tiene su balance_sheet_statement
    correspondiente, debe señalarse ese periodo específico, no omitirlo."""
    raw = _raw_historical_data(
        {
            "income_statement": [
                _income_point("2025-12-31", 1_000_000.0, 150_000.0),
                _income_point("2024-12-31", 900_000.0, 120_000.0),
            ],
            "balance_sheet_statement": [
                _balance_point("2025-12-31", 400_000.0),
                # Falta el balance de 2024-12-31.
            ],
        }
    )

    with pytest.raises(NormalizationError, match="2024-12-31"):
        financial_statement_series_from_raw(raw)


def test_raises_when_date_missing_for_a_period() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                {"revenue": 1_000_000.0, "netIncome": 150_000.0, "source": "fmp"},
            ],
            "balance_sheet_statement": [],
        }
    )

    with pytest.raises(NormalizationError, match="period_end"):
        financial_statement_series_from_raw(raw)


def test_raises_when_date_is_invalid() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [
                {
                    "date": "not-a-date",
                    "revenue": 1_000_000.0,
                    "netIncome": 150_000.0,
                    "source": "fmp",
                },
            ],
            "balance_sheet_statement": [
                _balance_point("not-a-date", 400_000.0),
            ],
        }
    )

    with pytest.raises(NormalizationError, match="formato reconocible"):
        financial_statement_series_from_raw(raw)


def test_supports_a_single_historical_period() -> None:
    raw = _raw_historical_data(
        {
            "income_statement": [_income_point("2025-12-31", 1_000_000.0, 150_000.0)],
            "balance_sheet_statement": [_balance_point("2025-12-31", 400_000.0)],
        }
    )

    series = financial_statement_series_from_raw(raw)

    assert len(series.statements) == 1
    assert series.statements[0].period_end == date(2025, 12, 31)
