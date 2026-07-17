"""Pruebas para el parámetro `formats` de `generate_reports`/
`investigate_and_generate_reports` (investmentops.core.orchestrator).

Cubre la parte del orquestador de la tarea "Añadir al comando CLI la
opción de formato de salida (markdown, html, o ambos)" (TASKS.md, Fase 2,
"Orquestador y CLI"). No prueba de nuevo el comportamiento por defecto
(`formats=None` genera ambos formatos, orden `[markdown, html]`): eso ya
está cubierto en `test_core_orchestrator_reports.py` y debe seguir
pasando sin cambios, ya que ese es precisamente el criterio de no-ruptura
de esta extensión.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from investmentops.core.orchestrator import generate_reports, investigate
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

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


class _FailingProvider:
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


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_generate_reports_with_formats_markdown_only(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("hallazgo salud financiera"),
        _mock_anthropic_response("hallazgo valoración"),
    ]
    result = investigate(
        "AAPL", config=_analysis_config(), provider=_DummyProvider(_complete_payload())
    )

    paths = generate_reports(result, output_dir=tmp_path, formats=("markdown",))

    assert paths == [tmp_path / "AAPL.md"]
    assert paths[0].is_file()
    assert not (tmp_path / "AAPL.html").exists()


@patch("investmentops.ai_providers.anthropic_provider.requests.post")
def test_generate_reports_with_formats_html_only(
    mock_post: Mock, tmp_path: Path
) -> None:
    mock_post.side_effect = [
        _mock_anthropic_response("hallazgo salud financiera"),
        _mock_anthropic_response("hallazgo valoración"),
    ]
    result = investigate(
        "AAPL", config=_analysis_config(), provider=_DummyProvider(_complete_payload())
    )

    paths = generate_reports(result, output_dir=tmp_path, formats=("html",))

    assert paths == [tmp_path / "AAPL.html"]
    assert paths[0].is_file()
    assert not (tmp_path / "AAPL.md").exists()


def test_generate_reports_with_formats_order_independent_of_input_order(
    tmp_path: Path,
) -> None:
    """El orden de salida es siempre [markdown, html] cuando ambos se piden,
    sin importar el orden en que aparezcan en `formats`."""
    result = investigate("NOPE", provider=_FailingProvider())

    paths = generate_reports(result, output_dir=tmp_path, formats=("html", "markdown"))

    assert paths == [tmp_path / "NOPE.md", tmp_path / "NOPE.html"]


def test_generate_reports_raises_value_error_for_empty_formats(tmp_path: Path) -> None:
    result = investigate("NOPE", provider=_FailingProvider())

    with pytest.raises(ValueError, match="al menos un formato"):
        generate_reports(result, output_dir=tmp_path, formats=())


def test_generate_reports_raises_value_error_for_unknown_format(tmp_path: Path) -> None:
    result = investigate("NOPE", provider=_FailingProvider())

    with pytest.raises(ValueError, match="desconocido"):
        generate_reports(result, output_dir=tmp_path, formats=("pdf",))


def test_generate_reports_default_formats_still_returns_both_in_order(
    tmp_path: Path,
) -> None:
    """Regresión explícita: sin `formats`, el comportamiento histórico
    (ambos formatos, orden [markdown, html]) no cambia."""
    result = investigate("NOPE", provider=_FailingProvider())

    paths = generate_reports(result, output_dir=tmp_path)

    assert paths == [tmp_path / "NOPE.md", tmp_path / "NOPE.html"]
