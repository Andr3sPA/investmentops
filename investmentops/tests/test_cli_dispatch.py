"""Pruebas para la conexión entre la CLI y el orquestador
(investmentops.cli.dispatch).

Cubre la tarea "Conectar el comando con el orquestador" (TASKS.md, Fase
1, "CLI"). No prueba de nuevo el parseo de argumentos (ya cubierto en
`test_cli.py`/`test_cli_ticker_validation.py`), ni la impresión en
consola del resultado ni el manejo de mensajes de error legibles: esas
son tareas separadas y posteriores de la misma sección. `dispatch` se
prueba aquí inyectando un `DataProvider` de prueba (para no depender de
una llamada de red real a FMP) y mockeando `requests.post` de Anthropic,
igual patrón ya usado en `investmentops/tests/test_core_orchestrator.py`.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from investmentops.cli import dispatch, parse_args
from investmentops.core.research_result import ResearchResult
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que cumple el contrato `DataProvider`."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
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


def test_dispatch_returns_research_result_for_investigate_command() -> None:
    args = parse_args(["investigate", "AAPL"])
    provider = _DummyProvider(_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("La empresa muestra un margen saludable."),
            _mock_anthropic_response("La empresa parece razonablemente valorada."),
        ]
        result = dispatch(args, config=_analysis_config(), provider=provider)

    assert isinstance(result, ResearchResult)
    assert result.company.ticker == "AAPL"
    assert len(result.analysis_results) == 2
    assert result.failures == []


def test_dispatch_passes_ticker_from_parsed_args_to_provider() -> None:
    args = parse_args(["investigate", "ECOPETROL.CL"])
    provider = _DummyProvider(_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("La empresa muestra un margen saludable."),
            _mock_anthropic_response("La empresa parece razonablemente valorada."),
        ]
        dispatch(args, config=_analysis_config(), provider=provider)

    assert provider.received_ticker == "ECOPETROL.CL"


def test_dispatch_does_not_normalize_ticker_before_passing_it() -> None:
    """El ticker se pasa tal cual llegó de argparse; la normalización a
    mayúsculas ocurre más abajo en el pipeline (FMPFundamentalsProvider,
    assemble_research_result), no en `dispatch`."""
    args = parse_args(["investigate", "ecopetrol.cl"])
    provider = _DummyProvider(_complete_payload())

    with patch(
        "investmentops.ai_providers.anthropic_provider.requests.post"
    ) as mock_post:
        mock_post.side_effect = [
            _mock_anthropic_response("La empresa muestra un margen saludable."),
            _mock_anthropic_response("La empresa parece razonablemente valorada."),
        ]
        dispatch(args, config=_analysis_config(), provider=provider)

    assert provider.received_ticker == "ecopetrol.cl"


def test_dispatch_captures_data_provider_failure_as_research_failure() -> None:
    """`investigate` ya traduce fallos de la fuente de datos a
    `ResearchFailure`; `dispatch` no debe volver a envolverlos ni dejarlos
    escapar como excepción."""
    args = parse_args(["investigate", "NOPE"])

    result = dispatch(args, provider=_FailingProvider())

    assert isinstance(result, ResearchResult)
    assert result.analysis_results == []
    assert len(result.failures) == 1
    assert result.failures[0].stage == "data_provider"
    assert "no encontrado" in result.failures[0].reason


def test_dispatch_raises_value_error_for_unknown_command() -> None:
    import argparse

    fake_args = argparse.Namespace(command="unknown_command")

    with pytest.raises(ValueError, match="Comando desconocido"):
        dispatch(fake_args)
