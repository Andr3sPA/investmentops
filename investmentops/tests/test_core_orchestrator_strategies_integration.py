"""Pruebas para la inclusión de las lecturas por estrategia de inversión
(value, growth, calidad) en el "Resultado de investigación" ensamblado
por investmentops.core.orchestrator.investigate.

Cubre la tarea "Incluir los resultados de cada estrategia en el
'Resultado de investigación' como entradas independientes y
contrastables" (TASKS.md, Fase 6, "Orquestador"). No prueba de nuevo
run_value_engine/run_growth_engine/run_quality_engine en detalle (ya
cubiertos en test_core_orchestrator_strategies.py) ni el manejo de
fallos parciales de salud financiera/valoración/tendencia/noticias (ya
cubiertos en test_core_orchestrator.py/test_core_orchestrator_news_integration.py):
solo el nuevo comportamiento de investigate respecto a las tres
estrategias.

Las estrategias "value"/"quality" solo se intentan cuando no se inyecta
un `provider` de datos fundamentales de prueba (`provider is None`, uso
real): mismo criterio ya aplicado al motor de noticias relevantes. Por
eso estas pruebas mockean `requests.get` (FMP fundamentales y noticias)
y `requests.post` (Anthropic) en vez de inyectar un `DataProvider` de
prueba.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from investmentops.core.orchestrator import investigate
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


def _mock_response(json_data, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def _fmp_get_side_effect(url, params=None, timeout=None, **kwargs):
    if "income-statement" in url:
        return _mock_response(
            [{"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}]
        )
    if "balance-sheet-statement" in url:
        return _mock_response([{"date": "2025-12-31", "totalDebt": 400_000.0}])
    if "quote" in url:
        return _mock_response(
            [{"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}]
        )
    return _mock_response([])


def _mock_anthropic_response(text: str = "hallazgo") -> Mock:
    return _mock_response(
        {"model": "claude-sonnet-5", "content": [{"type": "text", "text": text}]}
    )


def _full_config(**overrides: object) -> dict:
    config: dict = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
        "agents": {
            "financial_health": "anthropic",
            "valuation": "anthropic",
            "value": "anthropic",
            "growth": "anthropic",
            "quality": "anthropic",
        },
        "ai_providers": {
            "anthropic": {"api_key": "fake-key"},
            "default": {"provider": "anthropic", "model": "claude-sonnet-5"},
        },
    }
    config.update(overrides)
    return config


@patch("investmentops.data_providers.news.requests.get")
@patch("investmentops.ai_providers.anthropic_provider.requests.post")
@patch("investmentops.data_providers.fundamentals.requests.get")
def test_investigate_includes_value_growth_and_quality_when_provider_not_injected(
    mock_fmp_get: Mock, mock_post: Mock, mock_news_get: Mock
) -> None:
    mock_fmp_get.side_effect = _fmp_get_side_effect
    mock_post.return_value = _mock_anthropic_response()
    mock_news_get.return_value = _mock_response([])

    result = investigate("AAPL", config=_full_config())

    analysis_ids = [analysis.analysis_id for analysis in result.analysis_results]
    assert "value" in analysis_ids
    assert "growth" in analysis_ids
    assert "quality" in analysis_ids


@patch("investmentops.data_providers.news.requests.get")
@patch("investmentops.ai_providers.anthropic_provider.requests.post")
@patch("investmentops.data_providers.fundamentals.requests.get")
def test_investigate_strategy_results_have_real_ai_provenance(
    mock_fmp_get: Mock, mock_post: Mock, mock_news_get: Mock
) -> None:
    mock_fmp_get.side_effect = _fmp_get_side_effect
    mock_post.return_value = _mock_anthropic_response()
    mock_news_get.return_value = _mock_response([])

    result = investigate("AAPL", config=_full_config())

    value_result = next(a for a in result.analysis_results if a.analysis_id == "value")
    assert value_result.provenance.ai_provider == "anthropic"
    assert value_result.provenance.ai_model == "claude-sonnet-5"


def test_investigate_skips_strategies_when_provider_injected() -> None:
    """Regresión: con un `provider` de prueba inyectado (caso ya cubierto
    por las pruebas existentes de `investigate`), las estrategias no
    deben intentarse — evita romper pruebas ya existentes que no las
    anticipan (ej. `mock_post.side_effect` con solo 2 respuestas)."""

    class _DummyProvider:
        def fetch(self, ticker: str) -> RawProviderData:
            return RawProviderData(
                ticker=ticker,
                payload={
                    "income_statement": [
                        {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
                    ],
                    "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
                    "quote": [
                        {
                            "price": 185.5,
                            "marketCap": 2_900_000_000_000.0,
                            "timestamp": 1735689600,
                        }
                    ],
                },
                metadata=ProviderMetadata(
                    source="dummy_provider",
                    queried_at=datetime.now(timezone.utc),
                    reliability="alta",
                ),
            )

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("hallazgo salud financiera"),
            _mock_anthropic_response("hallazgo valoración"),
        ]
        result = investigate(
            "AAPL",
            config=_full_config(),
            provider=_DummyProvider(),
        )

    analysis_ids = [analysis.analysis_id for analysis in result.analysis_results]
    assert "value" not in analysis_ids
    assert "growth" not in analysis_ids
    assert "quality" not in analysis_ids
    assert len(result.analysis_results) == 2


@patch("investmentops.data_providers.news.requests.get")
@patch("investmentops.ai_providers.anthropic_provider.requests.post")
@patch("investmentops.data_providers.fundamentals.requests.get")
def test_investigate_captures_strategy_ai_failure_as_analysis_engine_failure(
    mock_fmp_get: Mock, mock_post: Mock, mock_news_get: Mock
) -> None:
    mock_fmp_get.side_effect = _fmp_get_side_effect
    mock_post.return_value = _mock_response({}, status_code=500)
    mock_news_get.return_value = _mock_response([])

    result = investigate("AAPL", config=_full_config())

    value_failure = next(f for f in result.failures if f.identifier == "value")
    assert value_failure.stage == "analysis_engine"