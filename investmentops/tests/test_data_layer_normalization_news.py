"""Pruebas para la transformación de noticias crudas al modelo de dominio
"Noticias" (investmentops.data_layer.normalization.news_from_raw).

Cubre la tarea "Implementar la transformación de noticias crudas al
modelo normalizado" (TASKS.md, Fase 4, "Normalización"). No prueba de
nuevo `financial_statement_from_raw`/`market_data_from_raw`/
`financial_statement_series_from_raw` (corte único y serie histórica, ya
cubiertos en `test_data_layer_normalization.py`/
`test_ai_providers_selection.py`), ni la consulta real a FMP
(`FMPNewsProvider.fetch`, ya cubierta en `test_data_providers_news.py`,
`test_data_providers_news_provenance.py` y
`test_data_providers_news_error_handling.py`): usa payloads con la misma
forma que ya produce `FMPNewsProvider.fetch`, incluyendo
`"source"`/`"queried_at"` por noticia.
"""

from datetime import datetime, timezone

import pytest

from investmentops.data_layer import News
from investmentops.data_layer.normalization import NormalizationError, news_from_raw
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


def _raw_news_data(payload: list, source: str = "fmp") -> RawProviderData:
    return RawProviderData(
        ticker="AAPL",
        payload=payload,
        metadata=ProviderMetadata(
            source=source,
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        ),
    )


def _news_item(
    title: str = "Apple anuncia nuevo producto",
    text: str = "Resumen de la noticia...",
    site: str = "example_news_site",
    published_date: str = "2026-07-15 09:00:00",
    url: str = "https://example.test/news/1",
    source: str = "fmp",
) -> dict:
    return {
        "symbol": "AAPL",
        "title": title,
        "text": text,
        "site": site,
        "publishedDate": published_date,
        "url": url,
        "source": source,
        "queried_at": "2026-07-19T00:00:00+00:00",
    }


def test_builds_one_news_per_raw_item_in_order() -> None:
    raw = _raw_news_data(
        [
            _news_item(title="Primera noticia", published_date="2026-07-15 09:00:00"),
            _news_item(title="Segunda noticia", published_date="2026-07-14 08:00:00"),
        ]
    )

    news_list = news_from_raw(raw)

    assert isinstance(news_list, list)
    assert len(news_list) == 2
    assert all(isinstance(item, News) for item in news_list)
    assert news_list[0].title == "Primera noticia"
    assert news_list[1].title == "Segunda noticia"


def test_maps_fields_from_raw_item_to_news() -> None:
    raw = _raw_news_data(
        [
            _news_item(
                title="Apple anuncia nuevo producto",
                text="Resumen de la noticia...",
                site="example_news_site",
                published_date="2026-07-15 09:00:00",
                url="https://example.test/news/1",
            )
        ]
    )

    news_list = news_from_raw(raw)

    news = news_list[0]
    assert news.title == "Apple anuncia nuevo producto"
    assert news.summary == "Resumen de la noticia..."
    assert news.source == "example_news_site"
    assert news.published_at == datetime(2026, 7, 15, 9, 0, 0)
    assert news.url == "https://example.test/news/1"


def test_source_is_the_publishing_site_not_the_data_provider() -> None:
    """`News.source` debe venir de `"site"` (el medio), no del proveedor
    de datos (`"source"` adjuntado por `_attach_news_provenance`, que en
    la práctica siempre es "fmp")."""
    raw = _raw_news_data([_news_item(site="Reuters", source="fmp")])

    news_list = news_from_raw(raw)

    assert news_list[0].source == "Reuters"


def test_empty_payload_returns_empty_list_without_error() -> None:
    """Una empresa sin noticias recientes no es un error de normalización."""
    raw = _raw_news_data([])

    news_list = news_from_raw(raw)

    assert news_list == []


def test_none_payload_returns_empty_list_without_error() -> None:
    raw = _raw_news_data(None)  # type: ignore[arg-type]

    news_list = news_from_raw(raw)

    assert news_list == []


def test_raises_when_title_is_missing() -> None:
    item = _news_item()
    del item["title"]
    raw = _raw_news_data([item])

    with pytest.raises(NormalizationError, match="title"):
        news_from_raw(raw)


def test_raises_when_summary_is_missing() -> None:
    item = _news_item()
    del item["text"]
    raw = _raw_news_data([item])

    with pytest.raises(NormalizationError, match="summary"):
        news_from_raw(raw)


def test_raises_when_source_site_is_missing() -> None:
    item = _news_item()
    del item["site"]
    raw = _raw_news_data([item])

    with pytest.raises(NormalizationError, match="source"):
        news_from_raw(raw)


def test_raises_when_published_at_is_missing() -> None:
    item = _news_item()
    del item["publishedDate"]
    raw = _raw_news_data([item])

    with pytest.raises(NormalizationError, match="published_at"):
        news_from_raw(raw)


def test_raises_when_url_is_missing() -> None:
    item = _news_item()
    del item["url"]
    raw = _raw_news_data([item])

    with pytest.raises(NormalizationError, match="url"):
        news_from_raw(raw)


def test_raises_when_published_date_is_invalid() -> None:
    raw = _raw_news_data([_news_item(published_date="not-a-date")])

    with pytest.raises(NormalizationError, match="formato reconocible"):
        news_from_raw(raw)


def test_error_message_identifies_the_position_of_the_offending_news_item() -> None:
    """Con varias noticias, el mensaje de error debe identificar cuál
    (por posición) falló, no solo que 'alguna' falló."""
    good_item = _news_item(title="Noticia válida")
    bad_item = _news_item(title="Noticia sin fecha")
    del bad_item["publishedDate"]
    raw = _raw_news_data([good_item, bad_item])

    with pytest.raises(NormalizationError, match="#2"):
        news_from_raw(raw)


def test_does_not_raise_on_valid_multi_item_payload() -> None:
    raw = _raw_news_data(
        [
            _news_item(title="Noticia 1", published_date="2026-07-15 09:00:00"),
            _news_item(title="Noticia 2", published_date="2026-07-14 08:00:00"),
            _news_item(title="Noticia 3", published_date="2026-07-13 07:30:00"),
        ]
    )

    news_list = news_from_raw(raw)

    assert len(news_list) == 3