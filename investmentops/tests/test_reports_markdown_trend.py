"""Pruebas para la sección "Evolución de ingresos y beneficios" del
generador Markdown (investmentops.reports.markdown.render_markdown).

Cubre la tarea "Añadir la sección 'Evolución de ingresos y beneficios' a
la plantilla Markdown, conforme al formato ya decidido" (TASKS.md, Fase
3, "Reportes"), sobre el formato fijado en
`investmentops/reports/TREND_PRESENTATION.md`. No prueba de nuevo las
secciones de salud financiera/valoración (ya cubiertas en
`test_reports_markdown.py`), ni el motor de tendencia en sí
(`investmentops.analysis_engines.trends`, ya cubierto en sus propios
archivos de prueba) ni su conversión a `AnalysisResult`
(`investmentops.core.orchestrator._trend_analysis_result_to_analysis_result`,
ya cubierta en `test_core_orchestrator_trend_analysis.py`).
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports import render_markdown


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

    output = render_markdown(result)

    assert "## Evolución de ingresos y beneficios" in output


def test_render_shows_trend_analysis_after_valuation() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.index("## Valoración") < output.index(
        "## Evolución de ingresos y beneficios"
    )


def test_render_keeps_empty_trend_section_when_agent_absent() -> None:
    """Si el motor de tendencia no está en `analysis_results` (ej. el
    proveedor no soporta series históricas), la sección conserva solo su
    encabezado vacío."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Evolución de ingresos y beneficios")
    section_body = (
        output[section_start:]
        .replace("## Evolución de ingresos y beneficios", "")
        .strip()
    )
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

    output = render_markdown(result)

    assert "Texto de interpretación de la tendencia de ingresos." in output


def test_render_places_trend_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_trend_analysis_result(findings=["hallazgo de tendencia"])]
    )

    output = render_markdown(result)

    section_start = output.index("## Evolución de ingresos y beneficios")
    assert "hallazgo de tendencia" in output[section_start:]
    assert "hallazgo de tendencia" not in output[:section_start]


def test_render_trend_section_ignores_other_analysis_results() -> None:
    from investmentops.analysis_engines.contracts import AnalysisProvenance as _P

    financial_health = AnalysisResult(
        analysis_id="financial_health",
        findings=["hallazgo de salud financiera"],
        supporting_metrics={"net_margin": 0.1},
        limitations=[],
        provenance=_P(
            ai_provider="anthropic",
            ai_model="claude-sonnet-5",
            generated_at=datetime.now(timezone.utc),
        ),
    )
    result = assemble_research_result("AAPL", [financial_health])

    output = render_markdown(result)

    section_start = output.index("## Evolución de ingresos y beneficios")
    assert "hallazgo de salud financiera" not in output[section_start:]


# --- Tabla de variación periodo a periodo ------------------------------------


def test_render_includes_growth_table_header() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result()])

    output = render_markdown(result)

    assert "| Periodo | Ingresos (var.) | Beneficios (var.) |" in output
    assert "|---|---|---|" in output


def test_render_includes_one_row_per_period_with_signed_percentages() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result()])

    output = render_markdown(result)

    assert "| 2025-12-31 | +8.3% | +8.3% |" in output
    assert "| 2024-12-31 | -5.3% | -10.0% |" in output


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

    output = render_markdown(result)

    assert "| 2025-12-31 | — | +5.0% |" in output


def test_render_omits_table_when_both_period_mappings_are_empty() -> None:
    """Serie de un solo periodo (o vacía): sin datos de variación que mostrar."""
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

    output = render_markdown(result)

    assert "| Periodo |" not in output


def test_render_does_not_duplicate_aggregate_trend_as_supporting_metrics_list() -> None:
    """A diferencia de salud financiera/valoración, esta sección no vuelca
    `revenue_trend`/`net_income_trend` como línea "- clave: valor": ya
    están incluidos en el texto de los hallazgos."""
    result = assemble_research_result("AAPL", [_trend_analysis_result()])

    output = render_markdown(result)

    assert "- revenue_trend:" not in output
    assert "- net_income_trend:" not in output


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

    output = render_markdown(result)

    assert "Se detectó un hueco irregular en la serie." in output


def test_render_omits_trend_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_trend_analysis_result(limitations=[])])

    output = render_markdown(result)

    section_start = output.index("## Evolución de ingresos y beneficios")
    assert "**Limitaciones:**" not in output[section_start:]


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

    output = render_markdown(result)

    assert "**Generado por:** none (deterministic) el" in output
    assert provenance.generated_at.isoformat() in output


def test_render_omits_trend_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Evolución de ingresos y beneficios")
    assert "**Generado por:**" not in output[section_start:]
