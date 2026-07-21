"""Pruebas para la procedencia por noticia individual
(investmentops.data_providers.news.FMPNewsProvider.fetch).

Cubre la tarea "Adjuntar metadatos de procedencia (fuente, fecha de
publicación, fecha de consulta) a cada noticia cruda" (TASKS.md, Fase 4,
"Fuente de datos de noticias"). No prueba de nuevo el comportamiento
básico de `fetch` (contrato, parámetros de consulta, manejo de errores,
lista vacía como respuesta válida): eso ya está cubierto en
`test_data_providers_news.py`. Solo prueba que cada noticia cruda lleva
su propia procedencia (`"source"`, `"queried_at"`), sin alterar los
campos originales de FMP (incluida `"publishedDate"`, la fecha de
publicación) ni el `RawProviderData.metadata` de nivel superior.
"""

from unittest.mock import Mock, patch

from investmentops.data_providers.news import FMPNewsProvider


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


@patch("investmentops.data_providers.news.requests.get")
def test_each_news_item_has_source_and_queried_at(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    for item in result.payload:
        assert item["source"] == "fmp"
        assert "queried_at" in item


@patch("investmentops.data_providers.news.requests.get")
def test_provenance_matches_top_level_metadata(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    item = result.payload[0]
    assert item["source"] == result.metadata.source
    assert item["queried_at"] == result.metadata.queried_at.isoformat()


@patch("investmentops.data_providers.news.requests.get")
def test_provenance_preserves_original_fmp_fields_including_published_date(
    mock_get: Mock,
) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    item = result.payload[0]
    assert item["symbol"] == "AAPL"
    assert item["publishedDate"] == "2026-07-15 09:00:00"
    assert item["title"] == "Apple anuncia nuevo producto"
    assert item["text"] == "Resumen de la noticia..."
    assert item["site"] == "example_news_site"
    assert item["url"] == "https://example.test/news/1"


@patch("investmentops.data_providers.news.requests.get")
def test_provenance_does_not_mutate_original_response_objects(mock_get: Mock) -> None:
    """Confirma que se construyen copias nuevas, no se mutan los dicts
    originales devueltos por `response.json()`."""
    original_items = _sample_news_items()
    mock_get.return_value = _mock_response(original_items)

    provider = FMPNewsProvider(api_key="fake-key")
    provider.fetch("AAPL")

    assert "source" not in original_items[0]
    assert "queried_at" not in original_items[0]


@patch("investmentops.data_providers.news.requests.get")
def test_all_items_in_a_response_share_the_same_queried_at(mock_get: Mock) -> None:
    mock_get.return_value = _mock_response(_sample_news_items())

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    queried_at_values = {item["queried_at"] for item in result.payload}
    assert len(queried_at_values) == 1


@patch("investmentops.data_providers.news.requests.get")
def test_empty_response_still_returns_empty_list_payload(mock_get: Mock) -> None:
    """Una lista vacía sigue siendo válida y sigue siendo una lista (no
    rompe al intentar adjuntar procedencia sobre una lista vacía)."""
    mock_get.return_value = _mock_response([])

    provider = FMPNewsProvider(api_key="fake-key")
    result = provider.fetch("AAPL")

    assert result.payload == []