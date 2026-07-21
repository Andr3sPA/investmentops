"""Pruebas para el modelo de dominio "Noticias" (investmentops.data_layer.News).

Cubre la tarea "Definir el modelo de dominio 'Noticias' (fecha, fuente,
resumen)" (TASKS.md, Fase 4, "Normalización"). No prueba ninguna
transformación desde datos crudos de un proveedor: eso corresponde a una
tarea posterior (ver TASKS.md, "Implementar la transformación de
noticias crudas al modelo normalizado").
"""

from datetime import datetime

import pytest

from investmentops.data_layer import News


def test_news_holds_title_summary_source_published_at_and_url() -> None:
    news = News(
        title="Apple anuncia nuevo producto",
        summary="Resumen de la noticia...",
        source="example_news_site",
        published_at=datetime(2026, 7, 15, 9, 0, 0),
        url="https://example.test/news/1",
    )

    assert news.title == "Apple anuncia nuevo producto"
    assert news.summary == "Resumen de la noticia..."
    assert news.source == "example_news_site"
    assert news.published_at == datetime(2026, 7, 15, 9, 0, 0)
    assert news.url == "https://example.test/news/1"


def test_news_is_immutable() -> None:
    news = News(
        title="Apple anuncia nuevo producto",
        summary="Resumen de la noticia...",
        source="example_news_site",
        published_at=datetime(2026, 7, 15, 9, 0, 0),
        url="https://example.test/news/1",
    )

    with pytest.raises(AttributeError):
        news.title = "Otro titular"  # type: ignore[misc]


def test_news_published_at_preserves_time_granularity() -> None:
    """A diferencia de FinancialStatement.period_end/MarketData.as_of
    (solo fecha), published_at conserva la hora de publicación."""
    news = News(
        title="Analistas comentan resultados trimestrales",
        summary="Otro resumen...",
        source="another_site",
        published_at=datetime(2026, 7, 14, 23, 45, 0),
        url="https://example.test/news/2",
    )

    assert news.published_at.hour == 23
    assert news.published_at.minute == 45


def test_news_source_is_the_publishing_site_not_the_data_provider() -> None:
    """El campo `source` identifica el medio (ej. Reuters), no el
    proveedor de datos (fmp) que entregó la noticia."""
    news = News(
        title="Título de ejemplo",
        summary="Resumen de ejemplo",
        source="Reuters",
        published_at=datetime(2026, 7, 15, 9, 0, 0),
        url="https://example.test/news/3",
    )

    assert news.source == "Reuters"