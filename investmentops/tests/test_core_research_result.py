"""Pruebas para la estructura "Resultado de investigación" (investmentops.core).

Cubre la tarea "Definir la estructura de 'Resultado de investigación'
(agregación de resultados de análisis para una empresa)" (TASKS.md, Fase
1, "Contratos e interfaces"). No prueba la lógica que ensambla un
`ResearchResult` real invocando fuentes de datos y motores de análisis:
eso corresponde a una tarea posterior (ver TASKS.md, "Orquestador
mínimo").
"""

from datetime import datetime, timezone

import pytest

from investmentops.analysis_engines import AnalysisProvenance, AnalysisResult
from investmentops.core import ResearchFailure, ResearchResult
from investmentops.data_layer import Company


def _sample_company() -> Company:
    return Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Tecnología",
        market="NASDAQ",
    )


def _sample_analysis_result(analysis_id: str = "financial_health") -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        findings=["La empresa muestra una liquidez estable."],
        supporting_metrics={"current_ratio": 1.5},
        limitations=[],
        provenance=AnalysisProvenance(
            ai_provider="dummy_provider",
            ai_model="dummy-model",
            generated_at=datetime.now(timezone.utc),
        ),
    )


def test_research_result_aggregates_company_and_analysis_results() -> None:
    company = _sample_company()
    analysis_results = [
        _sample_analysis_result("financial_health"),
        _sample_analysis_result("valuation"),
    ]
    generated_at = datetime.now(timezone.utc)

    result = ResearchResult(
        company=company,
        analysis_results=analysis_results,
        failures=[],
        generated_at=generated_at,
    )

    assert result.company == company
    assert result.analysis_results == analysis_results
    assert result.failures == []
    assert result.generated_at == generated_at


def test_research_result_can_hold_partial_failures_alongside_successful_results() -> None:
    """Un fallo parcial no debe excluir los análisis que sí se completaron."""
    company = _sample_company()
    successful = [_sample_analysis_result("financial_health")]
    failure = ResearchFailure(
        stage="analysis_engine",
        identifier="valuation",
        reason="El proveedor de IA no respondió",
    )

    result = ResearchResult(
        company=company,
        analysis_results=successful,
        failures=[failure],
        generated_at=datetime.now(timezone.utc),
    )

    assert result.analysis_results == successful
    assert result.failures == [failure]
    assert result.failures[0].stage == "analysis_engine"
    assert result.failures[0].identifier == "valuation"


def test_research_result_supports_empty_analysis_results_with_failures_only() -> None:
    """Si todos los análisis fallan, el resultado sigue siendo válido y explícito."""
    company = _sample_company()
    failures = [
        ResearchFailure(
            stage="data_provider",
            identifier="fundamentals",
            reason="Ticker no encontrado",
        )
    ]

    result = ResearchResult(
        company=company,
        analysis_results=[],
        failures=failures,
        generated_at=datetime.now(timezone.utc),
    )

    assert result.analysis_results == []
    assert result.failures == failures


def test_research_result_is_immutable() -> None:
    result = ResearchResult(
        company=_sample_company(),
        analysis_results=[],
        failures=[],
        generated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(AttributeError):
        result.company = _sample_company()  # type: ignore[misc]


def test_research_failure_is_immutable() -> None:
    failure = ResearchFailure(
        stage="data_provider",
        identifier="fundamentals",
        reason="Ticker no encontrado",
    )

    with pytest.raises(AttributeError):
        failure.reason = "otro motivo"  # type: ignore[misc]
