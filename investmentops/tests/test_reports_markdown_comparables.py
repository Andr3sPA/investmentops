"""Pruebas para la sección "Comparables del sector" del generador
Markdown (investmentops.reports.markdown.render_markdown).

Cubre la tarea "Añadir la sección 'Comparables del sector' a la
plantilla Markdown" (TASKS.md, Fase 5, "Reportes"), sobre el formato
decidido inline en `investmentops/reports/markdown.py` (ver docstring
del módulo, "Sección 'Comparables del sector'"). No prueba de nuevo las
demás secciones (ya cubiertas en `test_reports_markdown.py`/
`test_reports_markdown_trend.py`/`test_reports_markdown_news.py`), ni el
motor de posicionamiento relativo en sí
(`investmentops.analysis_engines.comparables`, ya cubierto en sus
propios archivos de prueba) ni su conversión a `AnalysisResult`
(`investmentops.core.orchestrator._comparables_analysis_result_to_analysis_result`).
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports import render_markdown


def _comparables_result(
    findings: list[str] | None = None,
    supporting_metrics: dict | None = None,
    limitations: list[str] | None = None,
    provenance: AnalysisProvenance | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="comparables",
        findings=(
            findings
            if findings is not None
            else [
                "En margen neto, la empresa está por encima de 0, por debajo de "
                "1, e igual a 0 de 1 par(es) comparable(s)."
            ]
        ),
        supporting_metrics=(
            supporting_metrics
            if supporting_metrics is not None
            else {
                "company": {
                    "ticker": "AAPL",
                    "net_margin": 0.15,
                    "debt_to_revenue": 0.4,
                    "price_to_earnings": 20.0,
                    "price_to_sales": 3.0,
                },
                "comparisons": {
                    "net_margin": [
                        {
                            "peer_ticker": "MSFT",
                            "company_value": 0.15,
                            "peer_value": 0.2,
                            "position": "por_debajo",
                        }
                    ],
                    "debt_to_revenue": [
                        {
                            "peer_ticker": "MSFT",
                            "company_value": 0.4,
                            "peer_value": 0.3,
                            "position": "por_encima",
                        }
                    ],
                    "price_to_earnings": [
                        {
                            "peer_ticker": "MSFT",
                            "company_value": 20.0,
                            "peer_value": 18.0,
                            "position": "por_encima",
                        }
                    ],
                    "price_to_sales": [
                        {
                            "peer_ticker": "MSFT",
                            "company_value": 3.0,
                            "peer_value": 2.5,
                            "position": "por_encima",
                        }
                    ],
                },
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


def test_render_includes_empty_comparables_header() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert "## Comparables del sector" in output


def test_render_shows_comparables_after_news_relevance() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.index("## Noticias recientes relevantes") < output.index(
        "## Comparables del sector"
    )


def test_render_is_the_last_section_of_the_document() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.rstrip("\n").endswith(
        output[output.index("## Comparables del sector"):].rstrip("\n")
    )


def test_render_keeps_empty_comparables_section_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Comparables del sector")
    section_body = (
        output[section_start:].replace("## Comparables del sector", "").strip()
    )
    assert section_body == ""


# --- Hallazgos -----------------------------------------------------------------


def test_render_includes_comparables_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL", [_comparables_result(findings=["Texto de hallazgo comparativo."])]
    )

    output = render_markdown(result)

    assert "Texto de hallazgo comparativo." in output


def test_render_places_comparables_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_comparables_result(findings=["hallazgo comparativo"])]
    )

    output = render_markdown(result)

    section_start = output.index("## Comparables del sector")
    assert "hallazgo comparativo" in output[section_start:]
    assert "hallazgo comparativo" not in output[:section_start]


def test_render_comparables_section_ignores_other_analysis_results() -> None:
    news_relevance = AnalysisResult(
        analysis_id="news_relevance",
        findings=["hallazgo de noticias"],
        supporting_metrics={"relevant_news": []},
        limitations=[],
        provenance=AnalysisProvenance(
            ai_provider="none",
            ai_model="deterministic",
            generated_at=datetime.now(timezone.utc),
        ),
    )
    result = assemble_research_result("AAPL", [news_relevance])

    output = render_markdown(result)

    section_start = output.index("## Comparables del sector")
    assert "hallazgo de noticias" not in output[section_start:]


# --- Métricas de la empresa --------------------------------------------------


def test_render_includes_company_metrics_when_present() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_markdown(result)

    assert "**Métricas de la empresa:**" in output
    assert "- net_margin: 0.15" in output
    assert "- debt_to_revenue: 0.4" in output
    assert "- price_to_earnings: 20.0" in output
    assert "- price_to_sales: 3.0" in output


def test_render_company_metrics_do_not_include_ticker_key() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_markdown(result)

    assert "- ticker:" not in output


def test_render_omits_company_metrics_section_when_absent() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _comparables_result(
                findings=["No hay empresas pares disponibles."],
                supporting_metrics={"company": {}, "comparisons": {}},
            )
        ],
    )

    output = render_markdown(result)

    assert "**Métricas de la empresa:**" not in output


# --- Tabla comparativa --------------------------------------------------------


def test_render_includes_comparison_table_header() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_markdown(result)

    assert "| Métrica | Par | Valor empresa | Valor par | Posición |" in output
    assert "|---|---|---|---|---|" in output


def test_render_includes_one_row_per_metric_and_peer() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_markdown(result)

    assert "| net_margin | MSFT | 0.15 | 0.2 | por_debajo |" in output
    assert "| debt_to_revenue | MSFT | 0.4 | 0.3 | por_encima |" in output
    assert "| price_to_earnings | MSFT | 20.0 | 18.0 | por_encima |" in output
    assert "| price_to_sales | MSFT | 3.0 | 2.5 | por_encima |" in output


def test_render_shows_em_dash_for_non_calculable_value_and_position() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _comparables_result(
                supporting_metrics={
                    "company": {"ticker": "AAPL", "net_margin": 0.15},
                    "comparisons": {
                        "net_margin": [
                            {
                                "peer_ticker": "MSFT",
                                "company_value": 0.15,
                                "peer_value": None,
                                "position": None,
                            }
                        ]
                    },
                }
            )
        ],
    )

    output = render_markdown(result)

    assert "| net_margin | MSFT | 0.15 | — | — |" in output


def test_render_omits_table_when_no_peers() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _comparables_result(
                findings=["No hay empresas pares disponibles."],
                supporting_metrics={
                    "company": {"ticker": "AAPL", "net_margin": 0.15},
                    "comparisons": {
                        "net_margin": [],
                        "debt_to_revenue": [],
                        "price_to_earnings": [],
                        "price_to_sales": [],
                    },
                },
            )
        ],
    )

    output = render_markdown(result)

    assert "| Métrica |" not in output


# --- Limitaciones ----------------------------------------------------------------


def test_render_includes_comparables_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _comparables_result(
                limitations=[
                    "No se compara el crecimiento (variación periodo a periodo) "
                    "frente a los pares."
                ]
            )
        ],
    )

    output = render_markdown(result)

    assert "**Limitaciones:**" in output
    assert (
        "- No se compara el crecimiento (variación periodo a periodo) frente a "
        "los pares."
        in output
    )


def test_render_omits_comparables_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_comparables_result(limitations=[])])

    output = render_markdown(result)

    section_start = output.index("## Comparables del sector")
    assert "**Limitaciones:**" not in output[section_start:]


# --- Procedencia (centinela) ------------------------------------------------------


def test_render_includes_comparables_sentinel_provenance() -> None:
    provenance = AnalysisProvenance(
        ai_provider="none",
        ai_model="deterministic",
        generated_at=datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL", [_comparables_result(provenance=provenance)]
    )

    output = render_markdown(result)

    assert "**Generado por:** none (deterministic) el" in output
    assert provenance.generated_at.isoformat() in output


def test_render_omits_comparables_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Comparables del sector")
    assert "**Generado por:**" not in output[section_start:]