"""Pruebas para el filtrado de noticias por ventana de tiempo reciente
(investmentops.analysis_engines.news_relevance.filter_relevant_news).

Cubre la tarea "Implementar el filtrado de noticias según ese criterio"
(TASKS.md, Fase 4, "Motor de análisis: noticias relevantes"), sobre el
criterio ya fijado en
`investmentops/analysis_engines/NEWS_RELEVANCE.md`. No prueba el resumen
breve por noticia ni el ensamblado del resultado estructurado del motor:
son tareas separadas y posteriores de la misma sección.
"""

from datetime import datetime

import pytest

from investmentops.analysis_engines.news_relevance import (
    DEFAULT_RELEVANCE_WINDOW_DAYS,
    filter_relevant_news,
)
from investmentops.data_layer import News


def _news(
    title: str = "Noticia",
    published_at: datetime = datetime(2026, 7, 15, 9, 0, 0),
) -> News:
    return News(
        title=title,
        summary="Resumen",
        source="example_news_site",
        published_at=published_at,
        url="https://example.test/news",
    )


def test_keeps_news_within_the_default_seven_day_window() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    recent = _news(title="Reciente", published_at=datetime(2026, 7, 15, 9, 0, 0))

    result = filter_relevant_news([recent], now=now)

    assert result == [recent]


def test_excludes_news_older_than_the_window() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    old = _news(title="Vieja", published_at=datetime(2026, 7, 1, 9, 0, 0))

    result = filter_relevant_news([old], now=now)

    assert result == []


def test_includes_news_exactly_at_the_window_boundary() -> None:
    """Una noticia publicada justo en el límite de la ventana (`now -
    days`) debe incluirse, no excluirse por un margen mínimo."""
    now = datetime(2026, 7, 20, 12, 0, 0)
    boundary = _news(title="En el límite", published_at=datetime(2026, 7, 13, 12, 0, 0))

    result = filter_relevant_news([boundary], now=now, days=7)

    assert result == [boundary]


def test_uses_seven_days_as_default_window() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    just_inside = _news(
        title="Justo dentro", published_at=datetime(2026, 7, 13, 12, 0, 1)
    )
    just_outside = _news(
        title="Justo fuera", published_at=datetime(2026, 7, 13, 11, 59, 59)
    )

    result = filter_relevant_news([just_inside, just_outside], now=now)

    assert result == [just_inside]
    assert DEFAULT_RELEVANCE_WINDOW_DAYS == 7


def test_accepts_custom_window_size() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    within_30_days = _news(
        title="Dentro de 30 días", published_at=datetime(2026, 6, 25, 9, 0, 0)
    )

    result = filter_relevant_news([within_30_days], now=now, days=30)

    assert result == [within_30_days]


def test_preserves_relative_order_of_input_without_reordering() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    first = _news(title="Primera", published_at=datetime(2026, 7, 14, 9, 0, 0))
    second = _news(title="Segunda", published_at=datetime(2026, 7, 18, 9, 0, 0))
    third = _news(title="Tercera", published_at=datetime(2026, 7, 16, 9, 0, 0))

    result = filter_relevant_news([first, second, third], now=now)

    assert [item.title for item in result] == ["Primera", "Segunda", "Tercera"]


def test_empty_input_returns_empty_list() -> None:
    result = filter_relevant_news([], now=datetime(2026, 7, 20, 12, 0, 0))

    assert result == []


def test_no_news_within_window_returns_empty_list_without_error() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    old_one = _news(title="Vieja 1", published_at=datetime(2026, 1, 1, 9, 0, 0))
    old_two = _news(title="Vieja 2", published_at=datetime(2026, 2, 1, 9, 0, 0))

    result = filter_relevant_news([old_one, old_two], now=now)

    assert result == []


def test_defaults_now_to_the_current_time_when_not_provided() -> None:
    """Sin `now` explícito, debe evaluarse contra el reloj real, no
    quedarse "congelado" en algún instante fijo."""
    recent = _news(published_at=datetime.now())

    result = filter_relevant_news([recent])

    assert result == [recent]