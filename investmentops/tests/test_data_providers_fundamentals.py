"""Pruebas para el cliente mínimo de FMP (investmentops.data_providers.fundamentals).

Cubre las tareas "Implementar un cliente mínimo que consulte ese proveedor
y obtenga datos crudos de una empresa por ticker", "Adjuntar metadatos de
procedencia..." y "Implementar manejo de error básico..." (TASKS.md, Fase
1, "Fuente de datos fundamentales"). Como este cliente hace llamadas HTTP
reales a la API de FMP, todas las pruebas simulan (mockean) `requests.get`
en vez de depender de una llamada de red real o de una API key válida.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from investmentops.data_providers import DataProvider
from investmentops.data_providers.contracts import DataProviderError, RawProviderData
from investmentops.data_providers.fundamentals import FMPFundamentalsProvider


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def test_provider_satisfies_data_provider_protocol() -> None:
    provider = FMPFundamentalsProvider(api_key="fake-key")

    assert isinstance(provider, DataProvider)


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_returns_raw_provider_data_for_valid_ticker(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response([{"revenue": 1000, "netIncome": 100}]),
        _mock_response([{"totalDebt": 500}]),
        _mock_response([{"price": 150.0, "marketCap": 2_000_000}]),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch("aapl")

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert result.payload["income_statement"] == [{"revenue": 1000, "netIncome": 100}]
    assert result.payload["balance_sheet_statement"] == [{"totalDebt": 500}]
    assert result.payload["quote"] == [{"price": 150.0, "marketCap": 2_000_000}]
    assert result.metadata.source == "fmp"
    assert result.metadata.reliability == "alta"
    assert mock_get.call_count == 3


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_sends_api_key_as_query_param(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response([{"revenue": 1000}]),
        _mock_response([{"totalDebt": 500}]),
        _mock_response([{"price": 150.0}]),
    ]

    provider = FMPFundamentalsProvider(api_key="my-secret-key")
    provider.fetch("AAPL")

    for call in mock_get.call_args_list:
        assert call.kwargs["params"] == {"apikey": "my-secret-key"}


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raises_when_ticker_does_not_exist(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response([]),
        _mock_response([]),
        _mock_response([]),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no existe"):
        provider.fetch("NOPE")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raises_data_provider_error_on_network_failure(mock_get: Mock) -> None:
    mock_get.side_effect = requests.ConnectionError("boom")

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="No se pudo contactar"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raises_data_provider_error_on_unauthorized(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({}, status_code=401)

    provider = FMPFundamentalsProvider(api_key="bad-key")

    with pytest.raises(DataProviderError, match="rechazó"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raises_data_provider_error_on_server_error(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({}, status_code=500)

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="error \\(500\\)"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raises_data_provider_error_on_invalid_json(mock_get: Mock) -> None:
    bad_response = Mock()
    bad_response.status_code = 200
    bad_response.json.side_effect = ValueError("not json")
    mock_get.return_value = bad_response

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no se pudo interpretar"):
        provider.fetch("AAPL")


def test_fetch_rejects_empty_ticker() -> None:
    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no puede estar vacío"):
        provider.fetch("   ")


def test_constructor_raises_without_api_key() -> None:
    with pytest.raises(DataProviderError, match="Falta la API key"):
        FMPFundamentalsProvider(config={"data_providers": {"fundamentals": {}}})


def test_constructor_reads_api_key_and_base_url_from_config() -> None:
    config = {
        "data_providers": {
            "fundamentals": {
                "provider": "fmp",
                "api_key": "from-config",
                "base_url": "https://example.test/api",
            }
        }
    }

    provider = FMPFundamentalsProvider(config=config)

    assert provider._api_key == "from-config"
    assert provider._base_url == "https://example.test/api"


def test_constructor_uses_default_base_url_when_not_configured() -> None:
    provider = FMPFundamentalsProvider(
        config={"data_providers": {"fundamentals": {"api_key": "k"}}}
    )

    assert provider._base_url == "https://financialmodelingprep.com/api/v3"
