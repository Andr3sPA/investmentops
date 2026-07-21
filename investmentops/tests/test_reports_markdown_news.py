# investmentops/tests/test_reports_markdown_news.py
"""Pruebas para la sección "Noticias recientes relevantes" del generador
Markdown (investmentops.reports.markdown.render_markdown).

Cubre la tarea "Añadir la sección 'Noticias recientes relevantes' a la
plantilla Markdown" (TASKS.md, Fase 4, "Reportes"), sobre el formato de
lista Markdown decidido inline en
`investmentops/reports/markdown.py` (ver docstring del módulo, "Sección
'Noticias recientes relevantes'"). No prueba de nuevo las secciones de
salud financiera/valoración/tendencia (ya cubiertas en
`test_reports_markdown.py`/`test_reports_markdown_trend.py`), ni el
motor de noticias relevantes en sí
(`investmentops.analysis_engines.news_relevance`, ya cubierto en sus
propios archivos de prueba) ni su conversión a `AnalysisResult`
(`investmentops.core.orchestrator._news_relevance_result_to_analysis_result`,
ya cubierta en `test_core_orchestrator_news_relevance.py`).
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports import render_markdown


def _news_relevance_result(
    findings: list[str] | None = None,
    supporting_metrics: dict | None = None,
    limitations: list[str] | None = None,
    provenance: AnalysisProvenance | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="news_relevance",
        findings=(
            findings
            if findings is not None
            else ["Se encontraron 2 noticias recientes relevantes en los últimos 7 día(s)."]
        ),
        supporting_metrics=(
            supporting_metrics
            if supporting_metrics is not None
            else {
                "relevant_news": [
                    {
                        "title": "Apple anuncia nuevo producto",
                        "summary": "Resumen de la noticia.",
                        "source": "Reuters",
                        "published_at": "2026-07-18T09:00:00",
                        "url": "https://example.test/news/1",
                    },
                    {
                        "title": "Analistas comentan resultados trimestrales",
                        "summary": "Otro resumen.",
                        "source": "Bloomberg",
                        "published_at": "2026-07-17T08:00:00",
                        "url": "https://example.test/news/2",
                    },
                ]
            }
        ),
        limitations=limitations if limitations is not None else [],
        provenance=(
            provenance
            if provenance is not None
            else AnalysisProvenance(
                ai_provider="none",
                ai_model="deterministic",
                generated_at=datetime.now(timezone.utc),
            )
        ),
    )


# --- Encabezado y ubicación de la sección ------------------------------------


def test_render_includes_empty_news_relevance_header() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert "## Noticias recientes relevantes" in output


def test_render_shows_news_relevance_after_trend_analysis() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.index("## Evolución de ingresos y beneficios") < output.index(
        "## Noticias recientes relevantes"
    )


def test_render_is_the_last_section_of_the_document() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.rstrip("\n").endswith(
        output[output.index("## Noticias recientes relevantes"):].rstrip("\n")
    )


def test_render_keeps_empty_news_relevance_section_when_agent_absent() -> None:
    """Si el motor de noticias relevantes no está en `analysis_results`
    (ej. no se inyectó un proveedor de noticias), la sección conserva
    solo su encabezado vacío. Es la última sección del reporte, por lo
    que basta con verificar todo lo que sigue al encabezado."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Noticias recientes relevantes")
    section_body = (
        output[section_start:]
        .replace("## Noticias recientes relevantes", "")
        .strip()
    )
    assert section_body == ""


# --- Hallazgos -----------------------------------------------------------------


def test_render_includes_news_relevance_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [_news_relevance_result(findings=["Texto de hallazgo de noticias."])],
    )

    output = render_markdown(result)

    assert "Texto de hallazgo de noticias." in output


