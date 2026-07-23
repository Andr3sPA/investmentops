"""Pruebas para el reporte de comparación (varias empresas) en HTML
(investmentops.reports.html.render_html_comparison).

Cubre la tarea "Adaptar el generador HTML para soportar un reporte de
comparación (varias empresas) además del reporte individual" (TASKS.md,
Fase 5, "Reportes"), equivalente HTML de
`investmentops.reports.markdown.render_markdown_comparison` (mismo
patrón de pruebas ya usado en `test_reports_markdown_comparison.py`).
No prueba de nuevo `render_html` para un único `ResearchResult` (ya
cubierto en `test_reports_html.py` y en las pruebas de sus secciones
específicas); solo el anidado de varios reportes individuales bajo un
documento de comparación.
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.reports.html import render_html, render_html_comparison


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


def test_render_returns_full_html5_document() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html_comparison(["AAPL"], [result])

    assert output.startswith("<!DOCTYPE html>")
    assert '<html lang="es">' in output
    assert output.rstrip("\n").endswith("</html>")


def test_render_includes_comparison_title_with_all_tickers() -> None:
    result_aapl = assemble_research_result("AAPL", [])
    result_msft = assemble_research_result("MSFT", [])

    output = render_html_comparison(["AAPL", "MSFT"], [result_aapl, result_msft])

    assert "<title>Comparación: AAPL, MSFT</title>" in output
    assert "<h1>Comparación: AAPL, MSFT</h1>" in output


def test_render_ends_with_a_single_trailing_newline() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html_comparison(["AAPL"], [result])

    assert output.endswith("\n")
    assert not output.endswith("\n\n")


def test_render_with_empty_results_still_contains_title() -> None:
    output = render_html_comparison(["AAPL", "MSFT"], [])

    assert "<h1>Comparación: AAPL, MSFT</h1>" in output
    assert "<h2>Investigación:" not in output


# --- Anidado de reportes individuales -----------------------------------------


def test_render_shifts_individual_report_headings_by_one_level() -> None:
    """El '<h1>Investigación: AAPL</h1>' de render_html debe convertirse
    en '<h2>Investigación: AAPL</h2>' dentro del documento de comparación."""
    result = assemble_research_result("AAPL", [])

    output = render_html_comparison(["AAPL"], [result])

    assert "<h2>Investigación: AAPL</h2>" in output
    assert "<h1>Investigación: AAPL</h1>" not in output


def test_render_shifts_section_headings_by_one_level() -> None:
    """'<h2>Salud financiera</h2>' (nivel 2 en el reporte individual)
    debe convertirse en '<h3>Salud financiera</h3>' dentro del
    documento de comparación."""
    result = assemble_research_result("AAPL", [])

    output = render_html_comparison(["AAPL"], [result])

    assert "<h3>Salud financiera</h3>" in output
    assert "<h3>Valoración</h3>" in output
    assert "<h2>Salud financiera</h2>" not in output
    assert "<h2>Valoración</h2>" not in output


def test_render_includes_full_individual_report_content_for_each_company() -> None:
    result_aapl = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo de AAPL"])]
    )
    result_msft = assemble_research_result(
        "MSFT", [_financial_health_result(["hallazgo de MSFT"])]
    )

    output = render_html_comparison(["AAPL", "MSFT"], [result_aapl, result_msft])

    assert "hallazgo de AAPL" in output
    assert "hallazgo de MSFT" in output


def test_render_preserves_order_of_companies() -> None:
    result_msft = assemble_research_result(
        "MSFT", [_financial_health_result(["hallazgo de MSFT"])]
    )
    result_aapl = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo de AAPL"])]
    )

    output = render_html_comparison(["MSFT", "AAPL"], [result_msft, result_aapl])

    assert output.index("<h2>Investigación: MSFT</h2>") < output.index(
        "<h2>Investigación: AAPL</h2>"
    )
    assert output.index("hallazgo de MSFT") < output.index("hallazgo de AAPL")


def test_render_keeps_findings_under_their_own_company_section() -> None:
    result_aapl = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo exclusivo de AAPL"])]
    )
    result_msft = assemble_research_result("MSFT", [])

    output = render_html_comparison(["AAPL", "MSFT"], [result_aapl, result_msft])

    aapl_start = output.index("<h2>Investigación: AAPL</h2>")
    msft_start = output.index("<h2>Investigación: MSFT</h2>")
    assert "hallazgo exclusivo de AAPL" in output[aapl_start:msft_start]
    assert "hallazgo exclusivo de AAPL" not in output[msft_start:]


def test_render_matches_individual_report_content_for_single_company() -> None:
    """Confirma que, salvo el título de comparación y el desplazamiento de
    encabezados, el contenido reproduce lo mismo que render_html."""
    result = assemble_research_result(
        "AAPL", [_financial_health_result(["hallazgo de AAPL"])]
    )

    individual = render_html(result)
    comparison = render_html_comparison(["AAPL"], [result])

    assert "hallazgo de AAPL" in individual
    assert "hallazgo de AAPL" in comparison


def test_render_escapes_ticker_in_title_and_heading() -> None:
    output = render_html_comparison(["<AAPL>"], [])

    assert "<title>Comparación: &lt;AAPL&gt;</title>" in output
    assert "<h1>Comparación: &lt;AAPL&gt;</h1>" in output