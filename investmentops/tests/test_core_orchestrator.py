"""Pruebas para el orquestador mínimo (investmentops.core.orchestrator):
`fetch_raw_data` (disparo de la consulta al proveedor de datos),
`fetch_and_normalize` (paso de esos datos crudos a la capa de
normalización) y `run_analysis_engines` (invocación secuencial de los
agentes de salud financiera y valoración).

Cubre las tareas "Implementar la función que recibe un ticker y dispara
la consulta al proveedor de Fase 1", "Implementar el paso de datos
crudos a la capa de normalización" e "Implementar la invocación
secuencial de los dos agentes de análisis (salud financiera, valoración)
sobre el modelo normalizado" (TASKS.md, Fase 1, "Orquestador mínimo"). No
prueba el ensamblado en `ResearchResult` ni el manejo de fallos
parciales: esas son tareas separadas y posteriores de la misma sección.
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderError
from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.analysis_engines.prompts import PromptError
from investmentops.core.orchestrator import (
    NormalizedCompanyData,
    fetch_and_normalize,
    fetch_raw_data,
    run_analysis_engines,
)
from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_layer.normalization import NormalizationError
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que cumple el contrato `DataProvider`."""

    def __init__(self, payload: dict | None = None) -> None:
        self.received_ticker: str | None = None
        self._payload = payload if payload is not None else {"revenue": 1000}

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


class _FailingProvider:
    """Proveedor mínimo de prueba que señala un fallo mediante el contrato."""

    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"Ticker '{ticker}' no encontrado")


def _mock_response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


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


def _sample_company_data() -> NormalizedCompanyData:
    return NormalizedCompanyData(
        financial_statement=FinancialStatement(
            revenue=1_000_000.0,
            net_income=150_000.0,
            debt=400_000.0,
            source="fmp",
            period_end=date(2025, 12, 31),
        ),
        market_data=MarketData(
            price=185.5,
            market_cap=2_900_000_000_000.0,
            multiples={},
            source="fmp",
            as_of=date(2025, 12, 31),
        ),
    )


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


# --- fetch_raw_data ----------------------------------------------------------


def test_fetch_raw_data_uses_injected_provider() -> None:
    provider = _DummyProvider()

    result = fetch_raw_data("AAPL", provider=provider)

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert provider.received_ticker == "AAPL"


def test_fetch_raw_data_propagates_provider_failure() -> None:
    with pytest.raises(DataProviderError, match="no encontrado"):
        fetch_raw_data("NOPE", provider=_FailingProvider())


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raw_data_defaults_to_fmp_provider(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response([{"revenue": 1000, "netIncome": 100}]),
        _mock_response([{"totalDebt": 500}]),
        _mock_response([{"price": 150.0, "marketCap": 2_000_000}]),
    ]
    config = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
    }

    result = fetch_raw_data("AAPL", config=config)

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert result.metadata.source == "fmp"
    assert mock_get.call_count == 3


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_raw_data_propagates_fmp_failure_for_missing_ticker(
    mock_get: Mock,
) -> None:
    mock_get.side_effect = [
        _mock_response([]),
        _mock_response([]),
        _mock_response([]),
    ]
    config = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
    }

    with pytest.raises(DataProviderError, match="no existe"):
        fetch_raw_data("NOPE", config=config)


# --- fetch_and_normalize -------------------------------------------------------


def test_fetch_and_normalize_returns_normalized_company_data() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    result = fetch_and_normalize("AAPL", provider=provider)

    assert isinstance(result, NormalizedCompanyData)
    assert isinstance(result.financial_statement, FinancialStatement)
    assert isinstance(result.market_data, MarketData)


def test_fetch_and_normalize_builds_financial_statement_from_raw_payload() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    result = fetch_and_normalize("AAPL", provider=provider)

    assert result.financial_statement.revenue == 1_000_000.0
    assert result.financial_statement.net_income == 150_000.0
    assert result.financial_statement.debt == 400_000.0
    assert result.financial_statement.source == "dummy_provider"
    assert result.financial_statement.period_end == date(2025, 12, 31)


def test_fetch_and_normalize_builds_market_data_from_raw_payload() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    result = fetch_and_normalize("AAPL", provider=provider)

    assert result.market_data.price == 185.5
    assert result.market_data.market_cap == 2_900_000_000_000.0
    assert result.market_data.multiples == {}
    assert result.market_data.source == "dummy_provider"
    assert result.market_data.as_of == date(2025, 1, 1)


def test_fetch_and_normalize_passes_ticker_to_provider() -> None:
    provider = _DummyProvider(payload=_complete_payload())

    fetch_and_normalize("AAPL", provider=provider)

    assert provider.received_ticker == "AAPL"


