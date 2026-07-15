"""Pruebas para el guardado en caché local de datos normalizados
(investmentops.data_layer.cache).

Cubre la tarea "Implementar el guardado de los datos normalizados en la
caché tras cada consulta" (TASKS.md, Fase 1, "Normalización y
almacenamiento"). No prueba la lectura desde caché ni la verificación de
frescura: eso corresponde a una tarea posterior (ver TASKS.md).
"""

import json
from datetime import date
from pathlib import Path

import pytest

from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_layer.cache import (
    CacheError,
    save_financial_statement,
    save_market_data,
)


def _sample_statement() -> FinancialStatement:
    return FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def _sample_market_data() -> MarketData:
    return MarketData(
        price=185.5,
        market_cap=2_900_000_000_000.0,
        multiples={"pe": 18.4},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def test_save_financial_statement_writes_ticker_file(tmp_path: Path) -> None:
    file_path = save_financial_statement(
        "AAPL", _sample_statement(), cache_path=tmp_path
    )

    assert file_path == tmp_path / "AAPL.json"
    with file_path.open() as f:
        data = json.load(f)

    section = data["financial_statement"]
    assert section["revenue"] == 1_000_000.0
    assert section["net_income"] == 150_000.0
    assert section["debt"] == 400_000.0
    assert section["source"] == "fmp"
    assert section["period_end"] == "2025-12-31"
    assert "cached_at" in section


def test_save_market_data_writes_ticker_file(tmp_path: Path) -> None:
    file_path = save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    section = data["market_data"]
    assert section["price"] == 185.5
    assert section["market_cap"] == 2_900_000_000_000.0
    assert section["multiples"] == {"pe": 18.4}
    assert section["source"] == "fmp"
    assert section["as_of"] == "2025-12-31"
    assert "cached_at" in section


def test_save_normalizes_ticker_to_uppercase_filename(tmp_path: Path) -> None:
    file_path = save_financial_statement(
        "aapl", _sample_statement(), cache_path=tmp_path
    )

    assert file_path == tmp_path / "AAPL.json"


def test_save_merges_with_existing_sections_without_overwriting(
    tmp_path: Path,
) -> None:
    """Guardar market_data no debe borrar un financial_statement ya cacheado."""
    save_financial_statement("AAPL", _sample_statement(), cache_path=tmp_path)
    file_path = save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "market_data" in data


def test_save_overwrites_only_the_updated_section(tmp_path: Path) -> None:
    save_financial_statement("AAPL", _sample_statement(), cache_path=tmp_path)

    newer_statement = FinancialStatement(
        revenue=2_000_000.0,
        net_income=300_000.0,
        debt=500_000.0,
        source="fmp",
        period_end=date(2026, 3, 31),
    )
    file_path = save_financial_statement(
        "AAPL", newer_statement, cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    assert data["financial_statement"]["revenue"] == 2_000_000.0
    assert data["financial_statement"]["period_end"] == "2026-03-31"


def test_save_creates_cache_directory_if_missing(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"

    file_path = save_financial_statement(
        "AAPL", _sample_statement(), cache_path=cache_dir
    )

    assert file_path.parent == cache_dir
    assert file_path.is_file()


def test_save_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        save_financial_statement("   ", _sample_statement(), cache_path=tmp_path)


def test_save_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}

    file_path = save_financial_statement(
        "AAPL", _sample_statement(), config=config
    )

    assert file_path == tmp_path / "from_config" / "AAPL.json"
    assert file_path.is_file()


def test_cache_error_is_a_runtime_error() -> None:
    assert issubclass(CacheError, RuntimeError)
