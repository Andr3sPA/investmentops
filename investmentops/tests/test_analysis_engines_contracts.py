"""Pruebas para el contrato de "analysis engine" (investmentops.analysis_engines).

Cubre la tarea "Definir el contrato de 'analysis engine' / agente de IA
(entrada: modelo de dominio normalizado + métricas precalculadas cuando
aplique; salida: resultado estructurado)" (TASKS.md, Fase 1, "Contratos e
interfaces"). No prueba ningún agente concreto: eso corresponde a tareas
posteriores (ver TASKS.md, "Agente de análisis: salud financiera" y
"Agente de análisis: valoración").
"""

from datetime import datetime, timezone

import pytest

from investmentops.analysis_engines import (
    AnalysisEngine,
    AnalysisEngineError,
    AnalysisProvenance,
    AnalysisResult,
)


class _DummyEngine:
    """Agente mínimo de prueba que cumple el contrato `AnalysisEngine`."""

    def analyze(self, company_data, metrics=None) -> AnalysisResult:
        return AnalysisResult(
            analysis_id="dummy_analysis",
            findings=["La empresa muestra una liquidez estable."],
            supporting_metrics=metrics or {"current_ratio": 1.5},
            limitations=["Cálculo basado en datos parciales."],
            provenance=AnalysisProvenance(
                ai_provider="dummy_provider",
                ai_model="dummy-model",
                generated_at=datetime.now(timezone.utc),
            ),
        )


class _FailingEngine:
    """Agente mínimo de prueba que señala un fallo mediante el contrato."""

    def analyze(self, company_data, metrics=None) -> AnalysisResult:
        raise AnalysisEngineError("El proveedor de IA no respondió")


def test_dummy_engine_satisfies_analysis_engine_protocol() -> None:
    engine = _DummyEngine()

    assert isinstance(engine, AnalysisEngine)


def test_analyze_returns_analysis_result_with_provenance() -> None:
    engine = _DummyEngine()

    result = engine.analyze(company_data={"ticker": "AAPL"}, metrics={"current_ratio": 2.0})

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "dummy_analysis"
    assert result.findings == ["La empresa muestra una liquidez estable."]
    assert result.supporting_metrics == {"current_ratio": 2.0}
    assert result.limitations == ["Cálculo basado en datos parciales."]
    assert isinstance(result.provenance, AnalysisProvenance)
    assert result.provenance.ai_provider == "dummy_provider"
    assert result.provenance.ai_model == "dummy-model"
    assert isinstance(result.provenance.generated_at, datetime)


def test_analyze_accepts_metrics_as_optional() -> None:
    engine = _DummyEngine()

    result = engine.analyze(company_data={"ticker": "AAPL"})

    assert result.supporting_metrics == {"current_ratio": 1.5}


def test_failing_engine_raises_analysis_engine_error() -> None:
    engine = _FailingEngine()

    with pytest.raises(AnalysisEngineError, match="no respondió"):
        engine.analyze(company_data={"ticker": "AAPL"})


def test_analysis_engine_error_is_a_runtime_error() -> None:
    assert issubclass(AnalysisEngineError, RuntimeError)


def test_analysis_result_is_immutable() -> None:
    provenance = AnalysisProvenance(
        ai_provider="dummy_provider",
        ai_model="dummy-model",
        generated_at=datetime.now(timezone.utc),
    )
    result = AnalysisResult(
        analysis_id="dummy_analysis",
        findings=["hallazgo"],
        supporting_metrics={},
        limitations=[],
        provenance=provenance,
    )

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


def test_analysis_provenance_is_immutable() -> None:
    provenance = AnalysisProvenance(
        ai_provider="dummy_provider",
        ai_model="dummy-model",
        generated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(AttributeError):
        provenance.ai_provider = "otro_proveedor"  # type: ignore[misc]
