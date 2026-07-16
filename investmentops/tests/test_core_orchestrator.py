"""Pruebas para el orquestador mínimo (investmentops.core.orchestrator):
`fetch_raw_data` (disparo de la consulta al proveedor de datos),
`fetch_and_normalize` (paso de esos datos crudos a la capa de
normalización), `run_analysis_engines` (invocación secuencial de los
agentes de salud financiera y valoración), `assemble_research_result`
(ensamblado de ambos resultados en un "Resultado de investigación"
único) e `investigate` (flujo completo con manejo de fallos parciales,
sin detener el resto del flujo).

Cubre las tareas "Implementar la función que recibe un ticker y dispara
la consulta al proveedor de Fase 1", "Implementar el paso de datos
crudos a la capa de normalización", "Implementar la invocación
secuencial de los dos agentes de análisis (salud financiera, valoración)
sobre el modelo normalizado", "Implementar el ensamblado de ambos
resultados en un 'Resultado de investigación' único" e "Implementar el
manejo de fallo del proveedor de datos o del proveedor de IA sin
detener el resto del flujo, dejándolo explícito en el resultado"
(TASKS.md, Fase 1, "Orquestador mínimo").
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.ai_providers import AIProviderError
from investmentops.analysis_engines.contracts import (
    AnalysisProvenance,
    AnalysisResult,
)
from investmentops.analysis_engines.prompts import PromptError
from investmentops.core.orchestrator import (
    NormalizedCompanyData,
    assemble_research_result,
    fetch_and_normalize,
    fetch_raw_data,
    investigate,
    run_analysis_engines,
)
from investmentops.core.research_result import ResearchFailure, ResearchResult
from investmentops.data_layer import Company, FinancialStatement, MarketData
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


def _mock_anthropic_error(status_code: int = 500) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {}
    return response


def _sample_analysis_result(analysis_id: str = "financial_health") -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        findings=["hallazgo de prueba"],
        supporting_metrics={"metric": 1.0},
        limitations=[],
        provenance=AnalysisProvenance(
            ai_provider="dummy_provider",
            ai_model="dummy-model",
            generated_at=datetime.now(timezone.utc),
        ),
    )


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
    """`run_analysis_engines` mantiene su comportamiento "todo o nada":
    un fallo del primer agente detiene el flujo. `investigate` (probado
    más abajo) es la función que sí maneja este caso sin detenerse."""
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


# --- assemble_research_result --------------------------------------------------


def test_assemble_returns_research_result_instance() -> None:
    analysis_results = [
        _sample_analysis_result("financial_health"),
        _sample_analysis_result("valuation"),
    ]

    result = assemble_research_result("AAPL", analysis_results)

    assert isinstance(result, ResearchResult)


def test_assemble_builds_minimal_company_with_only_ticker() -> None:
    result = assemble_research_result("AAPL", [])

    assert isinstance(result.company, Company)
    assert result.company.ticker == "AAPL"
    assert result.company.name == ""
    assert result.company.sector == ""
    assert result.company.market == ""


def test_assemble_normalizes_ticker_to_uppercase() -> None:
    result = assemble_research_result("aapl", [])

    assert result.company.ticker == "AAPL"


def test_assemble_includes_analysis_results_as_given() -> None:
    financial_health = _sample_analysis_result("financial_health")
    valuation = _sample_analysis_result("valuation")

    result = assemble_research_result("AAPL", [financial_health, valuation])

    assert result.analysis_results == [financial_health, valuation]


def test_assemble_defaults_failures_to_empty_list() -> None:
    result = assemble_research_result("AAPL", [_sample_analysis_result()])

    assert result.failures == []


def test_assemble_accepts_explicit_failures() -> None:
    failure = ResearchFailure(
        stage="analysis_engine",
        identifier="valuation",
        reason="El proveedor de IA no respondió",
    )

    result = assemble_research_result(
        "AAPL", [_sample_analysis_result("financial_health")], failures=[failure]
    )

    assert result.failures == [failure]


def test_assemble_defaults_generated_at_to_now() -> None:
    before = datetime.now(timezone.utc)

    result = assemble_research_result("AAPL", [])

    after = datetime.now(timezone.utc)
    assert before <= result.generated_at <= after


def test_assemble_accepts_explicit_generated_at() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = assemble_research_result("AAPL", [], generated_at=fixed_time)

    assert result.generated_at == fixed_time


def test_assemble_result_is_immutable() -> None:
    result = assemble_research_result("AAPL", [])

    with pytest.raises(AttributeError):
        result.company = Company(ticker="MSFT", name="", sector="", market="")  # type: ignore[misc]


def test_assemble_end_to_end_with_run_analysis_engines_output() -> None:
    """Confirma que la salida de `run_analysis_engines` se puede pasar
    directamente a `assemble_research_result` sin transformación."""
    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("La empresa muestra un margen saludable."),
            _mock_anthropic_response("La empresa parece razonablemente valorada."),
        ]
        company_data = _sample_company_data()
        analysis_results = run_analysis_engines(company_data, config=_analysis_config())

    result = assemble_research_result("AAPL", analysis_results)

    assert result.company.ticker == "AAPL"
    assert len(result.analysis_results) == 2
    assert result.analysis_results[0].analysis_id == "financial_health"
    assert result.analysis_results[1].analysis_id == "valuation"
    assert result.failures == []


# --- investigate (manejo de fallos parciales) ----------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_returns_full_result_when_everything_succeeds(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider(payload=_complete_payload())

    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    assert isinstance(result, ResearchResult)
    assert result.company.ticker == "AAPL"
    assert len(result.analysis_results) == 2
    assert result.analysis_results[0].analysis_id == "financial_health"
    assert result.analysis_results[1].analysis_id == "valuation"
    assert result.failures == []


def test_investigate_captures_data_provider_failure_without_raising() -> None:
    result = investigate("NOPE", provider=_FailingProvider())

    assert isinstance(result, ResearchResult)
    assert result.analysis_results == []
    assert len(result.failures) == 1
    assert result.failures[0].stage == "data_provider"
    assert result.failures[0].identifier == "NOPE"
    assert "no encontrado" in result.failures[0].reason
    assert result.company.ticker == "NOPE"


def test_investigate_captures_normalization_failure_without_raising() -> None:
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

    result = investigate("AAPL", provider=provider)

    assert result.analysis_results == []
    assert len(result.failures) == 1
    assert result.failures[0].stage == "data_provider"
    assert "debt" in result.failures[0].reason


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_continues_to_valuation_when_financial_health_fails(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_error(500),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider(payload=_complete_payload())

    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    assert mock_post.call_count == 2
    assert len(result.analysis_results) == 1
    assert result.analysis_results[0].analysis_id == "valuation"
    assert len(result.failures) == 1
    assert result.failures[0].stage == "analysis_engine"
    assert result.failures[0].identifier == "financial_health"
    assert "500" in result.failures[0].reason


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_continues_after_valuation_fails(mock_post: Mock) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_error(500),
    ]
    provider = _DummyProvider(payload=_complete_payload())

    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    assert mock_post.call_count == 2
    assert len(result.analysis_results) == 1
    assert result.analysis_results[0].analysis_id == "financial_health"
    assert len(result.failures) == 1
    assert result.failures[0].stage == "analysis_engine"
    assert result.failures[0].identifier == "valuation"


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_captures_failures_from_both_agents(mock_post: Mock) -> None:
    mock_post.side_effect = [
        _mock_anthropic_error(500),
        _mock_anthropic_error(500),
    ]
    provider = _DummyProvider(payload=_complete_payload())

    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    assert result.analysis_results == []
    assert len(result.failures) == 2
    assert {failure.identifier for failure in result.failures} == {
        "financial_health",
        "valuation",
    }
    assert all(failure.stage == "analysis_engine" for failure in result.failures)


def test_investigate_propagates_agent_provider_selection_error_as_failure() -> None:
    """`AgentProviderSelectionError` es un fallo esperado de un agente
    concreto (configuración incompleta para ese agente): debe capturarse
    igual que `AIProviderError`, no propagarse."""
    provider = _DummyProvider(payload=_complete_payload())
    config: dict = {"agents": {}, "ai_providers": {}}

    result = investigate("AAPL", config=config, provider=provider)

    assert result.analysis_results == []
    assert len(result.failures) == 2
    assert all(failure.stage == "analysis_engine" for failure in result.failures)


def test_investigate_captures_prompt_error_as_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import investmentops.analysis_engines.financial_health as fh_module

    def _broken_load_prompt(agent_id: str) -> str:
        raise PromptError(f"No se encontró el prompt de '{agent_id}' (simulado).")

    monkeypatch.setattr(fh_module, "load_prompt", _broken_load_prompt)
    provider = _DummyProvider(payload=_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.return_value = _mock_anthropic_response(
            "La empresa parece razonablemente valorada."
        )
        result = investigate("AAPL", config=_analysis_config(), provider=provider)

    assert len(result.failures) == 1
    assert result.failures[0].identifier == "financial_health"
    assert "simulado" in result.failures[0].reason
    assert len(result.analysis_results) == 1
    assert result.analysis_results[0].analysis_id == "valuation"


def test_investigate_result_is_immutable() -> None:
    result = investigate("NOPE", provider=_FailingProvider())

    with pytest.raises(AttributeError):
        result.failures = []  # type: ignore[misc]
