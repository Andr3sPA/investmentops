"""Pruebas para la procedencia por empresa par individual
(investmentops.data_providers.comparables.FMPComparablesProvider.fetch).

Cubre la tarea "Adjuntar metadatos de procedencia a los datos de
comparables" (TASKS.md, Fase 5, "Fuente de datos de comparables"). No
prueba de nuevo el comportamiento básico de `fetch` (contrato,
parámetros de consulta, manejo de errores, lista vacía como respuesta
válida): eso ya está cubierto en `test_data_providers_comparables.py`.
Solo prueba que cada elemento del payload lleva su propia procedencia
(`"source"`, `"queried_at"`), sin alterar los campos originales de FMP
ni el `RawProviderData.metadata` de nivel superior. Mismo patrón ya
usado en `test_data_providers_fundamentals_historical_provenance.py` y
`test_data_providers_news_provenance.py`.
"""

from unittest.mock import Mock, patch

from investmentops.data_providers.comparables import FMPComparablesProvider


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


@patch("investmentops.data_providers.comparables.requests.get")
def test_each_payload_item_has_source_and_queried_at(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_peers_payload())

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    for item in result.payload:
        assert item["source"] == "fmp"
        assert "queried_at" in item


@patch("investmentops.data_providers.comparables.requests.get")
def test_provenance_matches_top_level_metadata(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_peers_payload())

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    item = result.payload[0]
    assert item["source"] == result.metadata.source
    assert item["queried_at"] == result.metadata.queried_at.isoformat()


@patch("investmentops.data_providers.comparables.requests.get")
def test_provenance_preserves_original_fmp_fields(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_peers_payload())

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    item = result.payload[0]
    assert item["symbol"] == "AAPL"
    assert item["companyName"] == "Apple Inc."
    assert item["peersList"] == ["MSFT", "GOOG", "GOOGL"]


@patch("investmentops.data_providers.comparables.requests.get")
def test_provenance_does_not_mutate_original_response_objects(mock_get: Mock) -> None:
    """Confirma que se construyen copias nuevas, no se mutan los dicts
    originales devueltos por `response.json()`."""
    original_payload = _sample_peers_payload()
    mock_get.return_value = _mock_response(original_payload)

    provider = FMPComparablesProvider(api_key="fake-key")
    provider.fetch("AAPL")

    assert "source" not in original_payload[0]
    assert "queried_at" not in original_payload[0]


@patch("investmentops.data_providers.comparables.requests.get")
def test_empty_payload_stays_empty_after_attaching_provenance(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response([])

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    assert result.payload == []


@patch("investmentops.data_providers.comparables.requests.get")
def test_all_items_share_the_same_queried_at(mock_get: Mock) -> None:
    payload = _sample_peers_payload() + [
        {"symbol": "AAPL", "companyName": "Apple Inc. (dup)", "peersList": ["META"]}
    ]
    mock_get.return_value = _mock_response(payload)

    provider = FMPComparablesProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    queried_at_values = {item["queried_at"] for item in result.payload}
    assert len(queried_at_values) == 1