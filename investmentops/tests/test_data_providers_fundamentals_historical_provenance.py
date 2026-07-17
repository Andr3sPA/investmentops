"""Pruebas para la procedencia por punto de la serie histórica
(investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch_historical).

Cubre la tarea "Adjuntar metadatos de procedencia a cada punto de la
serie histórica" (TASKS.md, Fase 3, "Fuente de datos histórica"). No
prueba de nuevo el comportamiento básico de `fetch_historical` (series
completas, `period`/`limit`, validación de argumentos, manejo de
errores): eso ya está cubierto en
`test_data_providers_fundamentals_historical.py`. Solo prueba que cada
punto de `income_statement`/`balance_sheet_statement` lleva su propia
procedencia (`"source"`, `"queried_at"`), sin alterar los campos
originales de FMP ni el `RawProviderData.metadata` de nivel superior.
"""

from unittest.mock import Mock, patch

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


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_each_income_statement_point_has_source_and_queried_at(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(3)),
        _mock_response(_balance_series(3)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("AAPL")

    for point in result.payload["income_statement"]:
        assert point["source"] == "fmp"
        assert "queried_at" in point


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_each_balance_sheet_point_has_source_and_queried_at(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(2)),
        _mock_response(_balance_series(2)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("AAPL")

    for point in result.payload["balance_sheet_statement"]:
        assert point["source"] == "fmp"
        assert "queried_at" in point


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_point_provenance_matches_top_level_metadata(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(1)),
        _mock_response(_balance_series(1)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("AAPL")

    point = result.payload["income_statement"][0]
    assert point["source"] == result.metadata.source
    assert point["queried_at"] == result.metadata.queried_at.isoformat()


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_point_provenance_preserves_original_fmp_fields(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(1)),
        _mock_response(_balance_series(1)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("AAPL")

    income_point = result.payload["income_statement"][0]
    assert income_point["date"] == "2025-12-31"
    assert income_point["revenue"] == 1_000_000.0
    assert income_point["netIncome"] == 100_000.0

    balance_point = result.payload["balance_sheet_statement"][0]
    assert balance_point["date"] == "2025-12-31"
    assert balance_point["totalDebt"] == 400_000.0


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_point_provenance_does_not_mutate_original_response_objects(mock_get: Mock) -> None:
    """Confirma que se construyen copias nuevas, no se mutan los dicts
    originales devueltos por `response.json()`."""
    original_income = _income_series(1)
    mock_get.side_effect = [
        _mock_response(original_income),
        _mock_response(_balance_series(1)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    provider.fetch_historical("AAPL")

    assert "source" not in original_income[0]
    assert "queried_at" not in original_income[0]


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_all_points_in_a_series_share_the_same_queried_at(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(_income_series(3)),
        _mock_response(_balance_series(3)),
    ]

    provider = FMPFundamentalsProvider(api_key="fake-key")
    result = provider.fetch_historical("AAPL")

    queried_at_values = {point["queried_at"] for point in result.payload["income_statement"]}
    assert len(queried_at_values) == 1
