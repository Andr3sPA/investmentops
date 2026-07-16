"""Pruebas para la plantilla base del generador Markdown
(investmentops.reports.markdown.render_markdown).

Cubre la tarea "Implementar la plantilla base de reporte en Markdown
(encabezados, secciones vacías)" (TASKS.md, Fase 2, "Generador
Markdown"). No prueba el volcado de hallazgos/métricas/limitaciones ni
la sección de fuentes/procedencia, ni el guardado en disco: esas son
tareas separadas y posteriores de la misma sección.
"""

from datetime import datetime, timezone

from investmentops.core.orchestrator import assemble_research_result
from investmentops.data_layer import Company
from investmentops.core.research_result import ResearchResult
from investmentops.reports import render_markdown


def test_render_includes_company_ticker_as_title() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.startswith("# Investigación: AAPL")


def test_render_includes_generated_at_timestamp() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = assemble_research_result("AAPL", [], generated_at=fixed_time)

    output = render_markdown(result)

    assert f"Generado: {fixed_time.isoformat()}" in output


def test_render_includes_empty_financial_health_and_valuation_headers() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert "## Salud financiera" in output
    assert "## Valoración" in output


def test_render_shows_financial_health_before_valuation() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.index("## Salud financiera") < output.index("## Valoración")


def test_render_omits_identity_line_when_company_details_are_empty() -> None:
    """En Fase 1, `Company.name`/`sector`/`market` siempre están vacíos
    (ver `assemble_research_result`); la plantilla no debe imprimir una
    línea de identidad vacía en ese caso."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    lines = output.splitlines()
    assert lines[1] == ""
    assert "Generado:" in lines[2]


def test_render_includes_identity_line_when_company_details_present() -> None:
    result = ResearchResult(
        company=Company(ticker="AAPL", name="Apple Inc.", sector="Tecnología", market="NASDAQ"),
        analysis_results=[],
        failures=[],
        generated_at=datetime.now(timezone.utc),
    )

    output = render_markdown(result)

    assert "Apple Inc. · Tecnología · NASDAQ" in output


def test_render_does_not_include_failures_section_yet() -> None:
    """La sección de fallos parciales es alcance de una tarea posterior
    (volcado de contenido), no de la plantilla base."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert "Fallos parciales" not in output


def test_render_ends_with_a_single_trailing_newline() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert output.endswith("\n")
    assert not output.endswith("\n\n")
