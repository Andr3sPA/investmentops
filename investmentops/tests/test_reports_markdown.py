"""Pruebas para el generador Markdown (investmentops.reports.markdown.render_markdown).

Cubre cuatro tareas de TASKS.md, Fase 2, "Generador Markdown":

- "Implementar la plantilla base de reporte en Markdown (encabezados,
  secciones vacías)."
- "Implementar el volcado de los hallazgos de salud financiera en la
  sección correspondiente."
- "Implementar el volcado de los hallazgos de valoración en la sección
  correspondiente."
- "Implementar la sección de fuentes/procedencia (qué proveedor, qué
  fecha) al final del reporte." (nuevas pruebas en este archivo).

No prueba el guardado en disco: es una tarea separada y posterior de la
misma sección. La sección "Evolución de ingresos y beneficios" (Fase 3)
tiene sus propias pruebas en `test_reports_markdown_trend.py`; este
archivo solo se ajustó en el punto donde una prueba asumía que
"Valoración" era la última sección del reporte, supuesto que dejó de
cumplirse al agregarse esa nueva sección después.
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.core.orchestrator import assemble_research_result
from investmentops.data_layer import Company
from investmentops.core.research_result import ResearchResult
from investmentops.reports import render_markdown


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


# --- Volcado de hallazgos de salud financiera --------------------------------


def test_render_includes_financial_health_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL", [_financial_health_result(findings=["Texto de interpretación del modelo."])]
    )

    output = render_markdown(result)

    assert "Texto de interpretación del modelo." in output


def test_render_places_financial_health_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL", [_financial_health_result(findings=["hallazgo de salud financiera"])]
    )

    output = render_markdown(result)

    section_start = output.index("## Salud financiera")
    section_end = output.index("## Valoración")
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

    output = render_markdown(result)

    assert "net_margin" in output
    assert "0.15" in output
    assert "debt_to_revenue" in output
    assert "0.4" in output


def test_render_includes_financial_health_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [_financial_health_result(limitations=["Sin datos de liquidez."])],
    )

    output = render_markdown(result)

    assert "Sin datos de liquidez." in output


def test_render_omits_limitations_subsection_when_empty() -> None:
    result = assemble_research_result(
        "AAPL", [_financial_health_result(limitations=[])]
    )

    output = render_markdown(result)

    assert "**Limitaciones:**" not in output


def test_render_keeps_empty_financial_health_section_when_agent_absent() -> None:
    """Si el agente de salud financiera no está en `analysis_results`
    (ej. falló), la sección conserva solo su encabezado vacío."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Salud financiera")
    section_end = output.index("## Valoración")
    section_body = output[section_start:section_end].replace("## Salud financiera", "").strip()
    assert section_body == ""


def test_render_financial_health_section_ignores_other_analysis_results() -> None:
    """Un `AnalysisResult` de valoración no debe volcarse en la sección de
    salud financiera (esa sección solo lee `analysis_id == 'financial_health'`)."""
    result = assemble_research_result("AAPL", [_valuation_result(findings=["hallazgo de valoración"])])

    output = render_markdown(result)

    section_start = output.index("## Salud financiera")
    section_end = output.index("## Valoración")
    assert "hallazgo de valoración" not in output[section_start:section_end]


# --- Volcado de hallazgos de valoración --------------------------------------


def test_render_includes_valuation_findings_when_present() -> None:
    result = assemble_research_result(
        "AAPL", [_valuation_result(findings=["Texto de interpretación del modelo de valoración."])]
    )

    output = render_markdown(result)

    assert "Texto de interpretación del modelo de valoración." in output


def test_render_places_valuation_findings_under_its_own_section() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _financial_health_result(findings=["hallazgo de salud financiera"]),
            _valuation_result(findings=["hallazgo de valoración"]),
        ],
    )

    output = render_markdown(result)

    section_start = output.index("## Valoración")
    assert "hallazgo de valoración" in output[section_start:]
    assert "hallazgo de valoración" not in output[: output.index("## Valoración")]


def test_render_includes_valuation_supporting_metrics() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _valuation_result(
                supporting_metrics={"price_to_earnings": 20.0, "price_to_sales": 3.0}
            )
        ],
    )

    output = render_markdown(result)

    assert "price_to_earnings" in output
    assert "20.0" in output
    assert "price_to_sales" in output
    assert "3.0" in output


