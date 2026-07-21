# investmentops/tests/test_data_providers_news_error_handling.py
"""Pruebas para el manejo de error cuando el proveedor de noticias falla
o no devuelve resultados (investmentops.data_providers.news.FMPNewsProvider.fetch).

Cubre la tarea "Implementar manejo de error si el proveedor de noticias
falla o no devuelve resultados" (TASKS.md, Fase 4, "Fuente de datos de
noticias"). No prueba de nuevo el contrato básico (`test_data_providers_news.py`,
ya cubre red/401/500/JSON inválido/ticker vacío/lista vacía) ni la
procedencia por noticia (`test_data_providers_news_provenance.py`). Solo
prueba el caso nuevo de esta tarea: un cuerpo JSON válido (200, sin error
de parseo) que no tiene la forma esperada (una lista de noticias).
"""

from unittest.mock import Mock, patch

import pytest

from investmentops.data_providers.contracts import DataProviderError
from investmentops.data_providers.news import FMPNewsProvider


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_raises_when_fmp_returns_an_error_object_instead_of_a_list(
    mock_get: Mock,
) -> None:
    """FMP a veces responde 200 con un objeto de error en vez de una lista
    (ej. API key inválida sin un código HTTP de error claro)."""
    mock_get.return_value = _mock_response({"Error Message": "Invalid API KEY"})

    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="formato inesperado"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_raises_when_fmp_returns_a_plain_string(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response("no soy una lista de noticias")

    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="formato inesperado"):
        provider.fetch("AAPL")


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_treats_null_response_as_empty_list_not_an_error(mock_get: Mock) -> None:
    """`null` (None tras json()) se trata igual que una lista vacía: sin
    noticias, no un fallo."""
    mock_get.return_value = _mock_response(None)

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    assert result.payload == []


@patch("investmentops.data_providers.news.requests.get")
def test_fetch_error_message_identifies_the_ticker(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response({"error": "algo salió mal"})

    provider = FMPNewsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="AAPL"):
        provider.fetch("AAPL")