def test_fetch_and_normalize_propagates_data_provider_error() -> None:
    with pytest.raises(DataProviderError, match="no encontrado"):
        fetch_and_normalize("NOPE", provider=_FailingProvider())


def test_fetch_and_normalize_propagates_normalization_error_on_incomplete_payload() -> None:
    """Un payload crudo sin balance_sheet_statement no debe normalizarse en
    silencio ni con datos inventados: debe propagar NormalizationError."""
    incomplete_payload = {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [],
        "quote": [
            {"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}
        ],
    }
    provider = _DummyProvider(payload=incomplete_payload)

    with pytest.raises(NormalizationError, match="debt"):
        fetch_and_normalize("AAPL", provider=provider)


def test_fetch_and_normalize_propagates_normalization_error_when_quote_missing() -> None:
    incomplete_payload = {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
        "quote": [],
    }
    provider = _DummyProvider(payload=incomplete_payload)

    with pytest.raises(NormalizationError, match="quote"):
        fetch_and_normalize("AAPL", provider=provider)


@patch("investmentops.data_providers.fundamentals.requests.get")
def test_fetch_and_normalize_defaults_to_fmp_provider(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _mock_response(
            [{"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}]
        ),
        _mock_response([{"date": "2025-12-31", "totalDebt": 400_000.0}]),
        _mock_response(
            [{"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}]
        ),
    ]
    config = {
        "data_providers": {"fundamentals": {"api_key": "fake-key"}},
    }

    result = fetch_and_normalize("AAPL", config=config)

    assert result.financial_statement.source == "fmp"
    assert result.market_data.source == "fmp"
    assert mock_get.call_count == 3


# --- run_analysis_engines ------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_analysis_engines_returns_both_results_in_order(mock_post: Mock) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    company_data = _sample_company_data()

    results = run_analysis_engines(company_data, config=_analysis_config())

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(result, AnalysisResult) for result in results)
    assert results[0].analysis_id == "financial_health"
    assert results[1].analysis_id == "valuation"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_analysis_engines_invokes_financial_health_before_valuation(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    company_data = _sample_company_data()

    run_analysis_engines(company_data, config=_analysis_config())

    first_call_content = mock_post.call_args_list[0].kwargs["json"]["messages"][0][
        "content"
    ]
    second_call_content = mock_post.call_args_list[1].kwargs["json"]["messages"][0][
        "content"
    ]
    assert "salud financiera" in first_call_content.lower()
    assert "valoración" in second_call_content.lower()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_analysis_engines_results_carry_expected_findings(mock_post: Mock) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    company_data = _sample_company_data()

    financial_health_result, valuation_result = run_analysis_engines(
        company_data, config=_analysis_config()
    )

    assert financial_health_result.findings == ["La empresa muestra un margen saludable."]
    assert valuation_result.findings == ["La empresa parece razonablemente valorada."]
    assert financial_health_result.supporting_metrics == {
        "net_margin": pytest.approx(0.15),
        "debt_to_revenue": pytest.approx(0.4),
    }
    assert valuation_result.supporting_metrics["price_to_earnings"] is not None
    assert valuation_result.supporting_metrics["price_to_sales"] is not None


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_run_analysis_engines_does_not_invoke_valuation_if_financial_health_fails(
    mock_post: Mock,
) -> None:
    """Un fallo del primer agente detiene el flujo (comportamiento esperado
    de esta tarea; manejar el fallo sin detener el flujo es una tarea
    separada y posterior de TASKS.md)."""
    mock_post.return_value = _mock_response({}, status_code=500)
    company_data = _sample_company_data()

    with pytest.raises(AIProviderError, match="error \\(500\\)"):
        run_analysis_engines(company_data, config=_analysis_config())

    assert mock_post.call_count == 1


def test_run_analysis_engines_propagates_agent_provider_selection_error() -> None:
    from investmentops.ai_providers.selection import AgentProviderSelectionError

    company_data = _sample_company_data()
    config: dict = {"agents": {}, "ai_providers": {}}

    with pytest.raises(AgentProviderSelectionError, match="No se pudo resolver"):
        run_analysis_engines(company_data, config=config)


def test_run_analysis_engines_propagates_prompt_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investmentops.analysis_engines.financial_health as fh_module

    def _broken_load_prompt(agent_id: str) -> str:
        raise PromptError(f"No se encontró el prompt de '{agent_id}' (simulado).")

    monkeypatch.setattr(fh_module, "load_prompt", _broken_load_prompt)

    company_data = _sample_company_data()

    with pytest.raises(PromptError, match="simulado"):
        run_analysis_engines(company_data, config=_analysis_config())
