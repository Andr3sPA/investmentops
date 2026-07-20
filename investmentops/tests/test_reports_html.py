"""Pruebas para el generador HTML (investmentops.reports.html.render_html).

Cubre la tarea "Implementar el volcado de las mismas secciones que en
Markdown (salud financiera, valoración, fuentes)" (TASKS.md, Fase 2,
"Generador HTML"). No prueba el guardado en disco: es una tarea separada
y posterior de la misma sección (ver `test_reports_markdown_save.py`
para el equivalente ya implementado en el generador Markdown, que
`save_html_report` seguirá cuando se implemente).
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.core.research_result import ResearchResult
from investmentops.data_layer import Company
from investmentops.reports import render_html


def _financial_health_result(
    findings: list[str] | None = None,
    supporting_metrics: dict | None = None,
    limitations: list[str] | None = None,
    provenance: AnalysisProvenance | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="financial_health",
        findings=findings if findings is not None else ["La empresa muestra un margen saludable."],
        supporting_metrics=(
            supporting_metrics if supporting_metrics is not None else {"net_margin": 0.15}
        ),
        limitations=limitations if limitations is not None else [],
        provenance=(
            provenance
            if provenance is not None
            else AnalysisProvenance(
                ai_provider="anthropic",
                ai_model="claude-sonnet-5",
                generated_at=datetime.now(timezone.utc),
            )
        ),
    )


def _valuation_result(
    findings: list[str] | None = None,
    supporting_metrics: dict | None = None,
    limitations: list[str] | None = None,
    provenance: AnalysisProvenance | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="valuation",
        findings=(
            findings if findings is not None else ["La empresa parece razonablemente valorada."]
        ),
        supporting_metrics=(
            supporting_metrics if supporting_metrics is not None else {"price_to_earnings": 20.0}
        ),
        limitations=limitations if limitations is not None else [],
        provenance=(
            provenance
            if provenance is not None
            else AnalysisProvenance(
                ai_provider="anthropic",
                ai_model="claude-sonnet-5",
                generated_at=datetime.now(timezone.utc),
            )
        ),
    )


# --- Estructura base -----------------------------------------------------


def test_render_returns_full_html5_document() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.startswith("<!DOCTYPE html>")
    assert '<html lang="es">' in output
    assert output.rstrip("\n").endswith("</html>")


def test_render_includes_charset_meta_tag() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert '<meta charset="utf-8">' in output


def test_render_includes_ticker_in_title_and_heading() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "<title>Investigación: AAPL</title>" in output
    assert "<h1>Investigación: AAPL</h1>" in output


def test_render_includes_generated_at_timestamp() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = assemble_research_result("AAPL", [], generated_at=fixed_time)

    output = render_html(result)

    assert f"Generado: {fixed_time.isoformat()}" in output


def test_render_includes_empty_financial_health_and_valuation_headers() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "<h2>Salud financiera</h2>" in output
    assert "<h2>Valoración</h2>" in output


def test_render_shows_financial_health_before_valuation() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.index("<h2>Salud financiera</h2>") < output.index("<h2>Valoración</h2>")


def test_render_omits_identity_paragraph_when_company_details_are_empty() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.count("<p>") == output.count("Generado:")


def test_render_includes_identity_paragraph_when_company_details_present() -> None:
    result = ResearchResult(
        company=Company(ticker="AAPL", name="Apple Inc.", sector="Tecnología", market="NASDAQ"),
        analysis_results=[],
        failures=[],
        generated_at=datetime.now(timezone.utc),
    )

    output = render_html(result)

    assert "<p>Apple Inc. · Tecnología · NASDAQ</p>" in output


def test_render_does_not_include_failures_section() -> None:
    """Fuera de alcance de esta tarea, mismo criterio que render_markdown."""
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "Fallos parciales" not in output


def test_render_ends_with_a_single_trailing_newline() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert output.endswith("\n")
    assert not output.endswith("\n\n")


# --- Volcado de hallazgos de salud financiera ------------------------------


def test_render_includes_financial_health_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL", [_financial_health_result(findings=["Texto de interpretación del modelo."])]
    )

    output = render_html(result)

    assert "<p>Texto de interpretación del modelo.</p>" in output


def test_render_places_financial_health_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_financial_health_result(findings=["hallazgo de salud financiera"])]
    )

    output = render_html(result)

    section_start = output.index("<h2>Salud financiera</h2>")
    section_end = output.index("<h2>Valoración</h2>")
    assert "hallazgo de salud financiera" in output[section_start:section_end]


def test_render_includes_financial_health_supporting_metrics() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _financial_health_result(
                supporting_metrics={"net_margin": 0.15, "debt_to_revenue": 0.4}
            )
        ],
    )

    output = render_html(result)

    assert "<h3>Métricas de soporte</h3>" in output
    assert "<li>net_margin: 0.15</li>" in output
    assert "<li>debt_to_revenue: 0.4</li>" in output


def test_render_includes_financial_health_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [_financial_health_result(limitations=["Sin datos de liquidez."])],
    )

    output = render_html(result)

    assert "<h3>Limitaciones</h3>" in output
    assert "<li>Sin datos de liquidez.</li>" in output


def test_render_omits_limitations_subsection_when_empty() -> None:
    result = assemble_research_result(
        "AAPL", [_financial_health_result(limitations=[])]
    )

    output = render_html(result)

    assert "<h3>Limitaciones</h3>" not in output


def test_render_keeps_empty_financial_health_section_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Salud financiera</h2>")
    section_end = output.index("<h2>Valoración</h2>")
    section_body = (
        output[section_start:section_end]
        .replace("<h2>Salud financiera</h2>", "")
        .strip()
    )
    assert section_body == ""


def test_render_financial_health_section_ignores_other_analysis_results() -> None:
    result = assemble_research_result(
        "AAPL", [_valuation_result(findings=["hallazgo de valoración"])]
    )

    output = render_html(result)

    section_start = output.index("<h2>Salud financiera</h2>")
    section_end = output.index("<h2>Valoración</h2>")
    assert "hallazgo de valoración" not in output[section_start:section_end]


# --- Volcado de hallazgos de valoración ------------------------------------


def test_render_includes_valuation_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [_valuation_result(findings=["Texto de interpretación del modelo de valoración."])],
    )

    output = render_html(result)

    assert "<p>Texto de interpretación del modelo de valoración.</p>" in output


def test_render_includes_valuation_supporting_metrics() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _valuation_result(
                supporting_metrics={"price_to_earnings": 20.0, "price_to_sales": 3.0}
            )
        ],
    )

    output = render_html(result)

    assert "<li>price_to_earnings: 20.0</li>" in output
    assert "<li>price_to_sales: 3.0</li>" in output


def test_render_includes_valuation_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _valuation_result(
                limitations=[
                    "No se dispone de datos para P/B.",
                    "No se dispone de datos para EV/EBITDA.",
                ]
            )
        ],
    )

    output = render_html(result)

    assert "<li>No se dispone de datos para P/B.</li>" in output
    assert "<li>No se dispone de datos para EV/EBITDA.</li>" in output


def test_render_keeps_empty_valuation_section_when_agent_absent() -> None:
    """Acotada por el encabezado de "Evolución de ingresos y beneficios"
    (nueva desde Fase 3): "Valoración" ya no es la última sección del
    reporte, por lo que la prueba ya no puede tomar todo lo que sigue a
    "<h2>Valoración</h2>" hasta el cierre de `<body>`."""
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    section_start = output.index("<h2>Valoración</h2>")
    section_end = output.index("<h2>Evolución de ingresos y beneficios</h2>")
    section_body = (
        output[section_start:section_end].replace("<h2>Valoración</h2>", "").strip()
    )
    assert section_body == ""

def test_render_includes_both_sections_when_both_agents_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _financial_health_result(findings=["hallazgo de salud financiera"]),
            _valuation_result(findings=["hallazgo de valoración"]),
        ],
    )

    output = render_html(result)

    fh_start = output.index("<h2>Salud financiera</h2>")
    val_start = output.index("<h2>Valoración</h2>")
    assert "hallazgo de salud financiera" in output[fh_start:val_start]
    assert "hallazgo de valoración" in output[val_start:]


# --- Fuentes/procedencia de IA (proveedor, modelo, fecha) ------------------


def test_render_includes_financial_health_provenance() -> None:
    provenance = AnalysisProvenance(
        ai_provider="anthropic",
        ai_model="claude-sonnet-5",
        generated_at=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL", [_financial_health_result(provenance=provenance)]
    )

    output = render_html(result)

    assert "Generado por: anthropic (claude-sonnet-5)" in output
    assert provenance.generated_at.isoformat() in output


def test_render_places_financial_health_provenance_under_its_own_section() -> None:
    fh_provenance = AnalysisProvenance(
        ai_provider="anthropic",
        ai_model="claude-sonnet-5",
        generated_at=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
    )
    val_provenance = AnalysisProvenance(
        ai_provider="anthropic",
        ai_model="claude-haiku-4-5",
        generated_at=datetime(2026, 7, 16, 11, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL",
        [
            _financial_health_result(provenance=fh_provenance),
            _valuation_result(provenance=val_provenance),
        ],
    )

    output = render_html(result)

    fh_start = output.index("<h2>Salud financiera</h2>")
    val_start = output.index("<h2>Valoración</h2>")
    assert "claude-sonnet-5" in output[fh_start:val_start]
    assert "claude-haiku-4-5" not in output[fh_start:val_start]
    assert "claude-haiku-4-5" in output[val_start:]


def test_render_omits_provenance_when_agent_absent() -> None:
    result = assemble_research_result("AAPL", [])

    output = render_html(result)

    assert "Generado por:" not in output


# --- Escapado de contenido dinámico -----------------------------------------


def test_render_escapes_html_special_characters_in_findings() -> None:
    """Los hallazgos provienen de un modelo de IA y no deben interpretarse
    como marcado HTML: '<', '>' y '&' deben escaparse."""
    result = assemble_research_result(
        "AAPL",
        [_financial_health_result(findings=["<script>alert('x')</script> & otros datos"])],
    )

    output = render_html(result)

    assert "<script>alert" not in output
    assert "&lt;script&gt;" in output
    assert "&amp;" in output


def test_render_escapes_ticker_in_title_and_heading() -> None:
    result = ResearchResult(
        company=Company(ticker="<AAPL>", name="", sector="", market=""),
        analysis_results=[],
        failures=[],
        generated_at=datetime.now(timezone.utc),
    )

    output = render_html(result)

    assert "<title>Investigación: &lt;AAPL&gt;</title>" in output
    assert "<h1>Investigación: &lt;AAPL&gt;</h1>" in output
