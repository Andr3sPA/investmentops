"""Pruebas para el punto de entrada de la CLI (investmentops.__main__.main).

Cubre dos tareas:

- "Implementar mensajes de error legibles en consola ante fallos del
  flujo" (TASKS.md, Fase 1, "CLI").
- "Implementar el mensaje final en consola indicando dónde quedaron
  guardados los reportes generados" (TASKS.md, Fase 2, "Orquestador y
  CLI").

Solo prueba `main()`: el parseo de argumentos (`test_cli.py`,
`test_cli_ticker_validation.py`, `test_cli_format.py`), la conexión con
el orquestador (`test_cli_dispatch.py`, `test_cli_format.py`) y el
formateo del resultado (`test_cli_output.py`) ya están cubiertos en sus
propios archivos de prueba. `dispatch` se mockea directamente (en vez de
invocar el flujo real) porque lo único relevante para estas tareas es
cómo `main()` reacciona a un éxito (con o sin reportes generados) o a un
`ConfigError`, no el contenido concreto del `ResearchResult`.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

import investmentops.__main__ as main_module
from investmentops.config import ConfigError
from investmentops.core.research_result import ResearchResult
from investmentops.data_layer import Company


def _empty_research_result(ticker: str = "AAPL") -> ResearchResult:
    return ResearchResult(
        company=Company(ticker=ticker, name="", sector="", market=""),
        analysis_results=[],
        failures=[],
        generated_at=datetime.now(timezone.utc),
    )


def test_main_returns_zero_and_prints_result_on_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        main_module, "dispatch", lambda args, **kwargs: _empty_research_result("AAPL")
    )

    exit_code = main_module.main(["investigate", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AAPL" in captured.out
    assert captured.err == ""


def test_main_returns_one_and_prints_readable_message_on_config_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _raise_config_error(args, **kwargs):
        raise ConfigError(
            "No se encontró el archivo de configuración local en "
            "'/fake/config.local.toml'. Antes de usar InvestmentOps, "
            "copia la plantilla y completa tus credenciales:\n"
            "    cp config.example.toml config.local.toml"
        )

    monkeypatch.setattr(main_module, "dispatch", _raise_config_error)

    exit_code = main_module.main(["investigate", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "Error de configuración" in captured.err
    assert "config.local.toml" in captured.err


def test_main_config_error_message_is_not_printed_to_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Confirma que el mensaje de error va a stderr, no se mezcla con stdout."""

    def _raise_config_error(args, **kwargs):
        raise ConfigError("config.local.toml no encontrado.")

    monkeypatch.setattr(main_module, "dispatch", _raise_config_error)

    main_module.main(["investigate", "AAPL"])

    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_main_propagates_system_exit_for_missing_ticker() -> None:
    with pytest.raises(SystemExit):
        main_module.main(["investigate"])


def test_main_propagates_system_exit_for_unknown_command() -> None:
    with pytest.raises(SystemExit):
        main_module.main(["unknown_command", "AAPL"])


def test_main_accepts_explicit_argv_without_touching_sys_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`main(argv=[...])` no debe depender de `sys.argv` real."""
    monkeypatch.setattr(
        main_module,
        "dispatch",
        lambda args, **kwargs: _empty_research_result("ECOPETROL.CL"),
    )
    monkeypatch.setattr("sys.argv", ["investmentops"])  # sin argumentos reales

    exit_code = main_module.main(["investigate", "ECOPETROL.CL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ECOPETROL.CL" in captured.out


# --- Mensaje final con las rutas de los reportes generados (--format) --------


def test_main_prints_report_paths_when_dispatch_returns_tuple(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    report_paths = [tmp_path / "AAPL.md", tmp_path / "AAPL.html"]
    monkeypatch.setattr(
        main_module,
        "dispatch",
        lambda args, **kwargs: (_empty_research_result("AAPL"), report_paths),
    )

    exit_code = main_module.main(["investigate", "AAPL", "--format", "both"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AAPL" in captured.out
    assert "Reportes generados:" in captured.out
    assert str(report_paths[0]) in captured.out
    assert str(report_paths[1]) in captured.out


def test_main_report_paths_appear_after_research_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    report_paths = [tmp_path / "AAPL.md"]
    monkeypatch.setattr(
        main_module,
        "dispatch",
        lambda args, **kwargs: (_empty_research_result("AAPL"), report_paths),
    )

    main_module.main(["investigate", "AAPL", "--format", "markdown"])

    captured = capsys.readouterr()
    assert captured.out.index("AAPL") < captured.out.index("Reportes generados:")


def test_main_prints_single_report_path_for_single_format(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    report_paths = [tmp_path / "AAPL.html"]
    monkeypatch.setattr(
        main_module,
        "dispatch",
        lambda args, **kwargs: (_empty_research_result("AAPL"), report_paths),
    )

    main_module.main(["investigate", "AAPL", "--format", "html"])

    captured = capsys.readouterr()
    assert "Reportes generados:" in captured.out
    assert str(report_paths[0]) in captured.out
    assert captured.out.count("  - ") == 1


def test_main_does_not_print_reports_section_when_dispatch_returns_plain_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sin `--format`, `dispatch` sigue devolviendo un `ResearchResult` a
    secas (no una tupla); `main()` no debe imprimir la sección de
    reportes en ese caso."""
    monkeypatch.setattr(
        main_module, "dispatch", lambda args, **kwargs: _empty_research_result("AAPL")
    )

    exit_code = main_module.main(["investigate", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Reportes generados:" not in captured.out
