"""Pruebas para el guardado y la lectura en caché local de datos
normalizados (investmentops.data_layer.cache).

Cubre las tareas "Implementar el guardado de los datos normalizados en la
caché tras cada consulta" e "Implementar la lectura desde caché para
evitar una nueva llamada al proveedor si el dato ya existe y es reciente"
(TASKS.md, Fase 1, "Normalización y almacenamiento").
"""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_layer.cache import (
    DEFAULT_MAX_AGE,
    CacheError,
    load_financial_statement,
    load_market_data,
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


def _write_section(
    tmp_path: Path, ticker: str, section: str, data: dict, cached_at: str
) -> Path:
    """Escribe directamente un archivo de caché con un `cached_at` dado.

    Útil para simular datos vencidos o corruptos sin depender del reloj
    real ni de `save_*` (que siempre escribe `cached_at` como "ahora").
    """
    file_path = tmp_path / f"{ticker}.json"
    payload = {section: {**data, "cached_at": cached_at}}
    file_path.write_text(json.dumps(payload))
    return file_path


# --- save_financial_statement / save_market_data ---------------------------


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


# --- load_financial_statement / load_market_data ----------------------------


def test_load_financial_statement_returns_none_when_ticker_not_cached(
    tmp_path: Path,
) -> None:
    assert load_financial_statement("AAPL", cache_path=tmp_path) is None


def test_load_market_data_returns_none_when_ticker_not_cached(
    tmp_path: Path,
) -> None:
    assert load_market_data("AAPL", cache_path=tmp_path) is None


def test_load_financial_statement_returns_none_when_section_missing(
    tmp_path: Path,
) -> None:
    """El archivo existe (tiene market_data), pero no financial_statement."""
    save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)

    assert load_financial_statement("AAPL", cache_path=tmp_path) is None


def test_load_financial_statement_returns_model_when_fresh(tmp_path: Path) -> None:
    save_financial_statement("AAPL", _sample_statement(), cache_path=tmp_path)

    result = load_financial_statement("AAPL", cache_path=tmp_path)

    assert result == _sample_statement()


def test_load_market_data_returns_model_when_fresh(tmp_path: Path) -> None:
    save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)

    result = load_market_data("AAPL", cache_path=tmp_path)

    assert result == _sample_market_data()


def test_load_is_case_insensitive_on_ticker(tmp_path: Path) -> None:
    save_financial_statement("AAPL", _sample_statement(), cache_path=tmp_path)

    result = load_financial_statement("aapl", cache_path=tmp_path)

    assert result == _sample_statement()


def test_load_financial_statement_returns_none_when_stale(tmp_path: Path) -> None:
    stale_cached_at = (
        datetime.now(timezone.utc) - DEFAULT_MAX_AGE - timedelta(hours=1)
    ).isoformat()
    _write_section(
        tmp_path,
        "AAPL",
        "financial_statement",
        {
            "revenue": 1_000_000.0,
            "net_income": 150_000.0,
            "debt": 400_000.0,
            "source": "fmp",
            "period_end": "2025-12-31",
        },
        stale_cached_at,
    )

    assert load_financial_statement("AAPL", cache_path=tmp_path) is None


def test_load_market_data_returns_none_when_stale(tmp_path: Path) -> None:
    stale_cached_at = (
        datetime.now(timezone.utc) - DEFAULT_MAX_AGE - timedelta(hours=1)
    ).isoformat()
    _write_section(
        tmp_path,
        "AAPL",
        "market_data",
        {
            "price": 185.5,
            "market_cap": 2_900_000_000_000.0,
            "multiples": {"pe": 18.4},
            "source": "fmp",
            "as_of": "2025-12-31",
        },
        stale_cached_at,
    )

    assert load_market_data("AAPL", cache_path=tmp_path) is None


def test_load_respects_custom_max_age(tmp_path: Path) -> None:
    """Un dato de hace 2 horas es 'reciente' con max_age=1 día pero no con 1 hora."""
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_section(
        tmp_path,
        "AAPL",
        "financial_statement",
        {
            "revenue": 1_000_000.0,
            "net_income": 150_000.0,
            "debt": 400_000.0,
            "source": "fmp",
            "period_end": "2025-12-31",
        },
        two_hours_ago,
    )

    assert (
        load_financial_statement(
            "AAPL", cache_path=tmp_path, max_age=timedelta(hours=1)
        )
        is None
    )
    assert (
        load_financial_statement(
            "AAPL", cache_path=tmp_path, max_age=timedelta(days=1)
        )
        is not None
    )


def test_load_financial_statement_raises_when_cached_at_missing(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "AAPL.json"
    file_path.write_text(
        json.dumps(
            {
                "financial_statement": {
                    "revenue": 1_000_000.0,
                    "net_income": 150_000.0,
                    "debt": 400_000.0,
                    "source": "fmp",
                    "period_end": "2025-12-31",
                }
            }
        )
    )

    with pytest.raises(CacheError, match="cached_at"):
        load_financial_statement("AAPL", cache_path=tmp_path)


def test_load_financial_statement_raises_when_cached_at_invalid(
    tmp_path: Path,
) -> None:
    _write_section(
        tmp_path,
        "AAPL",
        "financial_statement",
        {
            "revenue": 1_000_000.0,
            "net_income": 150_000.0,
            "debt": 400_000.0,
            "source": "fmp",
            "period_end": "2025-12-31",
        },
        "no-es-una-fecha",
    )

    with pytest.raises(CacheError, match="formato no reconocible"):
        load_financial_statement("AAPL", cache_path=tmp_path)


def test_load_financial_statement_raises_when_fields_missing(
    tmp_path: Path,
) -> None:
    _write_section(
        tmp_path,
        "AAPL",
        "financial_statement",
        {"revenue": 1_000_000.0},  # faltan net_income, debt, source, period_end
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_financial_statement("AAPL", cache_path=tmp_path)


def test_load_market_data_raises_when_fields_missing(tmp_path: Path) -> None:
    _write_section(
        tmp_path,
        "AAPL",
        "market_data",
        {"price": 185.5},  # falta market_cap, source, as_of
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_market_data("AAPL", cache_path=tmp_path)


def test_load_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        load_financial_statement("   ", cache_path=tmp_path)


def test_load_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}
    save_financial_statement("AAPL", _sample_statement(), config=config)

    result = load_financial_statement("AAPL", config=config)

    assert result == _sample_statement()


def test_load_roundtrips_after_save_preserving_all_fields(tmp_path: Path) -> None:
    """El ciclo completo save -> load debe reconstruir un modelo equivalente."""
    save_financial_statement("AAPL", _sample_statement(), cache_path=tmp_path)
    save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)

    statement = load_financial_statement("AAPL", cache_path=tmp_path)
    market_data = load_market_data("AAPL", cache_path=tmp_path)

    assert statement == _sample_statement()
    assert market_data == _sample_market_data()
