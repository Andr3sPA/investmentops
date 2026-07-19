"""Pruebas para el registro de la invocación del motor de evolución de
ingresos y beneficios en el orquestador
(investmentops.core.orchestrator.run_trend_analysis_engine /
_trend_analysis_result_to_analysis_result).

Cubre la tarea "Registrar la invocación de `assemble_trend_analysis` en
el flujo de análisis del orquestador, conforme a la decisión de
integración ya tomada, sin modificar los motores existentes (salud
financiera, valoración)" (TASKS.md, Fase 3, "Orquestador"), sobre la
decisión ya documentada en `investmentops/core/TREND_INTEGRATION.md`. No
prueba de nuevo `fetch_and_normalize_historical` (ya cubierta en
`test_core_orchestrator.py`) ni `assemble_trend_analysis` (ya cubierta
en `test_analysis_engines_trend_assembly.py`) más allá de lo necesario
para confirmar que `run_trend_analysis_engine` los encadena
correctamente. Tampoco prueba la incorporación de este resultado a
`ResearchResult`/`investigate`: esa es la tarea siguiente y separada de
la misma sección.
"""

from datetime import date, datetime, timezone

import pytest

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.trends import (
    AGENT_ID as TREND_AGENT_ID,
    TrendAnalysisResult,
    assemble_trend_analysis,
)
from investmentops.core.orchestrator import (
    TREND_ANALYSIS_AI_MODEL,
    TREND_ANALYSIS_AI_PROVIDER,
    _trend_analysis_result_to_analysis_result,
    run_trend_analysis_engine,
)
from investmentops.data_layer.contracts import ProviderMetadata  # type: ignore  # noqa: F401
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyHistoricalProvider:
    """Proveedor mínimo de prueba con `fetch_historical`."""

    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload if payload is not None else _complete_historical_payload()
        self.received_ticker: str | None = None
        self.received_period: str | None = None
        self.received_limit: int | None = None

    def fetch_historical(self, ticker: str, *, period: str = "annual", limit: int = 5):
        self.received_ticker = ticker
        self.received_period = period
        self.received_limit = limit
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingHistoricalProvider:
    def fetch_historical(self, ticker: str, *, period: str = "annual", limit: int = 5):
        raise DataProviderError(f"Ticker '{ticker}' no encontrado")


def _income_point(period_end: str, revenue: float, net_income: float) -> dict:
    return {
        "date": period_end,
        "revenue": revenue,
        "netIncome": net_income,
        "source": "dummy_provider",
        "queried_at": "2026-07-19T00:00:00+00:00",
    }


def _balance_point(period_end: str, debt: float) -> dict:
    return {
        "date": period_end,
        "totalDebt": debt,
        "source": "dummy_provider",
        "queried_at": "2026-07-19T00:00:00+00:00",
    }


def _complete_historical_payload() -> dict:
    return {
        "income_statement": [
            _income_point("2025-12-31", 1_300_000.0, 260_000.0),
            _income_point("2024-12-31", 1_200_000.0, 240_000.0),
            _income_point("2023-12-31", 1_100_000.0, 220_000.0),
        ],
        "balance_sheet_statement": [
            _balance_point("2025-12-31", 400_000.0),
            _balance_point("2024-12-31", 350_000.0),
            _balance_point("2023-12-31", 300_000.0),
        ],
    }


# --- _trend_analysis_result_to_analysis_result -------------------------------


def _sample_trend_result() -> TrendAnalysisResult:
    return TrendAnalysisResult(
        analysis_id=TREND_AGENT_ID,
        findings=["Los ingresos muestran una tendencia creciente en los periodos analizados."],
        supporting_metrics={"revenue_trend": "creciente", "net_income_trend": "creciente"},
        limitations=[],
    )


def test_conversion_returns_analysis_result_with_trend_agent_id() -> None:
    trend_result = _sample_trend_result()

    result = _trend_analysis_result_to_analysis_result(trend_result)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == TREND_AGENT_ID
    assert result.analysis_id == "trend_analysis"


