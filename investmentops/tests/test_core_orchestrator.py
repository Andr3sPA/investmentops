"""Pruebas para la función que dispara la consulta al proveedor de datos
fundamentales (investmentops.core.orchestrator.fetch_raw_data).

Cubre la tarea "Implementar la función que recibe un ticker y dispara la
consulta al proveedor de Fase 1" (TASKS.md, Fase 1, "Orquestador
mínimo"). No prueba normalización, agentes de análisis, ensamblado en
`ResearchResult` ni manejo de fallos parciales: esas son tareas
separadas y posteriores de la misma sección.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.core.orchestrator import fetch_raw_data
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que cumple el contrato `DataProvider`."""

    def __init__(self) -> None:
        self.received_ticker: str | None = None

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_ticker = ticker
        return RawProviderData(
            ticker=ticker,
            payload={"revenue": 1000},
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
