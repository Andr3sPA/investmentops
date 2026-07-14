"""Pruebas para la transformación de datos crudos de FMP al modelo
"Estados financieros normalizados" (investmentops.data_layer.normalization).

Cubre la tarea "Implementar la transformación de datos crudos del
proveedor al modelo 'Estados financieros normalizados'" (TASKS.md, Fase
1, "Normalización y almacenamiento"). No prueba la transformación al
modelo "Datos de mercado" (`MarketData`) ni el cacheo de datos
normalizados: esas son tareas separadas y posteriores (ver TASKS.md).
"""

from datetime import date, datetime, timezone

import pytest

from investmentops.data_layer import FinancialStatement
from investmentops.data_layer.normalization import (
    NormalizationError,
    financial_statement_from_raw,
)
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


def _raw_data(payload: dict, source: str = "fmp") -> RawProviderData:
    return RawProviderData(
        ticker="AAPL",
        payload=payload,
        metadata=ProviderMetadata(
            source=source,
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        ),
    )


def test_financial_statement_from_raw_builds_statement_from_latest_period() -> None:
    raw = _raw_data(
        {
            "income_statement": [
                {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0},
                {"date": "2024-12-31", "revenue": 900_000.0, "netIncome": 120_000.0},
            ],
            "balance_sheet_statement": [
                {"date": "2025-12-31", "totalDebt": 400_000.0},
            ],
            "quote": [{"price": 185.5}],
        }
    )

    statement = financial_statement_from_raw(raw)

    assert isinstance(statement, FinancialStatement)
    assert statement.revenue == 1_000_000.0
    assert statement.net_income == 150_000.0
    assert statement.debt == 400_000.0
    assert statement.source == "fmp"
    assert statement.period_end == date(2025, 12, 31)


def test_financial_statement_from_raw_uses_provider_metadata_source() -> None:
    """El `source` del modelo debe venir de la procedencia, no de un valor fijo."""
    raw = _raw_data(
        {
            "income_statement": [
                {"date": "2025-06-30", "revenue": 500_000.0, "netIncome": -50_000.0}
            ],
            "balance_sheet_statement": [{"date": "2025-06-30", "totalDebt": 300_000.0}],
        },
        source="example_provider",
    )

    statement = financial_statement_from_raw(raw)

    assert statement.source == "example_provider"
    assert statement.net_income == -50_000.0


def test_financial_statement_from_raw_raises_when_income_statement_missing() -> None:
    raw = _raw_data({"income_statement": [], "balance_sheet_statement": []})

    with pytest.raises(NormalizationError, match="income_statement"):
        financial_statement_from_raw(raw)


def test_financial_statement_from_raw_raises_when_debt_is_missing() -> None:
    raw = _raw_data(
        {
            "income_statement": [
                {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
            ],
            "balance_sheet_statement": [],
        }
    )

    with pytest.raises(NormalizationError, match="debt"):
        financial_statement_from_raw(raw)


def test_financial_statement_from_raw_raises_when_date_is_missing() -> None:
    raw = _raw_data(
        {
            "income_statement": [{"revenue": 1_000_000.0, "netIncome": 150_000.0}],
            "balance_sheet_statement": [{"totalDebt": 400_000.0}],
        }
    )

    with pytest.raises(NormalizationError, match="period_end"):
        financial_statement_from_raw(raw)


def test_financial_statement_from_raw_raises_when_date_is_invalid() -> None:
    raw = _raw_data(
        {
            "income_statement": [
                {"date": "not-a-date", "revenue": 1_000_000.0, "netIncome": 150_000.0}
            ],
            "balance_sheet_statement": [{"totalDebt": 400_000.0}],
        }
    )

    with pytest.raises(NormalizationError, match="formato reconocible"):
        financial_statement_from_raw(raw)


def test_normalization_error_is_a_runtime_error() -> None:
    assert issubclass(NormalizationError, RuntimeError)
