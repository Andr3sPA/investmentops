"""Pruebas para la obtención y normalización de noticias en el
orquestador (investmentops.core.orchestrator.fetch_raw_news_data /
fetch_and_normalize_news).

Cubre la tarea "Registrar el nuevo proveedor de noticias sin modificar
los proveedores existentes" (TASKS.md, Fase 4, "Orquestador"). Sigue
exactamente el mismo patrón de pruebas ya usado en
`test_core_orchestrator_normalization.py` para `fetch_normalized_data`
(fundamentales, Fase 1), aplicado al proveedor de noticias
(`FMPNewsProvider`, Fase 4). No prueba el motor de análisis de noticias
relevantes ni su inclusión en `ResearchResult`: son tareas separadas y
posteriores de la misma sección.
"""

from datetime import datetime, timezone

import pytest

from investmentops.core.orchestrator import (
    fetch_and_normalize_news,
    fetch_raw_news_data,
)
from investmentops.data_layer import News
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyNewsProvider:
    """Proveedor mínimo de prueba que cumple el mismo contrato que
    `FMPNewsProvider` (un método `fetch(ticker) -> RawProviderData`)."""

    def __init__(self, payload: list[dict]) -> None:
        self._payload = payload
        self.received_ticker: str | None = None

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_ticker = ticker
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="fmp",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingNewsProvider:
    """Proveedor mínimo de prueba que señala un fallo mediante el contrato."""

    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"No se pudo obtener noticias para '{ticker}'")


def _news_item(
    title: str = "Apple anuncia nuevo producto",
    text: str = "Resumen de la noticia...",
    site: str = "example_news_site",
    published_date: str = "2026-07-15 09:00:00",
    url: str = "https://example.test/news/1",
) -> dict:
    return {
        "symbol": "AAPL",
        "title": title,
        "text": text,
        "site": site,
        "publishedDate": published_date,
        "url": url,
        "source": "fmp",
        "queried_at": "2026-07-19T00:00:00+00:00",
    }


# --- fetch_raw_news_data ------------------------------------------------------


def test_fetch_raw_news_data_uses_injected_provider() -> None:
    provider = _DummyNewsProvider([_news_item()])

    result = fetch_raw_news_data("AAPL", provider=provider)

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert provider.received_ticker == "AAPL"


def test_fetch_raw_news_data_propagates_provider_failure() -> None:
    with pytest.raises(DataProviderError, match="No se pudo obtener noticias"):
        fetch_raw_news_data("NOPE", provider=_FailingNewsProvider())


def test_fetch_raw_news_data_returns_raw_provider_data_with_metadata() -> None:
    provider = _DummyNewsProvider([_news_item()])

    result = fetch_raw_news_data("AAPL", provider=provider)

    assert result.metadata.source == "fmp"
    assert result.payload == [_news_item()]


# --- fetch_and_normalize_news --------------------------------------------------


def test_fetch_and_normalize_news_returns_list_of_news() -> None:
    provider = _DummyNewsProvider([_news_item(), _news_item(title="Segunda noticia")])

    result = fetch_and_normalize_news("AAPL", provider=provider)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(item, News) for item in result)
    assert result[0].title == "Apple anuncia nuevo producto"
    assert result[1].title == "Segunda noticia"


def test_fetch_and_normalize_news_maps_fields_correctly() -> None:
    provider = _DummyNewsProvider([_news_item()])

    result = fetch_and_normalize_news("AAPL", provider=provider)

    news = result[0]
    assert news.summary == "Resumen de la noticia..."
    assert news.source == "example_news_site"
    assert news.published_at == datetime(2026, 7, 15, 9, 0, 0)
    assert news.url == "https://example.test/news/1"


def test_fetch_and_normalize_news_returns_empty_list_when_no_news() -> None:
    provider = _DummyNewsProvider([])

    result = fetch_and_normalize_news("AAPL", provider=provider)

    assert result == []


def test_fetch_and_normalize_news_propagates_data_provider_error() -> None:
    with pytest.raises(DataProviderError, match="No se pudo obtener noticias"):
        fetch_and_normalize_news("NOPE", provider=_FailingNewsProvider())


def test_fetch_and_normalize_news_passes_ticker_to_provider() -> None:
    provider = _DummyNewsProvider([_news_item()])

    fetch_and_normalize_news("AAPL", provider=provider)

    assert provider.received_ticker == "AAPL"