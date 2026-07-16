"""Pruebas para el paso de datos crudos a la capa de normalización en el
orquestador (investmentops.core.orchestrator.fetch_normalized_data).

Cubre la tarea "Implementar el paso de datos crudos a la capa de
normalización" (TASKS.md, Fase 1, "Orquestador mínimo"). No prueba de
nuevo `fetch_raw_data` en detalle (ya cubierto en
`test_core_orchestrator.py`) más allá de lo necesario para confirmar el
encadenado; tampoco prueba invocación de agentes de análisis, ensamblado
de `ResearchResult`, ni manejo de fallos parciales: esas son tareas
separadas y posteriores de la misma sección.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.core.orchestrator import fetch_normalized_data
from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_layer.normalization import NormalizationError
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que devuelve un payload con forma de FMP."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.received_ticker: str | None = None

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_ticker = ticker
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingProvider:
    """Proveedor mínimo de prueba que señala un fallo mediante el contrato."""

    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"Ticker '{ticker}' no encontrado")


def _valid_payload() -> dict:
    return {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
        "quote": [
            {
                "price": 185.5,
                "marketCap": 2_900_000_000_000.0,
                "timestamp": 1735689600,  # 2025-01-01T00:00:00Z
            }
        ],
    }


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def test_fetch_normalized_data_uses_injected_provider() -> None:
    provider = _DummyProvider(_valid_payload())

    statement, market_data = fetch_normalized_data("AAPL", provider=provider)

    assert provider.received_ticker == "AAPL"
    assert isinstance(statement, FinancialStatement)
    assert isinstance(market_data, MarketData)


def test_fetch_normalized_data_builds_financial_statement_from_raw() -> None:
    provider = _DummyProvider(_valid_payload())

    statement, _ = fetch_normalized_data("AAPL", provider=provider)

    assert statement.revenue == 1_000_000.0
    assert statement.net_income == 150_000.0
    assert statement.debt == 400_000.0
    assert statement.source == "dummy_provider"
    assert statement.period_end == date(2025, 12, 31)


def test_fetch_normalized_data_builds_market_data_from_raw() -> None:
    provider = _DummyProvider(_valid_payload())

    _, market_data = fetch_normalized_data("AAPL", provider=provider)

    assert market_data.price == 185.5
    assert market_data.market_cap == 2_900_000_000_000.0
    assert market_data.multiples == {}
    assert market_data.source == "dummy_provider"
    assert market_data.as_of == date(2025, 1, 1)


def test_fetch_normalized_data_propagates_provider_failure() -> None:
    with pytest.raises(DataProviderError, match="no encontrado"):
        fetch_normalized_data("NOPE", provider=_FailingProvider())


def test_fetch_normalized_data_propagates_normalization_error_when_fields_missing() -> None:
    incomplete_payload = {
        "income_statement": [],
        "balance_sheet_statement": [],
        "quote": [],
    }
    provider = _DummyProvider(incomplete_payload)

    with pytest.raises(NormalizationError, match="income_statement"):
        fetch_normalized_data("AAPL", provider=provider)


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_normalized_data_defaults_to_fmp_provider(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(
            [{"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}]
        ),
        _mock_response([{"date": "2025-12-31", "totalDebt": 400_000.0}]),
        _mock_response(
            [{"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}]
        ),
    ]
    config = {"data_providers": {"fundamentals": {"api_key": "fake-key"}}}

    statement, market_data = fetch_normalized_data("AAPL", config=config)

    assert statement.source == "fmp"
    assert market_data.source == "fmp"
    assert mock_get.call_count == 3
