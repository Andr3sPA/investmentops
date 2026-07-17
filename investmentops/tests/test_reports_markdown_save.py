"""Pruebas para el guardado del reporte Markdown en disco
(investmentops.reports.markdown.save_markdown_report).

Cubre la tarea "Implementar el guardado del archivo Markdown generado en
una ruta local configurable" (TASKS.md, Fase 2, "Generador Markdown"). No
prueba de nuevo `render_markdown` (ya cubierto en
`test_reports_markdown.py`); solo el guardado del texto ya renderizado.
"""

from pathlib import Path

import pytest

from investmentops.reports.markdown import (
    DEFAULT_OUTPUT_DIR,
    ReportError,
    save_markdown_report,
)


def test_save_writes_file_with_given_content(tmp_path: Path) -> None:
    file_path = save_markdown_report(
        "AAPL", "# Investigación: AAPL\n", output_dir=tmp_path
    )

    assert file_path == tmp_path / "AAPL.md"
    assert file_path.read_text(encoding="utf-8") == "# Investigación: AAPL\n"


def test_save_normalizes_ticker_to_uppercase_filename(tmp_path: Path) -> None:
    file_path = save_markdown_report("aapl", "contenido", output_dir=tmp_path)

    assert file_path == tmp_path / "AAPL.md"


def test_save_creates_output_directory_if_missing(tmp_path: Path) -> None:
    output_dir = tmp_path / "nested" / "reports"

    file_path = save_markdown_report("AAPL", "contenido", output_dir=output_dir)

    assert file_path.parent == output_dir
    assert file_path.is_file()


def test_save_overwrites_existing_report_for_same_ticker(tmp_path: Path) -> None:
    save_markdown_report("AAPL", "primera versión", output_dir=tmp_path)
    file_path = save_markdown_report("AAPL", "segunda versión", output_dir=tmp_path)

    assert file_path.read_text(encoding="utf-8") == "segunda versión"


def test_save_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="no puede estar vacío"):
        save_markdown_report("   ", "contenido", output_dir=tmp_path)


def test_save_reads_output_dir_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"output": {"output_dir": str(tmp_path / "from_config")}}

    file_path = save_markdown_report("AAPL", "contenido", config=config)

    assert file_path == tmp_path / "from_config" / "AAPL.md"
    assert file_path.is_file()


def test_save_uses_default_output_dir_when_config_has_no_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config: dict = {"output": {}}

    file_path = save_markdown_report("AAPL", "contenido", config=config)

    assert file_path == Path(DEFAULT_OUTPUT_DIR) / "AAPL.md"
    assert file_path.is_file()


def test_report_error_is_a_runtime_error() -> None:
    assert issubclass(ReportError, RuntimeError)
