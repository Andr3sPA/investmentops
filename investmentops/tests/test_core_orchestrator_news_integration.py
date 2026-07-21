"""Pruebas para la inclusión del resultado del motor de noticias
relevantes en el "Resultado de investigación" ensamblado por
`investmentops.core.orchestrator.investigate`.

Cubre la tarea "Incluir el nuevo resultado en el 'Resultado de
investigación'" (TASKS.md, Fase 4, "Orquestador"), sobre la pieza ya
implementada en la tarea anterior de esta misma sección
(`run_news_relevance_engine`/`_news_relevance_result_to_analysis_result`,
ver `test_core_orchestrator_news_relevance.py`). No prueba de nuevo esas
piezas en detalle, ni el manejo de fallos parciales de salud
financiera/valoración/tendencia (ya cubiertos en
`test_core_orchestrator.py`): solo el nuevo comportamiento de
`investigate` respecto al motor de noticias relevantes.

`investigate` solo intenta el motor de noticias relevantes si se le
inyecta explícitamente un `news_provider`, o si no se inyectó ningún
`provider` de datos fundamentales (uso real, sin proveedores de prueba),
mismo criterio en espíritu ya usado para el motor de tendencia (ver
`investmentops/core/orchestrator.py`, "Inclusión del motor de tendencia
en investigate"), pero mediante un parámetro separado (`news_provider`),
ya que el proveedor de noticias (`FMPNewsProvider`) es un tipo distinto
del proveedor de datos fundamentales (`FMPFundamentalsProvider`/
`DataProvider`) y no tiene sentido detectarlo mediante `hasattr` sobre
el mismo objeto.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from investmentops.analysis_engines.news_relevance import (
    AGENT_ID as NEWS_RELEVANCE_AGENT_ID,
)
from investmentops.core.orchestrator import investigate
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba de datos fundamentales (payload completo)."""

    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload if payload is not None else _complete_payload()

    def fetch(self, ticker: str) -> RawProviderData:
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _DummyNewsProvider:
    """Proveedor mínimo de prueba de noticias, misma forma que `FMPNewsProvider`."""

    def __init__(self, payload: list[dict] | None = None) -> None:
        self._payload = payload if payload is not None else [_news_item()]
        self.received_ticker: str | None = None

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_ticker = ticker
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_news_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingNewsProvider:
    """Proveedor mínimo de prueba que señala un fallo mediante el contrato."""

    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"No se pudo obtener noticias para '{ticker}'")


def _complete_payload() -> dict:
    return {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
        "quote": [
            {"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}
        ],
    }


def _news_item(published_date: str = "2026-07-18 09:00:00") -> dict:
    return {
        "symbol": "AAPL",
        "title": "Apple anuncia nuevo producto",
        "text": "Resumen de la noticia...",
        "site": "example_news_site",
        "publishedDate": published_date,
        "url": "https://example.test/news/1",
        "source": "dummy_news_provider",
        "queried_at": "2026-07-21T00:00:00+00:00",
    }


def _analysis_config(**overrides: object) -> dict:
    config: dict = {
        "agents": {"financial_health": "anthropic", "valuation": "anthropic"},
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


def _mock_anthropic_response(text: str) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "model": "claude-sonnet-5",
        "content": [{"type": "text", "text": text}],
    }
    return response


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_includes_news_relevance_when_news_provider_given(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()
    news_provider = _DummyNewsProvider()

    result = investigate(
        "AAPL",
        config=_analysis_config(),
        provider=provider,
        news_provider=news_provider,
    )

    analysis_ids = [analysis.analysis_id for analysis in result.analysis_results]
    assert NEWS_RELEVANCE_AGENT_ID in analysis_ids
    assert news_provider.received_ticker == "AAPL"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_news_relevance_result_has_sentinel_provenance(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()
    news_provider = _DummyNewsProvider()

    result = investigate(
        "AAPL",
        config=_analysis_config(),
        provider=provider,
        news_provider=news_provider,
    )

    news_result = next(
        analysis
        for analysis in result.analysis_results
        if analysis.analysis_id == NEWS_RELEVANCE_AGENT_ID
    )
    assert news_result.provenance.ai_provider == "none"
    assert news_result.provenance.ai_model == "deterministic"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_captures_news_provider_failure_without_raising(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()

    result = investigate(
        "AAPL",
        config=_analysis_config(),
        provider=provider,
        news_provider=_FailingNewsProvider(),
    )

    analysis_ids = [analysis.analysis_id for analysis in result.analysis_results]
    assert NEWS_RELEVANCE_AGENT_ID not in analysis_ids
    assert any(
        failure.stage == "data_provider" and failure.identifier == NEWS_RELEVANCE_AGENT_ID
        for failure in result.failures
    )
    assert "financial_health" in analysis_ids
    assert "valuation" in analysis_ids


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_skips_news_relevance_when_no_news_provider_given(
    mock_post: Mock,
) -> None:
    """Regresión: sin `news_provider` explícito y con un `provider` de
    prueba inyectado (caso ya cubierto por las pruebas existentes de
    `investigate` en `test_core_orchestrator.py`), el motor de noticias
    relevantes no debe intentarse — evita disparar una consulta real a
    FMPNewsProvider (y una falla espuria por falta de API key de
    noticias) en pruebas que no la anticipan."""
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()

    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    analysis_ids = [analysis.analysis_id for analysis in result.analysis_results]
    assert NEWS_RELEVANCE_AGENT_ID not in analysis_ids
    assert result.failures == []