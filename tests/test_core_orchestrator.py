"""Pruebas para el orquestador mínimo (investmentops.core.orchestrator):
`fetch_raw_data` (disparo de la consulta al proveedor de datos) y
`fetch_and_normalize` (paso de esos datos crudos a la capa de
normalización).

Cubre las tareas "Implementar la función que recibe un ticker y dispara
la consulta al proveedor de Fase 1" e "Implementar el paso de datos
crudos a la capa de normalización" (TASKS.md, Fase 1, "Orquestador
mínimo"). No prueba la invocación de los agentes de análisis, el
ensamblado en `ResearchResult` ni el manejo de fallos parciales: esas son
tareas separadas y posteriores de la misma sección.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.core.orchestrator import (
    NormalizedCompanyData,
    fetch_and_normalize,
    fetch_raw_data,
)
from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_layer.normalization import NormalizationError
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que cumple el contrato `DataProvider`."""

    def __init__(self, payload: dict | None = None) -> None:
        self.received_ticker: str | None = None
        self._payload = payload if payload is not None else {"revenue": 1000}

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


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def _complete_payload() -> dict:
    return {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
        "quote": [
            {"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}
        ],
    }


# --- fetch_raw_data ----------------------------------------------------------


def test_fetch_raw_data_uses_injected_provider() -> None:
    provider = _DummyProvider()

    result = fetch_raw_data("AAPL", provider=provider)

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert provider.received_ticker == "AAPL"


def test_fetch_raw_data_propagates_provider_failure() -> None:
    with pytest.raises(DataProviderError, match="no encontrado"):
        fetch_raw_data("NOPE", provider=_FailingProvider())


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raw_data_defaults_to_fmp_provider(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response([{"revenue": 1000, "netIncome": 100}]),
        _mock_response([{"totalDebt": 500}]),
        _mock_response([{"price": 150.0, "marketCap": 2_000_000}]),
    ]
    config = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
    }

    result = fetch_raw_data("AAPL", config=config)

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert result.metadata.source == "fmp"
    assert mock_get.call_count == 3


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raw_data_propagates_fmp_failure_for_missing_ticker(
    mock_get: Mock,
) -> None:
    mock_get.side_effect = [
        _mock_response([]),
        _mock_response([]),
        _mock_response([]),
    ]
    config = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
    }

    with pytest.raises(DataProviderError, match="no existe"):
        fetch_raw_data("NOPE", config=config)


# --- fetch_and_normalize -------------------------------------------------------


def test_fetch_and_normalize_returns_normalized_company_data() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    result = fetch_and_normalize("AAPL", provider=provider)

    assert isinstance(result, NormalizedCompanyData)
    assert isinstance(result.financial_statement, FinancialStatement)
    assert isinstance(result.market_data, MarketData)


def test_fetch_and_normalize_builds_financial_statement_from_raw_payload() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    result = fetch_and_normalize("AAPL", provider=provider)

    assert result.financial_statement.revenue == 1_000_000.0
    assert result.financial_statement.net_income == 150_000.0
    assert result.financial_statement.debt == 400_000.0
    assert result.financial_statement.source == "dummy_provider"
    assert result.financial_statement.period_end == date(2025, 12, 31)


def test_fetch_and_normalize_builds_market_data_from_raw_payload() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    result = fetch_and_normalize("AAPL", provider=provider)

    assert result.market_data.price == 185.5
    assert result.market_data.market_cap == 2_900_000_000_000.0
    assert result.market_data.multiples == {}
    assert result.market_data.source == "dummy_provider"
    assert result.market_data.as_of == date(2025, 1, 1)


def test_fetch_and_normalize_passes_ticker_to_provider() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    fetch_and_normalize("AAPL", provider=provider)

    assert provider.received_ticker == "AAPL"


def test_fetch_and_normalize_propagates_data_provider_error() -> None:
    with pytest.raises(DataProviderError, match="no encontrado"):
        fetch_and_normalize("NOPE", provider=_FailingProvider())


def test_fetch_and_normalize_propagates_normalization_error_on_incomplete_payload() -> None:
    """Un payload crudo sin balance_sheet_statement no debe normalizarse en
    silencio ni con datos inventados: debe propagar NormalizationError."""
    incomplete_payload = {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [],
        "quote": [
            {"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}
        ],
    }
    provider = _DummyProvider(payload=incomplete_payload)

    with pytest.raises(NormalizationError, match="debt"):
        fetch_and_normalize("AAPL", provider=provider)


def test_fetch_and_normalize_propagates_normalization_error_when_quote_missing() -> None:
    incomplete_payload = {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
        "quote": [],
    }
    provider = _DummyProvider(payload=incomplete_payload)

    with pytest.raises(NormalizationError, match="quote"):
        fetch_and_normalize("AAPL", provider=provider)


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_and_normalize_defaults_to_fmp_provider(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(
            [{"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}]
        ),
        _mock_response([{"date": "2025-12-31", "totalDebt": 400_000.0}]),
        _mock_response(
            [{"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}]
        ),
    ]
    config = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
    }

    result = fetch_and_normalize("AAPL", config=config)

    assert result.financial_statement.source == "fmp"
    assert result.market_data.source == "fmp"
    assert mock_get.call_count == 3
