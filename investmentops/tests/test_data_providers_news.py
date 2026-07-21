"""Pruebas para el cliente mínimo de noticias de FMP
(investmentops.data_providers.news.FMPNewsProvider).

Cubre la tarea "Implementar el contrato de 'data provider' para noticias
(ticker/nombre de empresa in, lista de eventos crudos out)" (TASKS.md,
Fase 4, "Fuente de datos de noticias"), sobre la decisión ya tomada en
`investmentops/data_providers/NEWS_PROVIDER.md`. No prueba todavía la
procedencia por noticia individual ni el manejo explícito de "sin
resultados": esas son tareas separadas y posteriores de la misma
sección. Como este cliente hace llamadas HTTP reales a la API de FMP,
todas las pruebas simulan (mockean) `requests.get`.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from investmentops.data_providers import DataProvider
from investmentops.data_providers.contracts import DataProviderError, RawProviderData
from investmentops.data_providers.news import DEFAULT_LIMIT, FMPNewsProvider


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def _sample_news_items() -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "publishedDate": "2026-07-15 09:00:00",
            "title": "Apple anuncia nuevo producto",
            "text": "Resumen de la noticia...",
            "site": "example_news_site",
            "url": "https://example.test/news/1",
        },
        {
            "symbol": "AAPL",
            "publishedDate": "2026-07-14 08:00:00",
            "title": "Analistas comentan resultados trimestrales",
            "text": "Otro resumen...",
            "site": "another_site",
            "url": "https://example.test/news/2",
        },
    ]


def test_provider_satisfies_data_provider_protocol() -> None:
    provider = FMPNewsProvider(api_key="fake-key")

    assert isinstance(provider, DataProvider)


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_returns_raw_provider_data_with_list_payload(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("aapl")

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert result.payload == _sample_news_items()
    assert result.metadata.source == "fmp"
    assert result.metadata.reliability == "alta"
    assert mock_get.call_count == 1


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_sends_ticker_limit_and_api_key_as_query_params(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="my-secret-key")
    provider.fetch("AAPL")

    call = mock_get.call_args
    assert call.kwargs["params"] == {
        "tickers": "AAPL",
        "limit": DEFAULT_LIMIT,
        "apikey": "my-secret-key",
    }


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_uses_custom_limit_when_provided(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key", limit=10)
    provider.fetch("AAPL")

    assert mock_get.call_args.kwargs["params"]["limit"] == 10


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_normalizes_ticker_to_uppercase(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("ecopetrol.cl")

    assert result.ticker == "ECOPETROL.CL"
    assert mock_get.call_args.kwargs["params"]["tickers"] == "ECOPETROL.CL"


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_treats_empty_list_as_a_valid_response(mock_get: Mock) -> None:
    """Una empresa sin noticias recientes no es un error en esta tarea
    (ver docstring del módulo, 'Alcance de esta tarea'): el manejo
    explícito de 'sin resultados' es una tarea separada y posterior."""
    mock_get.return_value = _mock_response([])

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    assert result.payload == []


def test_fetch_rejects_empty_ticker() -> None:
    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no puede estar vacío"):
        provider.fetch("   ")


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_raises_data_provider_error_on_network_failure(mock_get: Mock) -> None:
    mock_get.side_effect = requests.ConnectionError("boom")

    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="No se pudo contactar"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_raises_data_provider_error_on_unauthorized(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({}, status_code=401)

    provider = FMPNewsProvider(api_key="bad-key")

    with pytest.raises(DataProviderError, match="rechazó"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_raises_data_provider_error_on_server_error(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({}, status_code=500)

    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="error \\(500\\)"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_raises_data_provider_error_on_invalid_json(mock_get: Mock) -> None:
    bad_response = Mock()
    bad_response.status_code = 200
    bad_response.json.side_effect = ValueError("not json")
    mock_get.return_value = bad_response

    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no se pudo interpretar"):
        provider.fetch("AAPL")


def test_constructor_raises_without_api_key() -> None:
    with pytest.raises(DataProviderError, match="Falta la API key"):
        FMPNewsProvider(config={"data_providers": {"news": {}}})


def test_constructor_reads_api_key_and_base_url_from_config() -> None:
    config = {
        "data_providers": {
            "news": {
                "api_key": "from-config",
                "base_url": "https://example.test/api",
            }
        }
    }

    provider = FMPNewsProvider(config=config)

    assert provider._api_key == "from-config"
    assert provider._base_url == "https://example.test/api"


def test_constructor_uses_default_base_url_when_not_configured() -> None:
    provider = FMPNewsProvider(
        config={"data_providers": {"news": {"api_key": "k"}}}
    )

    assert provider._base_url == "https://financialmodelingprep.com/api/v3"


def test_constructor_does_not_read_from_fundamentals_section() -> None:
    """La API key de [data_providers.fundamentals] no debe usarse aquí:
    [data_providers.news] es una sección separada (ver NEWS_PROVIDER.md)."""
    config = {
        "data_providers": {
            "fundamentals": {"api_key": "fundamentals-key"},
        }
    }

    with pytest.raises(DataProviderError, match="Falta la API key"):
        FMPNewsProvider(config=config)