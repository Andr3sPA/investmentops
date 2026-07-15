"""Pruebas para la transformación de datos crudos de FMP a los modelos
"Estados financieros normalizados" y "Datos de mercado"
(investmentops.data_layer.normalization).

Cubre las tareas "Implementar la transformación de datos crudos del
proveedor al modelo 'Estados financieros normalizados'" e "Implementar la
transformación de datos crudos al modelo 'Datos de mercado'" (TASKS.md,
Fase 1, "Normalización y almacenamiento"). No prueba el cacheo de datos
normalizados: esa es una tarea separada y posterior (ver TASKS.md).
"""

from datetime import date, datetime, timezone

import pytest

from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_layer.normalization import (
    NormalizationError,
    financial_statement_from_raw,
    market_data_from_raw,
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


# --- financial_statement_from_raw ------------------------------------------


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


# --- market_data_from_raw ---------------------------------------------------


def test_market_data_from_raw_builds_market_data_from_latest_quote() -> None:
    raw = _raw_data(
        {
            "quote": [
                {
                    "price": 185.5,
                    "marketCap": 2_900_000_000_000.0,
                    "timestamp": 1735689600,  # 2025-01-01T00:00:00Z
                },
                {
                    "price": 180.0,
                    "marketCap": 2_800_000_000_000.0,
                    "timestamp": 1703980800,  # cotización anterior, no debe usarse
                },
            ],
        }
    )

    market_data = market_data_from_raw(raw)

    assert isinstance(market_data, MarketData)
    assert market_data.price == 185.5
    assert market_data.market_cap == 2_900_000_000_000.0
    assert market_data.multiples == {}
    assert market_data.source == "fmp"
    assert market_data.as_of == date(2025, 1, 1)


def test_market_data_from_raw_uses_provider_metadata_source() -> None:
    """El `source` del modelo debe venir de la procedencia, no de un valor fijo."""
    raw = _raw_data(
        {
            "quote": [
                {"price": 42.0, "marketCap": 1_000_000.0, "timestamp": 1735689600}
            ]
        },
        source="example_provider",
    )

    market_data = market_data_from_raw(raw)

    assert market_data.source == "example_provider"


def test_market_data_from_raw_leaves_multiples_empty() -> None:
    """El cálculo de múltiplos es responsabilidad del agente de valoración."""
    raw = _raw_data(
        {
            "quote": [
                {"price": 42.0, "marketCap": 1_000_000.0, "timestamp": 1735689600}
            ]
        }
    )

    market_data = market_data_from_raw(raw)

    assert market_data.multiples == {}


def test_market_data_from_raw_raises_when_quote_missing() -> None:
    raw = _raw_data({"quote": []})

    with pytest.raises(NormalizationError, match="quote"):
        market_data_from_raw(raw)


def test_market_data_from_raw_raises_when_price_is_missing() -> None:
    raw = _raw_data({"quote": [{"marketCap": 1_000_000.0, "timestamp": 1735689600}]})

    with pytest.raises(NormalizationError, match="price"):
        market_data_from_raw(raw)


def test_market_data_from_raw_raises_when_market_cap_is_missing() -> None:
    raw = _raw_data({"quote": [{"price": 42.0, "timestamp": 1735689600}]})

    with pytest.raises(NormalizationError, match="market_cap"):
        market_data_from_raw(raw)


def test_market_data_from_raw_raises_when_timestamp_is_missing() -> None:
    raw = _raw_data({"quote": [{"price": 42.0, "marketCap": 1_000_000.0}]})

    with pytest.raises(NormalizationError, match="as_of"):
        market_data_from_raw(raw)


def test_market_data_from_raw_raises_when_timestamp_is_invalid() -> None:
    raw = _raw_data(
        {
            "quote": [
                {
                    "price": 42.0,
                    "marketCap": 1_000_000.0,
                    "timestamp": "not-a-timestamp",
                }
            ]
        }
    )

    with pytest.raises(NormalizationError, match="formato reconocible"):
        market_data_from_raw(raw)


def test_normalization_error_is_a_runtime_error() -> None:
    assert issubclass(NormalizationError, RuntimeError)
