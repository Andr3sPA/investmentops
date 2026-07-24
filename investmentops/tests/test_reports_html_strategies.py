# investmentops/tests/test_reports_html_strategies.py
"""Pruebas para la sección "Lecturas por estrategia de inversión" del
generador HTML (investmentops.reports.html.render_html).

Cubre la tarea "Añadir la misma sección [Lecturas por estrategia de
inversión] a la plantilla HTML" (TASKS.md, Fase 6, "Reportes"). No
prueba de nuevo las demás secciones (ya cubiertas en
`test_reports_html.py`/`test_reports_html_trend.py`/
`test_reports_html_comparables.py`), ni los agentes de estrategia en sí
(`investmentops.analysis_engines.value`/`growth`/`quality`, ya cubiertos
en sus propios archivos de prueba) ni su registro en el orquestador
(`run_value_engine`/`run_growth_engine`/`run_quality_engine`, ya
cubiertos en `test_core_orchestrator_strategies.py`/
`test_core_orchestrator_strategies_integration.py`). Mismo patrón de
pruebas ya usado en `test_reports_markdown_strategies.py`.
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports import render_html


def _strategy_result(
    analysis_id: str,
    findings: list[str],
    supporting_metrics: dict,
    limitations: list[str] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        findings=findings,
        supporting_metrics=supporting_metrics,
        limitations=limitations if limitations is not None else [],
        provenance=AnalysisProvenance(
            ai_provider="anthropic",
            ai_model="claude-sonnet-5",
            generated_at=datetime.now(timezone.utc),
        ),
    )


def _value_result(**overrides) -> AnalysisResult:
    return _strategy_result(
        "value",
        overrides.get("findings", ["Lectura de value investing."]),
        overrides.get(
            "supporting_metrics",
            {"price_to_earnings": 20.0, "price_to_sales": 3.0, "net_margin": 0.15},
        ),
        overrides.get("limitations"),
    )


def _growth_result(**overrides) -> AnalysisResult:
    return _strategy_result(
        "growth",
        overrides.get("findings", ["Lectura de growth investing."]),
        overrides.get("supporting_metrics", {"revenue_trend": "creciente"}),
        overrides.get("limitations"),
    )


def _quality_result(**overrides) -> AnalysisResult:
    return _strategy_result(
        "quality",
        overrides.get("findings", ["Lectura de quality investing."]),
        overrides.get(
            "supporting_metrics", {"net_margin": 0.15, "debt_to_revenue": 0.4}
        ),
        overrides.get("limitations"),
    )


# --- Encabezados y ubicación de la sección -----------------------------------


def test_render_includes_section_header() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "<h2>Lecturas por estrategia de inversión</h2>" in output


def test_render_shows_section_after_comparables() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.index("<h2>Comparables del sector</h2>") < output.index(
        "<h2>Lecturas por estrategia de inversión</h2>"
    )


def test_render_includes_empty_subheaders_for_all_three_strategies() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "<h3>Value investing</h3>" in output
    assert "<h3>Growth investing</h3>" in output
    assert "<h3>Calidad (quality investing)</h3>" in output


def test_render_shows_strategy_subheaders_in_order() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.index("<h3>Value investing</h3>") < output.index(
        "<h3>Growth investing</h3>"
    )
    assert output.index("<h3>Growth investing</h3>") < output.index(
        "<h3>Calidad (quality investing)</h3>"
    )


def test_render_is_the_last_section_of_the_document() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Lecturas por estrategia de inversión</h2>")
    remaining_body = output[section_start:].split("</body>")[0]
    assert remaining_body.strip() != ""


def test_render_keeps_empty_strategy_subsections_when_agents_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h3>Value investing</h3>")
    remaining_body = output[section_start:].split("</body>")[0]
    section_body = remaining_body.replace("<h3>Value investing</h3>", "")
    section_body = section_body.replace("<h3>Growth investing</h3>", "")
    section_body = section_body.replace("<h3>Calidad (quality investing)</h3>", "")
    assert section_body.strip() == ""


# --- Hallazgos por estrategia -------------------------------------------------


def test_render_includes_value_findings_under_its_own_subsection() -> None:
    result = assemble_research_result(
        "AAPL", [_value_result(findings=["hallazgo de value"])]
    )

    output = render_html(result)

    section_start = output.index("<h3>Value investing</h3>")
    section_end = output.index("<h3>Growth investing</h3>")
    assert "hallazgo de value" in output[section_start:section_end]


def test_render_includes_growth_findings_under_its_own_subsection() -> None:
    result = assemble_research_result(
        "AAPL", [_growth_result(findings=["hallazgo de growth"])]
    )

    output = render_html(result)

    section_start = output.index("<h3>Growth investing</h3>")
    section_end = output.index("<h3>Calidad (quality investing)</h3>")
    assert "hallazgo de growth" in output[section_start:section_end]


def test_render_includes_quality_findings_under_its_own_subsection() -> None:
    result = assemble_research_result(
        "AAPL", [_quality_result(findings=["hallazgo de calidad"])]
    )

    output = render_html(result)

    section_start = output.index("<h3>Calidad (quality investing)</h3>")
    assert "hallazgo de calidad" in output[section_start:]


def test_render_shows_all_three_strategies_when_all_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _value_result(findings=["hallazgo de value"]),
            _growth_result(findings=["hallazgo de growth"]),
            _quality_result(findings=["hallazgo de calidad"]),
        ],
    )

    output = render_html(result)

    value_start = output.index("<h3>Value investing</h3>")
    growth_start = output.index("<h3>Growth investing</h3>")
    quality_start = output.index("<h3>Calidad (quality investing)</h3>")
    assert "hallazgo de value" in output[value_start:growth_start]
    assert "hallazgo de growth" in output[growth_start:quality_start]
    assert "hallazgo de calidad" in output[quality_start:]


def test_render_does_not_merge_strategies_into_a_single_reading() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _value_result(findings=["exclusivo de value"]),
            _quality_result(findings=["exclusivo de calidad"]),
        ],
    )

    output = render_html(result)

    value_start = output.index("<h3>Value investing</h3>")
    growth_start = output.index("<h3>Growth investing</h3>")
    assert "exclusivo de calidad" not in output[value_start:growth_start]


def test_render_strategy_sections_ignore_other_analysis_results() -> None:
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

    section_start = output.index("<h2>Lecturas por estrategia de inversión</h2>")
    assert "hallazgo de salud financiera" not in output[section_start:]


# --- Métricas de soporte ------------------------------------------------------


def test_render_includes_value_supporting_metrics() -> None:
    result = assemble_research_result(
        "AAPL",
        [_value_result(supporting_metrics={"price_to_earnings": 20.0, "price_to_sales": 3.0})],
    )

    output = render_html(result)

    assert "<li>price_to_earnings: 20.0</li>" in output
    assert "<li>price_to_sales: 3.0</li>" in output


def test_render_includes_growth_supporting_metrics() -> None:
    result = assemble_research_result(
        "AAPL", [_growth_result(supporting_metrics={"revenue_trend": "creciente"})]
    )

    output = render_html(result)

    assert "<li>revenue_trend: creciente</li>" in output


def test_render_includes_quality_supporting_metrics() -> None:
    result = assemble_research_result(
        "AAPL", [_quality_result(supporting_metrics={"net_margin": 0.15})]
    )

    output = render_html(result)

    assert "<li>net_margin: 0.15</li>" in output


# --- Limitaciones y procedencia ------------------------------------------------


def test_render_includes_strategy_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _value_result(
                limitations=[
                    "Esta interpretación corresponde exclusivamente al marco de "
                    "value investing."
                ]
            )
        ],
    )

    output = render_html(result)

    assert (
        "<li>Esta interpretación corresponde exclusivamente al marco de value "
        "investing.</li>"
        in output
    )


def test_render_omits_strategy_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_value_result(limitations=[])])

    output = render_html(result)

    section_start = output.index("<h3>Value investing</h3>")
    section_end = output.index("<h3>Growth investing</h3>")
    assert "<h3>Limitaciones</h3>" not in output[section_start:section_end]


def test_render_includes_real_ai_provenance_for_each_strategy() -> None:
    """A diferencia de tendencia/noticias/comparables (procedencia
    centinela), las estrategias tienen procedencia de IA real."""
    provenance = AnalysisProvenance(
        ai_provider="anthropic",
        ai_model="claude-haiku-4-5",
        generated_at=datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL",
        [
            AnalysisResult(
                analysis_id="value",
                findings=["hallazgo"],
                supporting_metrics={"price_to_earnings": 20.0},
                limitations=[],
                provenance=provenance,
            )
        ],
    )

    output = render_html(result)

    assert "Generado por: anthropic (claude-haiku-4-5)" in output
    assert provenance.generated_at.isoformat() in output


def test_render_omits_strategy_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Lecturas por estrategia de inversión</h2>")
    assert "Generado por:" not in output[section_start:]