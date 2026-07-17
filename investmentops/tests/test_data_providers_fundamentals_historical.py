"""Pruebas para la consulta de series históricas de ingresos y beneficios
(investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch_historical).

Cubre la tarea "Implementar la consulta de series históricas de ingresos
y beneficios para un ticker" (TASKS.md, Fase 3, "Fuente de datos
histórica"), sobre la base ya investigada y documentada en
`investmentops/data_providers/HISTORICAL_DATA.md`. No prueba de nuevo
`fetch()` (ya cubierto en `test_data_providers_fundamentals.py`), salvo
para confirmar que su comportamiento no cambió (`params == {"apikey":
...}`, sin `period`/`limit`). No prueba la transformación de estas
series al modelo de dominio de series temporales ni la propagación de
metadatos por punto: esas son tareas separadas y posteriores de la misma
sección de la Fase 3 ("Normalización").
"""

from unittest.mock import Mock, patch

import pytest
import requests

from investmentops.data_providers.contracts import DataProviderError, RawProviderData
from investmentops.data_providers.fundamentals import FMPFundamentalsProvider


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def _income_series(n: int = 3) -> list[dict]:
    return [
        {"date": f"{2025 - i}-12-31", "revenue": 1_000_000.0 - i * 1000, "netIncome": 100_000.0 - i * 10}
        for i in range(n)
    ]


def _balance_series(n: int = 3) -> list[dict]:
    return [{"date": f"{2025 - i}-12-31", "totalDebt": 400_000.0 - i * 100} for i in range(n)]


# --- fetch_historical: comportamiento básico --------------------------------


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_returns_raw_provider_data_with_full_series(
    mock_get: Mock,
) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(3)),
        _mock_response(_balance_series(3)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("aapl")

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert len(result.payload["income_statement"]) == 3
    assert len(result.payload["balance_sheet_statement"]) == 3
    assert result.metadata.source == "fmp"
    assert result.metadata.reliability == "alta"
    assert mock_get.call_count == 2


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_does_not_query_quote_endpoint(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(2)),
        _mock_response(_balance_series(2)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    provider.fetch_historical("AAPL")

    called_urls = [call.args[0] for call in mock_get.call_args_list]
    assert all("/quote/" not in url for url in called_urls)


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_sends_period_and_limit_query_params(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(2)),
        _mock_response(_balance_series(2)),
    ]

    provider = FMPFundamentalsProvider(api_key="my-secret-key")
    provider.fetch_historical("AAPL", period="quarter", limit=8)

    for call in mock_get.call_args_list:
        assert call.kwargs["params"] == {
            "apikey": "my-secret-key",
            "period": "quarter",
            "limit": 8,
        }


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_defaults_to_annual_period_and_limit_5(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(2)),
        _mock_response(_balance_series(2)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    provider.fetch_historical("AAPL")

    for call in mock_get.call_args_list:
        assert call.kwargs["params"]["period"] == "annual"
        assert call.kwargs["params"]["limit"] == 5


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_normalizes_ticker_to_uppercase(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(1)),
        _mock_response(_balance_series(1)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("ecopetrol.cl")

    assert result.ticker == "ECOPETROL.CL"


# --- Validación de argumentos -------------------------------------------------


def test_fetch_historical_rejects_empty_ticker() -> None:
    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no puede estar vacío"):
        provider.fetch_historical("   ")


def test_fetch_historical_rejects_invalid_period() -> None:
    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="'period'"):
        provider.fetch_historical("AAPL", period="monthly")


def test_fetch_historical_rejects_limit_below_one() -> None:
    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="'limit'"):
        provider.fetch_historical("AAPL", limit=0)


# --- Manejo de errores (mismo criterio que fetch()) --------------------------


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_raises_when_ticker_has_no_historical_data(
    mock_get: Mock,
) -> None:
    mock_get.side_effect = [_mock_response([]), _mock_response([])]

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no existe"):
        provider.fetch_historical("NOPE")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_raises_data_provider_error_on_network_failure(
    mock_get: Mock,
) -> None:
    mock_get.side_effect = requests.ConnectionError("boom")

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="No se pudo contactar"):
        provider.fetch_historical("AAPL")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_raises_data_provider_error_on_unauthorized(
    mock_get: Mock,
) -> None:
    mock_get.return_value = _mock_response({}, status_code=401)

    provider = FMPFundamentalsProvider(api_key="bad-key")

    with pytest.raises(DataProviderError, match="rechazó"):
        provider.fetch_historical("AAPL")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_raises_data_provider_error_on_server_error(
    mock_get: Mock,
) -> None:
    mock_get.return_value = _mock_response({}, status_code=500)

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="error \\(500\\)"):
        provider.fetch_historical("AAPL")


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_historical_raises_data_provider_error_on_invalid_json(
    mock_get: Mock,
) -> None:
    bad_response = Mock()
    bad_response.status_code = 200
    bad_response.json.side_effect = ValueError("not json")
    mock_get.return_value = bad_response

    provider = FMPFundamentalsProvider(api_key="fake-key")

    with pytest.raises(DataProviderError, match="no se pudo interpretar"):
        provider.fetch_historical("AAPL")


# --- Regresión: fetch() no cambió su comportamiento ---------------------------


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_still_sends_only_apikey_without_period_or_limit(mock_get: Mock) -> None:
    """Confirma que extender `_get` con `extra_params` no afectó a `fetch()`:
    sigue enviando únicamente `apikey`, sin `period` ni `limit`."""
    mock_get.side_effect = [
        _mock_response([{"revenue": 1000, "netIncome": 100}]),
        _mock_response([{"totalDebt": 500}]),
        _mock_response([{"price": 150.0, "marketCap": 2_000_000}]),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    provider.fetch("AAPL")

    for call in mock_get.call_args_list:
        assert call.kwargs["params"] == {"apikey": "fake-key"}
