"""Pruebas para el ensamblado del resultado estructurado del motor de
noticias relevantes
(investmentops.analysis_engines.news_relevance.assemble_news_relevance_analysis).

Cubre la tarea "Ensamblar el resultado estructurado del motor (hallazgos,
lista de noticias relevantes, advertencias si no hay noticias)"
(TASKS.md, Fase 4, "Motor de análisis: noticias relevantes"). No prueba
de nuevo `filter_relevant_news` (ya cubierto en
`test_analysis_engines_news_relevance.py`) ni `select_news_summary` (ya
cubierto en `test_analysis_engines_news_summary.py`) más allá de lo
necesario para confirmar que `assemble_news_relevance_analysis` los
encadena correctamente.
"""

from datetime import datetime

import pytest

from investmentops.analysis_engines.news_relevance import (
    AGENT_ID,
    NewsRelevanceResult,
    assemble_news_relevance_analysis,
)
from investmentops.data_layer import News


def _news(
    title: str = "Noticia",
    summary: str = "Resumen breve.",
    source: str = "example_news_site",
    published_at: datetime = datetime(2026, 7, 15, 9, 0, 0),
    url: str = "https://example.test/news",
) -> News:
    return News(
        title=title,
        summary=summary,
        source=source,
        published_at=published_at,
        url=url,
    )


# --- Estructura básica del resultado -----------------------------------------


def test_returns_news_relevance_result_with_expected_analysis_id() -> None:
    result = assemble_news_relevance_analysis(
        [_news()], now=datetime(2026, 7, 20, 12, 0, 0)
    )

    assert isinstance(result, NewsRelevanceResult)
    assert result.analysis_id == AGENT_ID
    assert result.analysis_id == "news_relevance"


def test_result_is_immutable() -> None:
    result = assemble_news_relevance_analysis(
        [_news()], now=datetime(2026, 7, 20, 12, 0, 0)
    )

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


# --- Hallazgos -----------------------------------------------------------------


def test_findings_report_count_of_relevant_news_found() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [
        _news(title="Primera", published_at=datetime(2026, 7, 18, 9, 0, 0)),
        _news(title="Segunda", published_at=datetime(2026, 7, 15, 9, 0, 0)),
    ]

    result = assemble_news_relevance_analysis(items, now=now)

    assert len(result.findings) == 1
    assert "2" in result.findings[0]
    assert "relevantes" in result.findings[0]


def test_findings_use_singular_for_a_single_relevant_news() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [_news(published_at=datetime(2026, 7, 18, 9, 0, 0))]

    result = assemble_news_relevance_analysis(items, now=now)

    assert "noticia reciente relevante" in result.findings[0]


def test_findings_indicate_missing_news_when_none_relevant() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    old_news = [_news(published_at=datetime(2026, 1, 1, 9, 0, 0))]

    result = assemble_news_relevance_analysis(old_news, now=now)

    assert "No se encontraron" in result.findings[0]


def test_findings_indicate_missing_news_for_empty_input() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)

    result = assemble_news_relevance_analysis([], now=now)

    assert "No se encontraron" in result.findings[0]


def test_findings_mention_the_configured_window_size() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)

    result = assemble_news_relevance_analysis([], now=now, days=30)

    assert "30" in result.findings[0]


# --- Métricas de soporte --------------------------------------------------------


def test_supporting_metrics_include_relevant_news_with_expected_fields() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [
        _news(
            title="Apple anuncia nuevo producto",
            summary="Resumen de la noticia.",
            source="Reuters",
            published_at=datetime(2026, 7, 18, 9, 0, 0),
            url="https://example.test/news/1",
        )
    ]

    result = assemble_news_relevance_analysis(items, now=now)

    relevant_news = result.supporting_metrics["relevant_news"]
    assert len(relevant_news) == 1
    entry = relevant_news[0]
    assert entry["title"] == "Apple anuncia nuevo producto"
    assert entry["summary"] == "Resumen de la noticia."
    assert entry["source"] == "Reuters"
    assert entry["published_at"] == "2026-07-18T09:00:00"
    assert entry["url"] == "https://example.test/news/1"


def test_supporting_metrics_use_truncated_summary_when_too_long() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [
        _news(
            summary="abcde fghij klmno",
            published_at=datetime(2026, 7, 18, 9, 0, 0),
        )
    ]

    result = assemble_news_relevance_analysis(items, now=now, summary_max_length=10)

    assert result.supporting_metrics["relevant_news"][0]["summary"] == "abcde..."


def test_supporting_metrics_relevant_news_is_empty_list_when_none_relevant() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)

    result = assemble_news_relevance_analysis([], now=now)

    assert result.supporting_metrics["relevant_news"] == []


def test_supporting_metrics_preserve_relative_order_of_relevant_news() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [
        _news(title="Primera", published_at=datetime(2026, 7, 14, 9, 0, 0)),
        _news(title="Segunda", published_at=datetime(2026, 7, 18, 9, 0, 0)),
        _news(title="Tercera", published_at=datetime(2026, 7, 16, 9, 0, 0)),
    ]

    result = assemble_news_relevance_analysis(items, now=now)

    titles = [entry["title"] for entry in result.supporting_metrics["relevant_news"]]
    assert titles == ["Primera", "Segunda", "Tercera"]


def test_excludes_news_outside_window_from_supporting_metrics() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [
        _news(title="Reciente", published_at=datetime(2026, 7, 18, 9, 0, 0)),
        _news(title="Vieja", published_at=datetime(2026, 1, 1, 9, 0, 0)),
    ]

    result = assemble_news_relevance_analysis(items, now=now)

    titles = [entry["title"] for entry in result.supporting_metrics["relevant_news"]]
    assert titles == ["Reciente"]


# --- Limitaciones ----------------------------------------------------------------


def test_limitations_are_empty_when_relevant_news_found() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [_news(published_at=datetime(2026, 7, 18, 9, 0, 0))]

    result = assemble_news_relevance_analysis(items, now=now)

    assert result.limitations == []


def test_limitations_include_warning_when_no_relevant_news() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    old_news = [_news(published_at=datetime(2026, 1, 1, 9, 0, 0))]

    result = assemble_news_relevance_analysis(old_news, now=now)

    assert len(result.limitations) == 1
    assert "días" in result.limitations[0]


def test_limitations_include_warning_for_empty_input() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)

    result = assemble_news_relevance_analysis([], now=now)

    assert len(result.limitations) == 1


# --- Parámetros por defecto -------------------------------------------------------


def test_uses_seven_days_as_default_window() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    just_inside = _news(published_at=datetime(2026, 7, 13, 12, 0, 1))

    result = assemble_news_relevance_analysis([just_inside], now=now)

    assert len(result.supporting_metrics["relevant_news"]) == 1


def test_uses_280_as_default_summary_max_length() -> None:
    now = datetime(2026, 7, 20, 12, 0, 0)
    items = [_news(summary="x" * 300, published_at=datetime(2026, 7, 18, 9, 0, 0))]

    result = assemble_news_relevance_analysis(items, now=now)

    assert result.supporting_metrics["relevant_news"][0]["summary"] == "x" * 280 + "..."


def test_defaults_now_to_the_current_time_when_not_provided() -> None:
    """Sin `now` explícito, debe evaluarse contra el reloj real, no
    quedarse "congelado" en algún instante fijo."""
    recent = _news(published_at=datetime.now())

    result = assemble_news_relevance_analysis([recent])

    assert len(result.supporting_metrics["relevant_news"]) == 1