# investmentops/tests/test_core_orchestrator_news_relevance.py
"""Pruebas para el registro de la invocación del motor de noticias
relevantes en el orquestador
(investmentops.core.orchestrator.run_news_relevance_engine /
_news_relevance_result_to_analysis_result).

Cubre la tarea "Registrar el nuevo motor de análisis sin modificar los
motores existentes" (TASKS.md, Fase 4, "Orquestador"), sobre el mismo
patrón ya usado por `run_trend_analysis_engine`/
`_trend_analysis_result_to_analysis_result` (Fase 3, ver
`test_core_orchestrator_trend_analysis.py`). No prueba de nuevo
`fetch_and_normalize_news` (ya cubierta en
`test_core_orchestrator_news.py`) ni `assemble_news_relevance_analysis`
(ya cubierta en `test_analysis_engines_news_assembly.py`) más allá de lo
necesario para confirmar que `run_news_relevance_engine` los encadena
correctamente. Tampoco prueba la incorporación de este resultado a
`ResearchResult`/`investigate`: esa es la tarea siguiente y separada de
la misma sección.
"""

from datetime import datetime, timezone

import pytest

from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.news_relevance import (
    AGENT_ID as NEWS_RELEVANCE_AGENT_ID,
    NewsRelevanceResult,
    assemble_news_relevance_analysis,
)
from investmentops.core.orchestrator import (
    NEWS_RELEVANCE_AI_MODEL,
    NEWS_RELEVANCE_AI_PROVIDER,
    _news_relevance_result_to_analysis_result,
    fetch_and_normalize_news,
    run_news_relevance_engine,
)
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyNewsProvider:
    """Proveedor mínimo de prueba con `fetch`, misma forma que `FMPNewsProvider`."""

    def __init__(self, payload: list[dict] | None = None) -> None:
        self._payload = payload if payload is not None else [_news_item()]
        self.received_ticker: str | None = None

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_ticker = ticker
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingNewsProvider:
    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"No se pudo obtener noticias para '{ticker}'")


def _news_item(
    title: str = "Apple anuncia nuevo producto",
    text: str = "Resumen de la noticia...",
    site: str = "example_news_site",
    published_date: str = "2026-07-18 09:00:00",
    url: str = "https://example.test/news/1",
) -> dict:
    return {
        "symbol": "AAPL",
        "title": title,
        "text": text,
        "site": site,
        "publishedDate": published_date,
        "url": url,
        "source": "dummy_provider",
        "queried_at": "2026-07-21T00:00:00+00:00",
    }


# --- _news_relevance_result_to_analysis_result --------------------------------


def _sample_news_result() -> NewsRelevanceResult:
    return NewsRelevanceResult(
        analysis_id=NEWS_RELEVANCE_AGENT_ID,
        findings=["Se encontraron 1 noticia reciente relevante en los últimos 7 día(s)."],
        supporting_metrics={"relevant_news": [{"title": "Noticia"}]},
        limitations=[],
    )


def test_conversion_returns_analysis_result_with_news_relevance_agent_id() -> None:
    news_result = _sample_news_result()

    result = _news_relevance_result_to_analysis_result(news_result)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == NEWS_RELEVANCE_AGENT_ID
    assert result.analysis_id == "news_relevance"


def test_conversion_preserves_findings_metrics_and_limitations() -> None:
    news_result = NewsRelevanceResult(
        analysis_id=NEWS_RELEVANCE_AGENT_ID,
        findings=["hallazgo de noticias"],
        supporting_metrics={"relevant_news": []},
        limitations=["advertencia de prueba"],
    )

    result = _news_relevance_result_to_analysis_result(news_result)

    assert result.findings == ["hallazgo de noticias"]
    assert result.supporting_metrics == {"relevant_news": []}
    assert result.limitations == ["advertencia de prueba"]


def test_conversion_uses_sentinel_provenance() -> None:
    news_result = _sample_news_result()

    result = _news_relevance_result_to_analysis_result(news_result)

    assert isinstance(result.provenance, AnalysisProvenance)
    assert result.provenance.ai_provider == "none"
    assert result.provenance.ai_model == "deterministic"
    assert result.provenance.ai_provider == NEWS_RELEVANCE_AI_PROVIDER
    assert result.provenance.ai_model == NEWS_RELEVANCE_AI_MODEL


