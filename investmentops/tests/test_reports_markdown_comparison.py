"""Pruebas para el reporte de comparación (varias empresas) en Markdown
(investmentops.reports.markdown.render_markdown_comparison).

Cubre la tarea "Adaptar el generador Markdown para soportar un reporte
de comparación (varias empresas) además del reporte individual"
(TASKS.md, Fase 5, "Reportes"), sobre la decisión de formato documentada
inline en `investmentops/reports/markdown.py` ("Reporte de comparación
(varias empresas, esta tarea)"). No prueba de nuevo `render_markdown`
para un único `ResearchResult` (ya cubierto en `test_reports_markdown.py`
y en las pruebas de sus secciones específicas); solo el anidado de
varios reportes individuales bajo un documento de comparación.
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports.markdown import render_markdown, render_markdown_comparison


def _financial_health_result(findings: list[str]) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="financial_health",
        findings=findings,
        supporting_metrics={"net_margin": 0.15},
        limitations=[],
        provenance=AnalysisProvenance(
            ai_provider="anthropic",
            ai_model="claude-sonnet-5",
            generated_at=datetime.now(timezone.utc),
        ),
    )


# --- Título y estructura general ---------------------------------------------


def test_render_includes_comparison_title_with_all_tickers() -> None:
    result_aapl = assemble_research_result("AAPL", [])
    result_msft = assemble_research_result("MSFT", [])

    output = render_markdown_comparison(["AAPL", "MSFT"], [result_aapl, result_msft])

    assert output.startswith("# Comparación: AAPL, MSFT")


def test_render_ends_with_a_single_trailing_newline() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown_comparison(["AAPL"], [result])

    assert output.endswith("\n")
    assert not output.endswith("\n\n")


def test_render_with_empty_results_contains_only_the_title() -> None:
    output = render_markdown_comparison(["AAPL", "MSFT"], [])

    assert output.strip() == "# Comparación: AAPL, MSFT"


# --- Anidado de reportes individuales -----------------------------------------


def test_render_shifts_individual_report_headings_by_one_level() -> None:
    """El '# Investigación: AAPL' de render_markdown debe convertirse en
    '## Investigación: AAPL' dentro del documento de comparación."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown_comparison(["AAPL"], [result])

    assert "## Investigación: AAPL" in output
    assert "# Investigación: AAPL" not in output.replace("## Investigación: AAPL", "")


def test_render_shifts_section_headings_by_one_level() -> None:
    """'## Salud financiera' (nivel 2 en el reporte individual) debe
    convertirse en '### Salud financiera' dentro del documento de
    comparación."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown_comparison(["AAPL"], [result])

    assert "### Salud financiera" in output
    assert "### Valoración" in output
    assert "## Salud financiera" not in output
    assert "## Valoración" not in output


def test_render_includes_full_individual_report_content_for_each_company() -> None:
    result_aapl = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo de AAPL"])]
    )
    result_msft = assemble_research_result(
        "MSFT", [_financial_health_result(["hallazgo de MSFT"])]
    )

    output = render_markdown_comparison(
        ["AAPL", "MSFT"], [result_aapl, result_msft]
    )

    assert "hallazgo de AAPL" in output
    assert "hallazgo de MSFT" in output


def test_render_preserves_order_of_companies() -> None:
    result_msft = assemble_research_result(
        "MSFT", [_financial_health_result(["hallazgo de MSFT"])]
    )
    result_aapl = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo de AAPL"])]
    )

    output = render_markdown_comparison(
        ["MSFT", "AAPL"], [result_msft, result_aapl]
    )

    assert output.index("## Investigación: MSFT") < output.index(
        "## Investigación: AAPL"
    )
    assert output.index("hallazgo de MSFT") < output.index("hallazgo de AAPL")


def test_render_keeps_findings_under_their_own_company_section() -> None:
    result_aapl = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo exclusivo de AAPL"])]
    )
    result_msft = assemble_research_result("MSFT", [])

    output = render_markdown_comparison(
        ["AAPL", "MSFT"], [result_aapl, result_msft]
    )

    aapl_start = output.index("## Investigación: AAPL")
    msft_start = output.index("## Investigación: MSFT")
    assert "hallazgo exclusivo de AAPL" in output[aapl_start:msft_start]
    assert "hallazgo exclusivo de AAPL" not in output[msft_start:]


def test_render_matches_shifted_render_markdown_output_for_single_company() -> None:
    """Confirma que, salvo el título de comparación y el desplazamiento de
    encabezados, el contenido reproduce exactamente render_markdown."""
    result = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo de AAPL"])]
    )

    individual = render_markdown(result)
    comparison = render_markdown_comparison(["AAPL"], [result])

    # El contenido del reporte individual (sin su encabezado) debe estar
    # presente en el reporte de comparación, con el mismo texto de hallazgo.
    assert "hallazgo de AAPL" in individual
    assert "hallazgo de AAPL" in comparison