"""Pruebas para el guardado del reporte HTML en disco
(investmentops.reports.html.save_html_report).

Cubre la tarea "Implementar el guardado del archivo HTML generado en una
ruta local configurable" (TASKS.md, Fase 2, "Generador HTML"). No prueba
de nuevo `render_html` (ya cubierto en `test_reports_html.py`); solo el
guardado del texto ya renderizado. Sigue el mismo patrón ya usado en
`test_reports_markdown_save.py` para `save_markdown_report`.
"""

from pathlib import Path

import pytest

from investmentops.reports.html import save_html_report
from investmentops.reports.markdown import DEFAULT_OUTPUT_DIR, ReportError


def test_save_writes_file_with_given_content(tmp_path: Path) -> None:
    file_path = save_html_report(
        "AAPL", "<!DOCTYPE html><html></html>\n", output_dir=tmp_path
    )

    assert file_path == tmp_path / "AAPL.html"
    assert file_path.read_text(encoding="utf-8") == "<!DOCTYPE html><html></html>\n"


def test_save_normalizes_ticker_to_uppercase_filename(tmp_path: Path) -> None:
    file_path = save_html_report("aapl", "contenido", output_dir=tmp_path)

    assert file_path == tmp_path / "AAPL.html"


def test_save_creates_output_directory_if_missing(tmp_path: Path) -> None:
    output_dir = tmp_path / "nested" / "reports"

    file_path = save_html_report("AAPL", "contenido", output_dir=output_dir)

    assert file_path.parent == output_dir
    assert file_path.is_file()


def test_save_overwrites_existing_report_for_same_ticker(tmp_path: Path) -> None:
    save_html_report("AAPL", "primera versión", output_dir=tmp_path)
    file_path = save_html_report("AAPL", "segunda versión", output_dir=tmp_path)

    assert file_path.read_text(encoding="utf-8") == "segunda versión"


def test_save_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="no puede estar vacío"):
        save_html_report("   ", "contenido", output_dir=tmp_path)


def test_save_reads_output_dir_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"output": {"output_dir": str(tmp_path / "from_config")}}

    file_path = save_html_report("AAPL", "contenido", config=config)

    assert file_path == tmp_path / "from_config" / "AAPL.html"
    assert file_path.is_file()


def test_save_uses_default_output_dir_when_config_has_no_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config: dict = {"output": {}}

    file_path = save_html_report("AAPL", "contenido", config=config)

    assert file_path == Path(DEFAULT_OUTPUT_DIR) / "AAPL.html"
    assert file_path.is_file()


def test_save_html_and_markdown_share_the_same_output_directory(
    tmp_path: Path,
) -> None:
    """Ambos formatos comparten `[output].output_dir`: un mismo ticker
    produce `<TICKER>.md` y `<TICKER>.html` en la misma carpeta."""
    from investmentops.reports.markdown import save_markdown_report

    config = {"output": {"output_dir": str(tmp_path)}}

    md_path = save_markdown_report("AAPL", "contenido md", config=config)
    html_path = save_html_report("AAPL", "contenido html", config=config)

    assert md_path.parent == html_path.parent == tmp_path


def test_report_error_raised_by_save_html_report_is_the_shared_report_error() -> None:
    """Confirma que `save_html_report` usa el mismo `ReportError` que
    `save_markdown_report`, no una excepción propia y separada."""
    from investmentops.reports.markdown import ReportError as MarkdownReportError

    with pytest.raises(MarkdownReportError):
        save_html_report("   ", "contenido")
