"""Pruebas para la conexión del subcomando `compare` con el orquestador
(investmentops.cli.dispatch).

Cubre la tarea "Conectar el comando CLI de comparación con esa función
del orquestador" (TASKS.md, Fase 5, "Orquestador y CLI"). No prueba de
nuevo el parseo de argumentos de `compare` (ya cubierto en
`test_cli.py`/`build_parser`), ni `investmentops.core.orchestrator.compare`
en detalle (ya cubierta en sus propias pruebas del orquestador): solo la
conexión entre `dispatch` y esa función ya existente, siguiendo el mismo
patrón ya usado en `test_cli_dispatch.py` para `"investigate"`.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from investmentops.cli import dispatch, parse_args
from investmentops.core.orchestrator import ComparisonResult
from investmentops.core.research_result import ResearchResult
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que devuelve un payload con forma de FMP."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.received_tickers: list[str] = []

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_tickers.append(ticker)
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingProvider:
    """Proveedor mínimo de prueba que señala un fallo mediante el contrato."""

    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"Ticker '{ticker}' no encontrado")


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


def test_dispatch_returns_comparison_result_for_compare_command() -> None:
    args = parse_args(["compare", "AAPL", "MSFT"])
    provider = _DummyProvider(_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("hallazgo salud financiera AAPL"),
            _mock_anthropic_response("hallazgo valoración AAPL"),
            _mock_anthropic_response("hallazgo salud financiera MSFT"),
            _mock_anthropic_response("hallazgo valoración MSFT"),
        ]
        result = dispatch(args, config=_analysis_config(), provider=provider)

    assert isinstance(result, ComparisonResult)
    assert result.tickers == ["AAPL", "MSFT"]
    assert len(result.results) == 2
    assert all(isinstance(r, ResearchResult) for r in result.results)
    assert result.results[0].company.ticker == "AAPL"
    assert result.results[1].company.ticker == "MSFT"


def test_dispatch_passes_each_ticker_to_the_provider_in_order() -> None:
    args = parse_args(["compare", "AAPL", "MSFT", "GOOGL"])
    provider = _DummyProvider(_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("hallazgo") for _ in range(6)
        ]
        dispatch(args, config=_analysis_config(), provider=provider)

    assert provider.received_tickers == ["AAPL", "MSFT", "GOOGL"]


def test_dispatch_compare_does_not_normalize_tickers_before_passing_them() -> None:
    args = parse_args(["compare", "ecopetrol.cl", "PFBCOLOM.CL"])
    provider = _DummyProvider(_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("hallazgo") for _ in range(4)
        ]
        dispatch(args, config=_analysis_config(), provider=provider)

    assert provider.received_tickers == ["ecopetrol.cl", "PFBCOLOM.CL"]


def test_dispatch_compare_captures_data_provider_failure_for_one_ticker_without_raising() -> None:
    """Un ticker inválido no debe detener la comparación de los demás:
    el fallo se refleja en el `ResearchResult` individual de ese ticker."""
    args = parse_args(["compare", "NOPE", "AAPL"])

    class _MixedProvider:
        def fetch(self, ticker: str) -> RawProviderData:
            if ticker == "NOPE":
                raise DataProviderError("Ticker 'NOPE' no encontrado")
            return _DummyProvider(_complete_payload()).fetch(ticker)

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("hallazgo") for _ in range(2)
        ]
        result = dispatch(args, config=_analysis_config(), provider=_MixedProvider())

    assert isinstance(result, ComparisonResult)
    assert result.results[0].analysis_results == []
    assert len(result.results[0].failures) == 1
    assert result.results[0].failures[0].stage == "data_provider"
    assert len(result.results[1].analysis_results) == 2
    assert result.results[1].failures == []


def test_dispatch_compare_returns_result_per_ticker_when_all_fail() -> None:
    args = parse_args(["compare", "NOPE1", "NOPE2"])

    result = dispatch(args, provider=_FailingProvider())

    assert isinstance(result, ComparisonResult)
    assert len(result.results) == 2
    assert all(r.analysis_results == [] for r in result.results)
    assert all(len(r.failures) == 1 for r in result.results)