"""Pruebas para la impresión en consola del resultado
(investmentops.cli.format_research_result).

Cubre la tarea "Implementar la impresión en consola del resultado (texto
simple, sin formato de reporte todavía)" (TASKS.md, Fase 1, "CLI"). No
prueba el parseo de argumentos (`test_cli.py`,
`test_cli_ticker_validation.py`) ni la conexión con el orquestador
(`test_cli_dispatch.py`); solo el formateo de un `ResearchResult` ya
construido a texto de consola.
"""

from datetime import datetime, timezone

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.cli import format_research_result
from investmentops.core.orchestrator import assemble_research_result
from investmentops.core.research_result import ResearchFailure


def _analysis_result(
    analysis_id: str = "financial_health",
    findings: list[str] | None = None,
    supporting_metrics: dict | None = None,
    limitations: list[str] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        findings=findings if findings is not None else ["La empresa muestra un margen saludable."],
        supporting_metrics=supporting_metrics if supporting_metrics is not None else {"net_margin": 0.15},
        limitations=limitations if limitations is not None else [],
        provenance=AnalysisProvenance(
            ai_provider="anthropic",
            ai_model="claude-sonnet-5",
            generated_at=datetime.now(timezone.utc),
        ),
    )


def test_format_includes_company_ticker() -> None:
    result = assemble_research_result("AAPL", [_analysis_result()])

    output = format_research_result(result)

    assert "AAPL" in output


def test_format_includes_generated_at_timestamp() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = assemble_research_result("AAPL", [], generated_at=fixed_time)

    output = format_research_result(result)

    assert fixed_time.isoformat() in output


def test_format_includes_analysis_id_and_findings() -> None:
    analysis = _analysis_result(
        analysis_id="valuation", findings=["La empresa parece razonablemente valorada."]
    )
    result = assemble_research_result("AAPL", [analysis])

    output = format_research_result(result)

    assert "valuation" in output
    assert "La empresa parece razonablemente valorada." in output


def test_format_includes_supporting_metrics() -> None:
    analysis = _analysis_result(
        supporting_metrics={"net_margin": 0.15, "debt_to_revenue": 0.4}
    )
    result = assemble_research_result("AAPL", [analysis])

    output = format_research_result(result)

    assert "net_margin" in output
    assert "0.15" in output
    assert "debt_to_revenue" in output
    assert "0.4" in output


def test_format_includes_limitations_when_present() -> None:
    analysis = _analysis_result(limitations=["Sin datos de liquidez."])
    result = assemble_research_result("AAPL", [analysis])

    output = format_research_result(result)

    assert "Sin datos de liquidez." in output


def test_format_omits_limitations_section_when_empty() -> None:
    analysis = _analysis_result(limitations=[])
    result = assemble_research_result("AAPL", [analysis])

    output = format_research_result(result)

    assert "Limitaciones:" not in output


def test_format_includes_ai_provenance() -> None:
    result = assemble_research_result("AAPL", [_analysis_result()])

    output = format_research_result(result)

    assert "anthropic" in output
    assert "claude-sonnet-5" in output


def test_format_shows_multiple_analysis_results_in_order() -> None:
    financial_health = _analysis_result(analysis_id="financial_health")
    valuation = _analysis_result(analysis_id="valuation")
    result = assemble_research_result("AAPL", [financial_health, valuation])

    output = format_research_result(result)

    assert output.index("financial_health") < output.index("valuation")


def test_format_indicates_explicitly_when_no_analysis_results() -> None:
    result = assemble_research_result("AAPL", [])

    output = format_research_result(result)

    assert "No se completó ningún análisis." in output


def test_format_includes_failures_section_when_present() -> None:
    failure = ResearchFailure(
        stage="analysis_engine",
        identifier="valuation",
        reason="El proveedor de IA no respondió",
    )
    result = assemble_research_result(
        "AAPL", [_analysis_result(analysis_id="financial_health")], failures=[failure]
    )

    output = format_research_result(result)

    assert "Fallos parciales" in output
    assert "analysis_engine" in output
    assert "valuation" in output
    assert "El proveedor de IA no respondió" in output


def test_format_omits_failures_section_when_empty() -> None:
    result = assemble_research_result("AAPL", [_analysis_result()])

    output = format_research_result(result)

    assert "Fallos parciales" not in output


def test_format_returns_non_empty_string_even_with_no_results_and_no_failures() -> None:
    result = assemble_research_result("AAPL", [])

    output = format_research_result(result)

    assert output.strip() != ""


def test_format_shows_data_provider_failure_when_analysis_could_not_run() -> None:
    """Caso típico de `investigate` cuando `fetch_and_normalize` falla:
    `analysis_results` vacío, un único fallo con stage='data_provider'."""
    failure = ResearchFailure(
        stage="data_provider",
        identifier="NOPE",
        reason="Ticker 'NOPE' no encontrado",
    )
    result = assemble_research_result("NOPE", [], failures=[failure])

    output = format_research_result(result)

    assert "No se completó ningún análisis." in output
    assert "data_provider" in output
    assert "Ticker 'NOPE' no encontrado" in output
