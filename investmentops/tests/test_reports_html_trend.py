"""Pruebas para la sección "Evolución de ingresos y beneficios" del
generador HTML (investmentops.reports.html.render_html).

Cubre la tarea "Añadir la misma sección [Evolución de ingresos y
beneficios] a la plantilla HTML, conforme al formato ya decidido"
(TASKS.md, Fase 3, "Reportes"), sobre el formato fijado en
`investmentops/reports/TREND_PRESENTATION.md`. Mismo patrón de pruebas ya
usado en `test_reports_markdown_trend.py` para el equivalente Markdown.
No prueba de nuevo las secciones de salud financiera/valoración (ya
cubiertas en `test_reports_html.py`), ni el motor de tendencia en sí
(`investmentops.analysis_engines.trends`) ni su conversión a
`AnalysisResult`
(`investmentops.core.orchestrator._trend_analysis_result_to_analysis_result`,
ya cubierta en `test_core_orchestrator_trend_analysis.py`).
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports import render_html


def _trend_analysis_result(
    findings: list[str] | None = None,
    supporting_metrics: dict | None = None,
    limitations: list[str] | None = None,
    provenance: AnalysisProvenance | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="trend_analysis",
        findings=(
            findings
            if findings is not None
            else [
                "Los ingresos muestran una tendencia creciente en los periodos analizados.",
                "Los beneficios muestran una tendencia creciente en los periodos analizados.",
            ]
        ),
        supporting_metrics=(
            supporting_metrics
            if supporting_metrics is not None
            else {
                "revenue_trend": "creciente",
                "net_income_trend": "creciente",
                "revenue_growth_by_period": {
                    "2025-12-31": 0.0833333333,
                    "2024-12-31": -0.0526315789,
                },
                "net_income_growth_by_period": {
                    "2025-12-31": 0.0833333333,
                    "2024-12-31": -0.1,
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


def test_render_includes_empty_trend_analysis_header() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "<h2>Evolución de ingresos y beneficios</h2>" in output


def test_render_shows_trend_analysis_after_valuation() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.index("<h2>Valoración</h2>") < output.index(
        "<h2>Evolución de ingresos y beneficios</h2>"
    )


def test_render_keeps_empty_trend_section_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Evolución de ingresos y beneficios</h2>")
    remaining_body = output[section_start:].split("</body>")[0]
    section_body = remaining_body.replace(
        "<h2>Evolución de ingresos y beneficios</h2>", ""
    ).strip()
    assert section_body == ""


# --- Hallazgos -----------------------------------------------------------------


def test_render_includes_trend_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _trend_analysis_result(
                findings=["Texto de interpretación de la tendencia de ingresos."]
            )
        ],
    )

    output = render_html(result)

    assert "<p>Texto de interpretación de la tendencia de ingresos.</p>" in output


def test_render_places_trend_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_trend_analysis_result(findings=["hallazgo de tendencia"])]
    )

    output = render_html(result)

    section_start = output.index("<h2>Evolución de ingresos y beneficios</h2>")
    assert "hallazgo de tendencia" in output[section_start:]
    assert "hallazgo de tendencia" not in output[:section_start]


def test_render_trend_section_ignores_other_analysis_results() -> None:
    financial_health = AnalysisResult(
        analysis_id="financial_health",
        findings=["hallazgo de salud financiera"],
        supporting_metrics={"net_margin": 0.1},
        limitations=[],
        provenance=AnalysisProvenance(
            ai_provider="anthropic",
            ai_model="claude-sonnet-5",
            generated_at=datetime.now(timezone.utc),
        ),
    )
    result = assemble_research_result("AAPL", [financial_health])

    output = render_html(result)

    section_start = output.index("<h2>Evolución de ingresos y beneficios</h2>")
    assert "hallazgo de salud financiera" not in output[section_start:]


# --- Tabla de variación periodo a periodo ------------------------------------


def test_render_includes_growth_table_header() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result()])

    output = render_html(result)

    assert (
        "<tr><th>Periodo</th><th>Ingresos (var.)</th><th>Beneficios (var.)</th></tr>"
        in output
    )


def test_render_includes_one_row_per_period_with_signed_percentages() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result()])

    output = render_html(result)

    assert "<tr><td>2025-12-31</td><td>+8.3%</td><td>+8.3%</td></tr>" in output
    assert "<tr><td>2024-12-31</td><td>-5.3%</td><td>-10.0%</td></tr>" in output


def test_render_shows_em_dash_for_non_calculable_period() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _trend_analysis_result(
                supporting_metrics={
                    "revenue_trend": None,
                    "net_income_trend": "creciente",
                    "revenue_growth_by_period": {"2025-12-31": None},
                    "net_income_growth_by_period": {"2025-12-31": 0.05},
                }
            )
        ],
    )

    output = render_html(result)

    assert "<tr><td>2025-12-31</td><td>—</td><td>+5.0%</td></tr>" in output


def test_render_omits_table_when_both_period_mappings_are_empty() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _trend_analysis_result(
                findings=["No hay suficientes datos para determinar una tendencia de ingresos."],
                supporting_metrics={
                    "revenue_trend": None,
                    "net_income_trend": None,
                    "revenue_growth_by_period": {},
                    "net_income_growth_by_period": {},
                },
            )
        ],
    )

    output = render_html(result)

    assert "<table>" not in output


def test_render_does_not_duplicate_aggregate_trend_as_supporting_metrics_list() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result()])

    output = render_html(result)

    assert "<li>revenue_trend:" not in output
    assert "<li>net_income_trend:" not in output


# --- Limitaciones ----------------------------------------------------------------


def test_render_includes_trend_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _trend_analysis_result(
                limitations=["Se detectó un hueco irregular en la serie."]
            )
        ],
    )

    output = render_html(result)

    assert "<li>Se detectó un hueco irregular en la serie.</li>" in output


def test_render_omits_trend_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result(limitations=[])])

    output = render_html(result)

    section_start = output.index("<h2>Evolución de ingresos y beneficios</h2>")
    assert "<h3>Limitaciones</h3>" not in output[section_start:]


# --- Procedencia (centinela) ------------------------------------------------------


def test_render_includes_trend_sentinel_provenance() -> None:
    provenance = AnalysisProvenance(
        ai_provider="none",
        ai_model="deterministic",
        generated_at=datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL", [_trend_analysis_result(provenance=provenance)]
    )

    output = render_html(result)

    assert "Generado por: none (deterministic) el" in output
    assert provenance.generated_at.isoformat() in output


def test_render_omits_trend_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Evolución de ingresos y beneficios</h2>")
    assert "Generado por:" not in output[section_start:]