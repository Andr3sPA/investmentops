"""Pruebas para la opción de formato de salida de la CLI (`--format`).

Cubre la tarea "Añadir al comando CLI la opción de formato de salida
(markdown, html, o ambos)" (TASKS.md, Fase 2, "Orquestador y CLI"). No
prueba de nuevo el parseo básico del ticker (`test_cli.py`,
`test_cli_ticker_validation.py`) ni el flujo de `dispatch` sin `--format`
(`test_cli_dispatch.py`, que sigue devolviendo `ResearchResult` sin
cambios); solo el nuevo flag `--format` y su conexión con
`investmentops.core.orchestrator.investigate_and_generate_reports`.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from investmentops.cli import build_parser, dispatch, parse_args
from investmentops.core.research_result import ResearchResult
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


class _DummyProvider:
    """Proveedor mínimo de prueba que devuelve un payload con forma de FMP."""

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


# --- Parseo de --format -------------------------------------------------------


def test_parse_args_format_defaults_to_none() -> None:
    args = parse_args(["investigate", "AAPL"])

    assert args.format is None


@pytest.mark.parametrize("value", ["markdown", "html", "both"])
def test_parse_args_accepts_valid_format_values(value: str) -> None:
    args = parse_args(["investigate", "AAPL", "--format", value])

    assert args.format == value


def test_parse_args_raises_system_exit_for_invalid_format() -> None:
    with pytest.raises(SystemExit):
        parse_args(["investigate", "AAPL", "--format", "pdf"])


def test_investigate_subparser_declares_format_option() -> None:
    parser = build_parser()
    investigate_parser = parser._subparsers._group_actions[0].choices["investigate"]
    format_action = next(
        action for action in investigate_parser._actions if action.dest == "format"
    )

    assert format_action.default is None
    assert set(format_action.choices) == {"markdown", "html", "both"}


# --- dispatch sin --format (regresión: comportamiento sin cambios) ------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_dispatch_without_format_still_returns_plain_research_result(
    mock_post: Mock,
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    args = parse_args(["investigate", "AAPL"])
    provider = _DummyProvider(_complete_payload())

    result = dispatch(args, config=_analysis_config(), provider=provider)

    assert isinstance(result, ResearchResult)


# --- dispatch con --format -----------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_dispatch_with_format_markdown_generates_only_markdown_file(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    args = parse_args(["investigate", "AAPL", "--format", "markdown"])
    provider = _DummyProvider(_complete_payload())

    result, paths = dispatch(
        args, config=_analysis_config(), provider=provider, output_dir=tmp_path
    )

    assert isinstance(result, ResearchResult)
    assert paths == [tmp_path / "AAPL.md"]
    assert paths[0].is_file()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_dispatch_with_format_html_generates_only_html_file(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    args = parse_args(["investigate", "AAPL", "--format", "html"])
    provider = _DummyProvider(_complete_payload())

    result, paths = dispatch(
        args, config=_analysis_config(), provider=provider, output_dir=tmp_path
    )

    assert paths == [tmp_path / "AAPL.html"]
    assert paths[0].is_file()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_dispatch_with_format_both_generates_markdown_and_html_in_order(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    args = parse_args(["investigate", "AAPL", "--format", "both"])
    provider = _DummyProvider(_complete_payload())

    result, paths = dispatch(
        args, config=_analysis_config(), provider=provider, output_dir=tmp_path
    )

    assert paths == [tmp_path / "AAPL.md", tmp_path / "AAPL.html"]
    assert paths[0].is_file()
    assert paths[1].is_file()


def test_dispatch_with_format_still_generates_reports_on_data_provider_failure(
    tmp_path: Path,
) -> None:
    """Un fallo de la fuente de datos no debe impedir que se generen los
    reportes (con secciones vacías), mismo criterio ya probado para
    `generate_reports`/`investigate_and_generate_reports` sin CLI de por
    medio (ver test_core_orchestrator_reports.py)."""

    class _FailingProvider:
        def fetch(self, ticker: str) -> RawProviderData:
            from investmentops.data_providers.contracts import DataProviderError

            raise DataProviderError(f"Ticker '{ticker}' no encontrado")

    args = parse_args(["investigate", "NOPE", "--format", "both"])

    result, paths = dispatch(args, provider=_FailingProvider(), output_dir=tmp_path)

    assert result.analysis_results == []
    assert len(result.failures) == 1
    assert paths == [tmp_path / "NOPE.md", tmp_path / "NOPE.html"]
    assert paths[0].is_file()
    assert paths[1].is_file()


def test_dispatch_raises_value_error_for_unknown_command() -> None:
    import argparse

    fake_args = argparse.Namespace(command="unknown_command")

    with pytest.raises(ValueError, match="Comando desconocido"):
        dispatch(fake_args)