def test_render_includes_valuation_limitations_when_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _valuation_result(
                limitations=["No se dispone de datos para P/B.", "No se dispone de datos para EV/EBITDA."]
            )
        ],
    )

    output = render_markdown(result)

    assert "No se dispone de datos para P/B." in output
    assert "No se dispone de datos para EV/EBITDA." in output


def test_render_omits_valuation_limitations_subsection_when_empty() -> None:
    result = assemble_research_result("AAPL", [_valuation_result(limitations=[])])

    output = render_markdown(result)

    assert "**Limitaciones:**" not in output


def test_render_keeps_empty_valuation_section_when_agent_absent() -> None:
    """Si el agente de valoración no está en `analysis_results` (ej.
    falló), la sección conserva solo su encabezado vacío.

    Acotada por el encabezado de "Evolución de ingresos y beneficios"
    (nueva desde Fase 3): "Valoración" ya no es la última sección del
    reporte, por lo que la prueba ya no puede tomar todo lo que sigue a
    "## Valoración" hasta el final del documento.
    """
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    section_start = output.index("## Valoración")
    section_end = output.index("## Evolución de ingresos y beneficios")
    section_body = (
        output[section_start:section_end].replace("## Valoración", "").strip()
    )
    assert section_body == ""


def test_render_valuation_section_ignores_other_analysis_results() -> None:
    """Un `AnalysisResult` de salud financiera no debe volcarse en la
    sección de valoración (esa sección solo lee `analysis_id == 'valuation'`)."""
    result = assemble_research_result(
        "AAPL", [_financial_health_result(findings=["hallazgo de salud financiera"])]
    )

    output = render_markdown(result)

    section_start = output.index("## Valoración")
    section_end = output.index("## Evolución de ingresos y beneficios")
    assert "hallazgo de salud financiera" not in output[section_start:section_end]


def test_render_includes_both_sections_when_both_agents_present() -> None:
    result = assemble_research_result(
        "AAPL",
        [
            _financial_health_result(findings=["hallazgo de salud financiera"]),
            _valuation_result(findings=["hallazgo de valoración"]),
        ],
    )

    output = render_markdown(result)

    fh_start = output.index("## Salud financiera")
    val_start = output.index("## Valoración")
    assert "hallazgo de salud financiera" in output[fh_start:val_start]
    assert "hallazgo de valoración" in output[val_start:]


# --- Fuentes/procedencia de IA (proveedor, modelo, fecha) --------------------


def test_render_includes_financial_health_provenance() -> None:
    provenance = AnalysisProvenance(
        ai_provider="anthropic",
        ai_model="claude-sonnet-5",
        generated_at=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL", [_financial_health_result(provenance=provenance)]
    )

    output = render_markdown(result)

    assert "anthropic" in output
    assert "claude-sonnet-5" in output
    assert provenance.generated_at.isoformat() in output


def test_render_includes_valuation_provenance() -> None:
    provenance = AnalysisProvenance(
        ai_provider="anthropic",
        ai_model="claude-haiku-4-5",
        generated_at=datetime(2026, 7, 16, 11, 0, tzinfo=timezone.utc),
    )
    result = assemble_research_result(
        "AAPL", [_valuation_result(provenance=provenance)]
    )

    output = render_markdown(result)

    assert "claude-haiku-4-5" in output
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

    output = render_markdown(result)

    fh_start = output.index("## Salud financiera")
    val_start = output.index("## Valoración")
    assert "claude-sonnet-5" in output[fh_start:val_start]
    assert "claude-haiku-4-5" not in output[fh_start:val_start]
    assert "claude-haiku-4-5" in output[val_start:]


def test_render_provenance_includes_generated_by_label() -> None:
    result = assemble_research_result("AAPL", [_financial_health_result()])

    output = render_markdown(result)

    assert "**Generado por:**" in output


def test_render_omits_provenance_when_agent_absent() -> None:
    """Si el agente no completó su análisis, no hay procedencia que mostrar."""
    result = assemble_research_result("AAPL", [])

    output = render_markdown(result)

    assert "**Generado por:**" not in output
