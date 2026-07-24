"""Pruebas para el registro de la invocación de los agentes de estrategia
(investmentops.core.orchestrator.run_value_engine / run_growth_engine /
run_quality_engine).

Cubre la tarea "Registrar los nuevos motores de estrategia sin modificar
los motores existentes" (TASKS.md, Fase 6, "Orquestador"). No prueba de
nuevo `fetch_and_normalize`/`fetch_and_normalize_historical` (ya
cubiertas en `test_core_orchestrator.py`) ni
`analyze_value`/`analyze_growth`/`analyze_quality` (ya cubiertas en sus
propios archivos de prueba de Fase 6) más allá de lo necesario para
confirmar que cada `run_*_engine` los encadena correctamente. Tampoco
prueba la incorporación de estos resultados a `ResearchResult`/
`investigate`: esa es la tarea siguiente y separada de la misma sección.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.core.orchestrator import (
    run_growth_engine,
    run_quality_engine,
    run_value_engine,
)
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


class _DummyProvider:
    """Proveedor mínimo de prueba con `fetch` y `fetch_historical`."""

    def __init__(self, payload: dict, historical_payload: dict | None = None) -> None:
        self._payload = payload
        self._historical_payload = historical_payload or payload

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

    def fetch_historical(self, ticker: str, *, period: str = "annual", limit: int = 5):
        return RawProviderData(
            ticker=ticker,
            payload=self._historical_payload,
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


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


def _historical_payload() -> dict:
    return {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_300_000.0, "netIncome": 260_000.0, "source": "fmp", "queried_at": "2026-07-23T00:00:00+00:00"},
            {"date": "2024-12-31", "revenue": 1_200_000.0, "netIncome": 240_000.0, "source": "fmp", "queried_at": "2026-07-23T00:00:00+00:00"},
        ],
        "balance_sheet_statement": [
            {"date": "2025-12-31", "totalDebt": 400_000.0, "source": "fmp", "queried_at": "2026-07-23T00:00:00+00:00"},
            {"date": "2024-12-31", "totalDebt": 350_000.0, "source": "fmp", "queried_at": "2026-07-23T00:00:00+00:00"},
        ],
    }


def _analysis_config(**overrides: object) -> dict:
    config: dict = {
        "agents": {"value": "anthropic", "growth": "anthropic", "quality": "anthropic"},
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


# --- run_value_engine ----------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_value_engine_returns_analysis_result_with_real_provenance(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_anthropic_response("Lectura de value investing.")
    provider = _DummyProvider(_complete_payload())

    result = run_value_engine("AAPL", config=_analysis_config(), provider=provider)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "value"
    assert result.findings == ["Lectura de value investing."]
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"


# --- run_growth_engine ----------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_growth_engine_returns_analysis_result_with_real_provenance(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_anthropic_response("Lectura de growth investing.")
    provider = _DummyProvider(_complete_payload(), _historical_payload())

    result = run_growth_engine("AAPL", config=_analysis_config(), provider=provider)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "growth"
    assert result.findings == ["Lectura de growth investing."]
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_growth_engine_uses_default_period_and_limit(mock_post: Mock) -> None:
    mock_post.return_value = _mock_anthropic_response("Lectura de growth investing.")

    class _TrackingProvider(_DummyProvider):
        def __init__(self) -> None:
            super().__init__(_complete_payload(), _historical_payload())
            self.received_period: str | None = None
            self.received_limit: int | None = None

        def fetch_historical(self, ticker: str, *, period: str = "annual", limit: int = 5):
            self.received_period = period
            self.received_limit = limit
            return super().fetch_historical(ticker, period=period, limit=limit)

    provider = _TrackingProvider()

    run_growth_engine("AAPL", config=_analysis_config(), provider=provider)

    assert provider.received_period == "annual"
    assert provider.received_limit == 5


# --- run_quality_engine ----------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_quality_engine_returns_analysis_result_with_real_provenance(
    mock_post: Mock,
) -> None:
    mock_post.return_value = _mock_anthropic_response("Lectura de quality investing.")
    provider = _DummyProvider(_complete_payload())

    result = run_quality_engine("AAPL", config=_analysis_config(), provider=provider)

    assert isinstance(result, AnalysisResult)
    assert result.analysis_id == "quality"
    assert result.findings == ["Lectura de quality investing."]
    assert result.provenance.ai_provider == "anthropic"
    assert result.provenance.ai_model == "claude-sonnet-5"