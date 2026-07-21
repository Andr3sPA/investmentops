"""Pruebas para el cliente mínimo de comparables de FMP
(investmentops.data_providers.comparables.FMPComparablesProvider).

Cubre la tarea "Implementar la consulta de comparables (lista de
empresas pares) para un ticker" (TASKS.md, Fase 5, "Fuente de datos de
comparables"), sobre la decisión ya tomada en
`investmentops/data_providers/COMPARABLES_PROVIDER.md`. La procedencia
por empresa par individual (`"source"`/`"queried_at"` por elemento) se
prueba en `test_data_providers_comparables_provenance.py`; este archivo
solo confirma que cada elemento del payload incluye esas claves sin
verificar su contenido en detalle. Como este cliente hace llamadas HTTP
reales a la API de FMP, todas las pruebas simulan (mockean)
`requests.get`.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from investmentops.data_providers import DataProvider
from investmentops.data_providers.comparables import (
    DEFAULT_BASE_URL,
    FMPComparablesProvider,
)
from investmentops.data_providers.contracts import DataProviderError, RawProviderData


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def _sample_peers_payload() -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "peersList": ["MSFT", "GOOG", "GOOGL"],
        }
    ]


def test_provider_satisfies_data_provider_protocol() -> None:
    provider = FMPComparablesProvider(api_key="fake-key")

    assert isinstance(provider, DataProvider)


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_returns_raw_provider_data_with_list_payload(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_peers_payload())

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("aapl")

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert len(result.payload) == 1
    entry = result.payload[0]
    assert entry["symbol"] == "AAPL"
    assert entry["companyName"] == "Apple Inc."
    assert entry["peersList"] == ["MSFT", "GOOG", "GOOGL"]
    assert result.metadata.source == "fmp"
    assert result.metadata.reliability == "alta"
    assert mock_get.call_count == 1


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_sends_symbol_and_api_key_as_query_params(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_peers_payload())

    provider = FMPComparablesProvider(api_key="my-secret-key")
    provider.fetch("AAPL")

    call = mock_get.call_args
    assert call.kwargs["params"] == {"symbol": "AAPL", "apikey": "my-secret-key"}


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_normalizes_ticker_to_uppercase(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_peers_payload())

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("ecopetrol.cl")

    assert result.ticker == "ECOPETROL.CL"
    assert mock_get.call_args.kwargs["params"]["symbol"] == "ECOPETROL.CL"


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_treats_empty_list_as_a_valid_response(mock_get: Mock) -> None:
    """FMP puede no encontrar pares para un ticker: una lista vacía es
    una respuesta válida, no un error."""
    mock_get.return_value = _mock_response([])

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    assert result.payload == []


def test_fetch_rejects_empty_ticker() -> None:
    provider = FMPComparablesProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no puede estar vacío"):
        provider.fetch("   ")


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_raises_data_provider_error_on_network_failure(mock_get: Mock) -> None:
    mock_get.side_effect = requests.ConnectionError("boom")

    provider = FMPComparablesProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="No se pudo contactar"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_raises_data_provider_error_on_unauthorized(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({}, status_code=401)

    provider = FMPComparablesProvider(api_key="bad-key")

    with pytest.raises(DataProviderError, match="rechazó"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_raises_data_provider_error_on_server_error(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({}, status_code=500)

    provider = FMPComparablesProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="error \\(500\\)"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.comparables.requests.get")
def test_fetch_raises_data_provider_error_on_invalid_json(mock_get: Mock) -> None:
    bad_response = Mock()
    bad_response.status_code = 200
    bad_response.json.side_effect = ValueError("not json")
    mock_get.return_value = bad_response

    provider = FMPComparablesProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no se pudo interpretar"):
        provider.fetch("AAPL")


def test_constructor_raises_without_api_key() -> None:
    with pytest.raises(DataProviderError, match="Falta la API key"):
        FMPComparablesProvider(config={"data_providers": {"comparables": {}}})


def test_constructor_reads_api_key_and_base_url_from_config() -> None:
    config = {
        "data_providers": {
            "comparables": {
                "api_key": "from-config",
                "base_url": "https://example.test/api",
            }
        }
    }

    provider = FMPComparablesProvider(config=config)

    assert provider._api_key == "from-config"
    assert provider._base_url == "https://example.test/api"


def test_constructor_uses_default_base_url_when_not_configured() -> None:
    provider = FMPComparablesProvider(
        config={"data_providers": {"comparables": {"api_key": "k"}}}
    )

    assert provider._base_url == DEFAULT_BASE_URL


def test_constructor_does_not_read_from_fundamentals_section() -> None:
    """La API key de [data_providers.fundamentals] no debe usarse aquí:
    [data_providers.comparables] es una sección separada (ver
    COMPARABLES_PROVIDER.md)."""
    config = {
        "data_providers": {
            "fundamentals": {"api_key": "fundamentals-key"},
        }
    }

    with pytest.raises(DataProviderError, match="Falta la API key"):
        FMPComparablesProvider(config=config)