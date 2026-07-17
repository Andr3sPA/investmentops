"""Pruebas para la generación de reportes desde el orquestador
(investmentops.core.orchestrator.generate_reports /
investigate_and_generate_reports).

Cubre la tarea "Extender el orquestador para invocar los generadores de
reporte tras ensamblar el resultado de investigación" (TASKS.md, Fase 2,
"Orquestador y CLI"). No prueba de nuevo `render_markdown`/`render_html`
(ya cubiertos en `test_reports_markdown.py`/`test_reports_html.py`) ni
`save_markdown_report`/`save_html_report` en detalle (ya cubiertos en
`test_reports_markdown_save.py`/`test_reports_html_save.py`); solo la
conexión entre el orquestador y esos generadores ya existentes.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from investmentops.core.orchestrator import (
    generate_reports,
    investigate,
    investigate_and_generate_reports,
)
from investmentops.core.research_result import ResearchFailure
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que devuelve un payload con forma de FMP."""

    def __init__(self, payload: dict | None = None) -> None:
        self.received_ticker: str | None = None
        self._payload = payload if payload is not None else _complete_payload()

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


# --- generate_reports ---------------------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_generate_reports_returns_markdown_and_html_paths_in_order(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()
    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    paths = generate_reports(result, output_dir=tmp_path)

    assert paths == [tmp_path / "AAPL.md", tmp_path / "AAPL.html"]
    assert paths[0].is_file()
    assert paths[1].is_file()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_generate_reports_markdown_content_matches_render_markdown(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()
    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    paths = generate_reports(result, output_dir=tmp_path)

    markdown_content = paths[0].read_text(encoding="utf-8")
    assert "# Investigación: AAPL" in markdown_content
    assert "La empresa muestra un margen saludable." in markdown_content
    assert "La empresa parece razonablemente valorada." in markdown_content


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_generate_reports_html_content_matches_render_html(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()
    result = investigate("AAPL", config=_analysis_config(), provider=provider)

    paths = generate_reports(result, output_dir=tmp_path)

    html_content = paths[1].read_text(encoding="utf-8")
    assert html_content.startswith("<!DOCTYPE html>")
    assert "La empresa muestra un margen saludable." in html_content


def test_generate_reports_handles_result_with_only_failures(tmp_path: Path) -> None:
    """Un `ResearchResult` con fallos parciales (sin análisis completados)
    igual debe poder generar sus reportes, mostrando secciones vacías."""
    result = investigate("NOPE", provider=_FailingProvider())
    assert result.analysis_results == []
    assert len(result.failures) == 1

    paths = generate_reports(result, output_dir=tmp_path)

    assert paths == [tmp_path / "NOPE.md", tmp_path / "NOPE.html"]
    assert paths[0].is_file()
    assert paths[1].is_file()


def test_generate_reports_uses_output_dir_from_config_when_not_given(
    tmp_path: Path,
) -> None:
    config = {"output": {"output_dir": str(tmp_path / "from_config")}}
    result = investigate("NOPE", config=config, provider=_FailingProvider())

    paths = generate_reports(result, config=config)

    assert paths[0] == tmp_path / "from_config" / "NOPE.md"
    assert paths[1] == tmp_path / "from_config" / "NOPE.html"
    assert paths[0].is_file()
    assert paths[1].is_file()


# --- investigate_and_generate_reports ------------------------------------------


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_investigate_and_generate_reports_returns_result_and_paths(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("La empresa muestra un margen saludable."),
        _mock_anthropic_response("La empresa parece razonablemente valorada."),
    ]
    provider = _DummyProvider()

    result, paths = investigate_and_generate_reports(
        "AAPL", config=_analysis_config(), provider=provider, output_dir=tmp_path
    )

    assert result.company.ticker == "AAPL"
    assert len(result.analysis_results) == 2
    assert paths == [tmp_path / "AAPL.md", tmp_path / "AAPL.html"]
    assert paths[0].is_file()
    assert paths[1].is_file()


def test_investigate_and_generate_reports_still_generates_reports_on_data_provider_failure(
    tmp_path: Path,
) -> None:
    """Un fallo de la fuente de datos (`ResearchFailure` dentro del
    `ResearchResult`) no debe impedir que igual se generen los reportes,
    ya que `investigate(...)` nunca deja escapar `DataProviderError`."""
    result, paths = investigate_and_generate_reports(
        "NOPE", provider=_FailingProvider(), output_dir=tmp_path
    )

    assert result.analysis_results == []
    assert len(result.failures) == 1
    assert isinstance(result.failures[0], ResearchFailure)
    assert paths == [tmp_path / "NOPE.md", tmp_path / "NOPE.html"]
    assert paths[0].is_file()
    assert paths[1].is_file()


def test_investigate_and_generate_reports_does_not_normalize_call_signature() -> None:
    """`investigate_and_generate_reports` no debe requerir `provider` ni
    `output_dir`: ambos deben seguir siendo opcionales (mismo criterio ya
    usado por `investigate`), aunque en esta prueba forzamos un fallo de
    proveedor para no depender de red real ni de `config.local.toml`."""
    result, paths = investigate_and_generate_reports("NOPE", provider=_FailingProvider())

    assert result.analysis_results == []
    assert len(paths) == 2