def test_conversion_preserves_findings_metrics_and_limitations() -> None:
    trend_result = TrendAnalysisResult(
        analysis_id=TREND_AGENT_ID,
        findings=["hallazgo de ingresos", "hallazgo de beneficios"],
        supporting_metrics={"revenue_trend": "mixta"},
        limitations=["advertencia de prueba"],
    )

    result = _trend_analysis_result_to_analysis_result(trend_result)

    assert result.findings == ["hallazgo de ingresos", "hallazgo de beneficios"]
    assert result.supporting_metrics == {"revenue_trend": "mixta"}
    assert result.limitations == ["advertencia de prueba"]


def test_conversion_uses_sentinel_provenance() -> None:
    trend_result = _sample_trend_result()

    result = _trend_analysis_result_to_analysis_result(trend_result)

    assert isinstance(result.provenance, AnalysisProvenance)
    assert result.provenance.ai_provider == "none"
    assert result.provenance.ai_model == "deterministic"
    assert result.provenance.ai_provider == TREND_ANALYSIS_AI_PROVIDER
    assert result.provenance.ai_model == TREND_ANALYSIS_AI_MODEL


def test_conversion_defaults_generated_at_to_now() -> None:
    before = datetime.now(timezone.utc)

    result = _trend_analysis_result_to_analysis_result(_sample_trend_result())

    after = datetime.now(timezone.utc)
    assert before <= result.provenance.generated_at <= after


def test_conversion_accepts_explicit_generated_at() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = _trend_analysis_result_to_analysis_result(
        _sample_trend_result(), generated_at=fixed_time
    )

    assert result.provenance.generated_at == fixed_time


def test_conversion_result_is_immutable() -> None:
    result = _trend_analysis_result_to_analysis_result(_sample_trend_result())

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


# --- run_trend_analysis_engine ------------------------------------------------


def test_run_trend_analysis_engine_returns_analysis_result() -> None:
    provider = _DummyHistoricalProvider()

    result = run_trend_analysis_engine("AAPL", provider=provider)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "trend_analysis"


def test_run_trend_analysis_engine_passes_ticker_period_and_limit_to_provider() -> None:
    provider = _DummyHistoricalProvider()

    run_trend_analysis_engine("AAPL", provider=provider, period="quarter", limit=8)

    assert provider.received_ticker == "AAPL"
    assert provider.received_period == "quarter"
    assert provider.received_limit == 8


def test_run_trend_analysis_engine_uses_default_period_and_limit() -> None:
    provider = _DummyHistoricalProvider()

    run_trend_analysis_engine("AAPL", provider=provider)

    assert provider.received_period == "annual"
    assert provider.received_limit == 5


def test_run_trend_analysis_engine_reflects_growing_trend_in_findings() -> None:
    provider = _DummyHistoricalProvider()

    result = run_trend_analysis_engine("AAPL", provider=provider)

    assert any("creciente" in finding for finding in result.findings)
    assert result.supporting_metrics["revenue_trend"] == "creciente"
    assert result.supporting_metrics["net_income_trend"] == "creciente"


def test_run_trend_analysis_engine_uses_sentinel_provenance() -> None:
    provider = _DummyHistoricalProvider()

    result = run_trend_analysis_engine("AAPL", provider=provider)

    assert result.provenance.ai_provider == "none"
    assert result.provenance.ai_model == "deterministic"


def test_run_trend_analysis_engine_propagates_data_provider_error() -> None:
    with pytest.raises(DataProviderError, match="no encontrado"):
        run_trend_analysis_engine("NOPE", provider=_FailingHistoricalProvider())


def test_run_trend_analysis_engine_matches_direct_assemble_trend_analysis_call() -> None:
    """Confirma que encadenar fetch_and_normalize_historical ->
    assemble_trend_analysis produce el mismo contenido que llamar
    assemble_trend_analysis directamente sobre la serie ya normalizada."""
    from investmentops.core.orchestrator import fetch_and_normalize_historical

    provider = _DummyHistoricalProvider()
    series = fetch_and_normalize_historical("AAPL", provider=provider)
    expected = assemble_trend_analysis(series)

    result = run_trend_analysis_engine("AAPL", provider=_DummyHistoricalProvider())

    assert result.findings == list(expected.findings)
    assert result.supporting_metrics == expected.supporting_metrics
    assert result.limitations == list(expected.limitations)