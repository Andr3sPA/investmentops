"""Pruebas para la selección de un resumen breve por noticia
(investmentops.analysis_engines.news_relevance.select_news_summary).

Cubre la tarea "Implementar un resumen breve por noticia relevante (o
selección del resumen ya provisto por la fuente)" (TASKS.md, Fase 4,
"Motor de análisis: noticias relevantes"). No prueba de nuevo
`filter_relevant_news` (ya cubierto en
`test_analysis_engines_news_relevance.py`).
"""

from datetime import datetime

from investmentops.analysis_engines.news_relevance import (
    DEFAULT_SUMMARY_MAX_LENGTH,
    select_news_summary,
)
from investmentops.data_layer import News


def _news(summary: str) -> News:
    return News(
        title="Título de prueba",
        summary=summary,
        source="example_news_site",
        published_at=datetime(2026, 7, 15, 9, 0, 0),
        url="https://example.test/news",
    )


def test_returns_summary_unchanged_when_within_max_length() -> None:
    news = _news("Resumen corto y directo.")

    result = select_news_summary(news, max_length=280)

    assert result == "Resumen corto y directo."


def test_truncates_at_the_nearest_word_boundary_when_too_long() -> None:
    news = _news("abcde fghij klmno")

    result = select_news_summary(news, max_length=10)

    assert result == "abcde..."


def test_hard_truncates_when_no_whitespace_before_the_limit() -> None:
    """Una sola palabra más larga que el límite: se corta exactamente en
    `max_length`, sin buscar un límite de palabra que no existe."""
    news = _news("abcdefghij")

    result = select_news_summary(news, max_length=5)

    assert result == "abcde..."


def test_strips_trailing_whitespace_before_appending_ellipsis() -> None:
    news = _news("abcde  fghij")

    result = select_news_summary(news, max_length=8)

    assert result == "abcde..."


def test_uses_280_as_default_max_length() -> None:
    news = _news("x" * 300)

    result = select_news_summary(news)

    assert result == "x" * 280 + "..."
    assert DEFAULT_SUMMARY_MAX_LENGTH == 280


def test_empty_summary_returns_empty_string() -> None:
    news = _news("")

    result = select_news_summary(news, max_length=280)

    assert result == ""


def test_summary_exactly_at_max_length_is_not_truncated() -> None:
    news = _news("x" * 280)

    result = select_news_summary(news, max_length=280)

    assert result == "x" * 280