def test_conversion_defaults_generated_at_to_now() -> None:
    before = datetime.now(timezone.utc)

    result = _news_relevance_result_to_analysis_result(_sample_news_result())

    after = datetime.now(timezone.utc)
    assert before <= result.provenance.generated_at <= after


def test_conversion_accepts_explicit_generated_at() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = _news_relevance_result_to_analysis_result(
        _sample_news_result(), generated_at=fixed_time
    )

    assert result.provenance.generated_at == fixed_time


def test_conversion_result_is_immutable() -> None:
    result = _news_relevance_result_to_analysis_result(_sample_news_result())

    with pytest.raises(AttributeError):
        result.analysis_id = "otro_id"  # type: ignore[misc]


# --- run_news_relevance_engine -------------------------------------------------


def test_run_news_relevance_engine_returns_analysis_result() -> None:
    provider = _DummyNewsProvider()

    result = run_news_relevance_engine(
        "AAPL", provider=provider, now=datetime(2026, 7, 21, 12, 0, 0)
    )

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "news_relevance"


def test_run_news_relevance_engine_passes_ticker_to_provider() -> None:
    provider = _DummyNewsProvider()

    run_news_relevance_engine(
        "AAPL", provider=provider, now=datetime(2026, 7, 21, 12, 0, 0)
    )

    assert provider.received_ticker == "AAPL"


def test_run_news_relevance_engine_reflects_relevant_news_in_findings() -> None:
    provider = _DummyNewsProvider()

    result = run_news_relevance_engine(
        "AAPL", provider=provider, now=datetime(2026, 7, 21, 12, 0, 0)
    )

    assert "1" in result.findings[0]
    assert len(result.supporting_metrics["relevant_news"]) == 1
    assert result.limitations == []


def test_run_news_relevance_engine_uses_default_window_and_summary_length() -> None:
    provider = _DummyNewsProvider()

    run_news_relevance_engine("AAPL", provider=provider, now=datetime(2026, 7, 21, 12, 0, 0))
    # No debe lanzar; usa DEFAULT_RELEVANCE_WINDOW_DAYS/DEFAULT_SUMMARY_MAX_LENGTH
    # internamente (ver assemble_news_relevance_analysis).


def test_run_news_relevance_engine_passes_custom_days_and_summary_max_length() -> None:
    provider = _DummyNewsProvider()

    result = run_news_relevance_engine(
        "AAPL",
        provider=provider,
        now=datetime(2026, 7, 21, 12, 0, 0),
        days=30,
        summary_max_length=5,
    )

    assert "30" in result.findings[0]
    assert result.supporting_metrics["relevant_news"][0]["summary"].endswith("...")


def test_run_news_relevance_engine_indicates_absence_when_no_relevant_news() -> None:
    old_item = _news_item(published_date="2026-01-01 09:00:00")
    provider = _DummyNewsProvider(payload=[old_item])

    result = run_news_relevance_engine(
        "AAPL", provider=provider, now=datetime(2026, 7, 21, 12, 0, 0)
    )

    assert "No se encontraron" in result.findings[0]
    assert result.supporting_metrics["relevant_news"] == []
    assert len(result.limitations) == 1


def test_run_news_relevance_engine_uses_sentinel_provenance() -> None:
    provider = _DummyNewsProvider()

    result = run_news_relevance_engine(
        "AAPL", provider=provider, now=datetime(2026, 7, 21, 12, 0, 0)
    )

    assert result.provenance.ai_provider == "none"
    assert result.provenance.ai_model == "deterministic"


def test_run_news_relevance_engine_propagates_data_provider_error() -> None:
    with pytest.raises(DataProviderError, match="No se pudo obtener noticias"):
        run_news_relevance_engine("NOPE", provider=_FailingNewsProvider())


def test_run_news_relevance_engine_matches_direct_assemble_call() -> None:
    """Confirma que encadenar fetch_and_normalize_news ->
    assemble_news_relevance_analysis produce el mismo contenido que
    llamar assemble_news_relevance_analysis directamente sobre las
    noticias ya normalizadas."""
    provider = _DummyNewsProvider()
    now = datetime(2026, 7, 21, 12, 0, 0)
    news_items = fetch_and_normalize_news("AAPL", provider=provider)
    expected = assemble_news_relevance_analysis(news_items, now=now)

    result = run_news_relevance_engine("AAPL", provider=_DummyNewsProvider(), now=now)

    assert result.findings == list(expected.findings)
    assert result.supporting_metrics == expected.supporting_metrics
    assert result.limitations == list(expected.limitations)