def test_render_places_news_relevance_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_news_relevance_result(findings=["hallazgo de noticias"])]
    )

    output = render_markdown(result)

    section_start = output.index("## Noticias recientes relevantes")
    assert "hallazgo de noticias" in output[section_start:]
    assert "hallazgo de noticias" not in output[:section_start]


def test_render_news_relevance_section_ignores_other_analysis_results() -> None:
    valuation = AnalysisResult(
        analysis_id="valuation",
        findings=["hallazgo de valoración"],
        supporting_metrics={"price_to_earnings": 20.0},
        limitations=[],
        provenance=AnalysisProvenance(
            ai_provider="anthropic",
            ai_model="claude-sonnet-5",
            generated_at=datetime.now(timezone.utc),
        ),
    )
    result = assemble_research_result("AAPL", [valuation])

    output = render_markdown(result)

    section_start = output.index("## Noticias recientes relevantes")
    assert "hallazgo de valoración" not in output[section_start:]


# --- Lista de noticias relevantes --------------------------------------------


def test_render_includes_one_list_item_per_relevant_news() -> None:
    result = assemble_research_result("AAPL", [_news_relevance_result()])

    output = render_markdown(result)

    assert (
        "- **Apple anuncia nuevo producto** (Reuters, 2026-07-18T09:00:00): "
        "Resumen de la noticia. ([Leer más](https://example.test/news/1))"
    ) in output
    assert (
        "- **Analistas comentan resultados trimestrales** (Bloomberg, "
        "2026-07-17T08:00:00): Otro resumen. "
        "([Leer más](https://example.test/news/2))"
    ) in output


def test_render_preserves_order_of_relevant_news() -> None:
    result = assemble_research_result("AAPL", [_news_relevance_result()])

    output = render_markdown(result)

    first_index = output.index("Apple anuncia nuevo producto")
    second_index = output.index("Analistas comentan resultados trimestrales")
    assert first_index < second_index


def test_render_omits_news_list_when_no_relevant_news() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _news_relevance_result(
                findings=["No se encontraron noticias recientes relevantes en los últimos 7 día(s)."],
                supporting_metrics={"relevant_news": []},
            )
        ],
    )

    output = render_markdown(result)

    assert "- **" not in output[output.index("## Noticias recientes relevantes"):]


def test_render_does_not_duplicate_relevant_news_as_supporting_metrics_list() -> None:
    """A diferencia de salud financiera/valoración, esta sección no vuelca
    `relevant_news` como línea "- clave: valor" genérica."""
    result = assemble_research_result("AAPL", [_news_relevance_result()])

    output = render_markdown(result)

    assert "- relevant_news:" not in output


# --- Limitaciones ----------------------------------------------------------------


def test_render_includes_news_relevance_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _news_relevance_result(
                findings=["No se encontraron noticias recientes relevantes en los últimos 7 día(s)."],
                supporting_metrics={"relevant_news": []},
                limitations=[
                    "No se encontraron noticias recientes relevantes en los últimos 7 día(s)."
                ],
            )
        ],
    )

    output = render_markdown(result)

    assert "**Limitaciones:**" in output
    assert (
        "- No se encontraron noticias recientes relevantes en los últimos 7 día(s)."
        in output
    )


def test_render_omits_news_relevance_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_news_relevance_result(limitations=[])])

    output = render_markdown(result)

    section_start = output.index("## Noticias recientes relevantes")
    assert "**Limitaciones:**" not in output[section_start:]


# --- Procedencia (centinela) ------------------------------------------------------


def test_render_includes_news_relevance_sentinel_provenance() -> None:
    provenance = AnalysisProvenance(
        ai_provider="none",
        ai_model="deterministic",
        generated_at=datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL", [_news_relevance_result(provenance=provenance)]
    )

    output = render_markdown(result)

    assert "**Generado por:** none (deterministic) el" in output
    assert provenance.generated_at.isoformat() in output


def test_render_omits_news_relevance_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Noticias recientes relevantes")
    assert "**Generado por:**" not in output[section_start:]