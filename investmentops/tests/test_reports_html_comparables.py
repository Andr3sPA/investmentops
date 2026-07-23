"""Pruebas para la sección "Comparables del sector" del generador HTML
(investmentops.reports.html.render_html).

Cubre la tarea "Añadir la misma sección [Comparables del sector] a la
plantilla HTML" (TASKS.md, Fase 5, "Reportes"), sobre el formato ya
fijado en `investmentops/reports/markdown.py` (docstring, "Sección
'Comparables del sector'"). Mismo patrón de pruebas ya usado en
`test_reports_markdown_comparables.py`. No prueba de nuevo las demás
secciones (ya cubiertas en `test_reports_html.py`/
`test_reports_html_trend.py`), ni el motor de posicionamiento relativo
en sí (`investmentops.analysis_engines.comparables`, ya cubierto en sus
propios archivos de prueba) ni su conversión a `AnalysisResult`.
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports import render_html


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

    output = render_html(result)

    assert "<h2>Comparables del sector</h2>" in output


def test_render_shows_comparables_after_news_relevance() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.index("<h2>Noticias recientes relevantes</h2>") < output.index(
        "<h2>Comparables del sector</h2>"
    )


def test_render_keeps_empty_comparables_section_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Comparables del sector</h2>")
    remaining_body = output[section_start:].split("</body>")[0]
    section_body = remaining_body.replace(
        "<h2>Comparables del sector</h2>", ""
    ).strip()
    assert section_body == ""


# --- Hallazgos -----------------------------------------------------------------


def test_render_includes_comparables_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL", [_comparables_result(findings=["Texto de hallazgo comparativo."])]
    )

    output = render_html(result)

    assert "<p>Texto de hallazgo comparativo.</p>" in output


def test_render_places_comparables_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_comparables_result(findings=["hallazgo comparativo"])]
    )

    output = render_html(result)

    section_start = output.index("<h2>Comparables del sector</h2>")
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

    output = render_html(result)

    section_start = output.index("<h2>Comparables del sector</h2>")
    assert "hallazgo de noticias" not in output[section_start:]


# --- Métricas de la empresa --------------------------------------------------


def test_render_includes_company_metrics_when_present() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_html(result)

    assert "<h3>Métricas de la empresa</h3>" in output
    assert "<li>net_margin: 0.15</li>" in output
    assert "<li>debt_to_revenue: 0.4</li>" in output
    assert "<li>price_to_earnings: 20.0</li>" in output
    assert "<li>price_to_sales: 3.0</li>" in output


def test_render_company_metrics_do_not_include_ticker_key() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_html(result)

    assert "<li>ticker:" not in output


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

    output = render_html(result)

    assert "<h3>Métricas de la empresa</h3>" not in output


# --- Tabla comparativa --------------------------------------------------------


def test_render_includes_comparison_table_header() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_html(result)

    assert (
        "<tr><th>Métrica</th><th>Par</th><th>Valor empresa</th>"
        "<th>Valor par</th><th>Posición</th></tr>"
    ) in output


def test_render_includes_one_row_per_metric_and_peer() -> None:
    result = assemble_research_result("AAPL", [_comparables_result()])

    output = render_html(result)

    assert "<tr><td>net_margin</td><td>MSFT</td><td>0.15</td><td>0.2</td><td>por_debajo</td></tr>" in output
    assert "<tr><td>debt_to_revenue</td><td>MSFT</td><td>0.4</td><td>0.3</td><td>por_encima</td></tr>" in output
    assert "<tr><td>price_to_earnings</td><td>MSFT</td><td>20.0</td><td>18.0</td><td>por_encima</td></tr>" in output
    assert "<tr><td>price_to_sales</td><td>MSFT</td><td>3.0</td><td>2.5</td><td>por_encima</td></tr>" in output


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

    output = render_html(result)

    assert "<tr><td>net_margin</td><td>MSFT</td><td>0.15</td><td>—</td><td>—</td></tr>" in output


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

    output = render_html(result)

    assert "<table>" not in output


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

    output = render_html(result)

    assert "<h3>Limitaciones</h3>" in output
    assert (
        "<li>No se compara el crecimiento (variación periodo a periodo) frente a "
        "los pares.</li>"
        in output
    )


def test_render_omits_comparables_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_comparables_result(limitations=[])])

    output = render_html(result)

    section_start = output.index("<h2>Comparables del sector</h2>")
    assert "<h3>Limitaciones</h3>" not in output[section_start:]


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

    output = render_html(result)

    assert "Generado por: none (deterministic) el" in output
    assert provenance.generated_at.isoformat() in output


def test_render_omits_comparables_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Comparables del sector</h2>")
    assert "Generado por:" not in output[section_start:]


# --- Escapado de contenido dinámico -----------------------------------------


def test_render_escapes_html_special_characters_in_comparables_findings() -> None:
    result = assemble_research_result(
        "AAPL",
        [_comparables_result(findings=["<script>alert('x')</script> & otros datos"])],
    )

    output = render_html(result)

    assert "<script>alert" not in output
    assert "&lt;script&gt;" in output