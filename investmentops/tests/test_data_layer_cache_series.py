"""Pruebas para el guardado y la lectura en caché local de series
históricas de estados financieros
(investmentops.data_layer.cache.save_financial_statement_series /
load_financial_statement_series).

Cubre la tarea "Extender la caché local para persistir series históricas
sin romper los datos ya guardados de Fase 1" (TASKS.md, Fase 3,
"Normalización"). No prueba de nuevo el guardado/lectura de corte único
(`save_financial_statement`/`load_financial_statement`,
`save_market_data`/`load_market_data`): eso ya está cubierto en
`test_data_layer_cache.py` y debe seguir pasando sin cambios, ya que ese
es precisamente el criterio de no-ruptura de esta extensión.
"""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from investmentops.data_layer import FinancialStatement, FinancialStatementSeries
from investmentops.data_layer.cache import (
    DEFAULT_MAX_AGE,
    CacheError,
    load_financial_statement,
    load_financial_statement_series,
    load_market_data,
    save_financial_statement,
    save_financial_statement_series,
    save_market_data,
)


def _sample_series(ticker: str = "AAPL") -> FinancialStatementSeries:
    return FinancialStatementSeries(
        ticker=ticker,
        statements=[
            FinancialStatement(
                revenue=1_000_000.0,
                net_income=150_000.0,
                debt=400_000.0,
                source="fmp",
                period_end=date(2025, 12, 31),
            ),
            FinancialStatement(
                revenue=900_000.0,
                net_income=120_000.0,
                debt=350_000.0,
                source="fmp",
                period_end=date(2024, 12, 31),
            ),
        ],
    )


def _sample_financial_statement() -> FinancialStatement:
    return FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def _sample_market_data():
    from investmentops.data_layer import MarketData

    return MarketData(
        price=185.5,
        market_cap=2_900_000_000_000.0,
        multiples={"pe": 18.4},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def _write_series_section(
    tmp_path: Path, ticker: str, data: dict, cached_at: str
) -> Path:
    """Escribe directamente un archivo de caché con un `cached_at` dado,
    para simular datos vencidos o corruptos sin depender del reloj real."""
    file_path = tmp_path / f"{ticker}.json"
    payload = {"financial_statement_series": {**data, "cached_at": cached_at}}
    file_path.write_text(json.dumps(payload))
    return file_path


# --- save_financial_statement_series ----------------------------------------


def test_save_writes_ticker_file(tmp_path: Path) -> None:
    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), cache_path=tmp_path
    )

    assert file_path == tmp_path / "AAPL.json"
    with file_path.open() as f:
        data = json.load(f)

    section = data["financial_statement_series"]
    assert len(section["statements"]) == 2
    assert "cached_at" in section


def test_save_serializes_each_statement_with_expected_fields(tmp_path: Path) -> None:
    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    first = data["financial_statement_series"]["statements"][0]
    assert first["revenue"] == 1_000_000.0
    assert first["net_income"] == 150_000.0
    assert first["debt"] == 400_000.0
    assert first["source"] == "fmp"
    assert first["period_end"] == "2025-12-31"


def test_save_preserves_order_of_statements(tmp_path: Path) -> None:
    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    periods = [s["period_end"] for s in data["financial_statement_series"]["statements"]]
    assert periods == ["2025-12-31", "2024-12-31"]


def test_save_normalizes_ticker_to_uppercase_filename(tmp_path: Path) -> None:
    file_path = save_financial_statement_series(
        "aapl", _sample_series(), cache_path=tmp_path
    )

    assert file_path == tmp_path / "AAPL.json"


def test_save_does_not_overwrite_existing_financial_statement_section(
    tmp_path: Path,
) -> None:
    """Guardar la serie no debe borrar un financial_statement (corte único)
    ya cacheado para el mismo ticker."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)
    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "financial_statement_series" in data


def test_save_does_not_overwrite_existing_market_data_section(tmp_path: Path) -> None:
    save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)
    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    assert "market_data" in data
    assert "financial_statement_series" in data


def test_save_does_not_overwrite_other_sections_when_they_are_saved_afterwards(
    tmp_path: Path,
) -> None:
    """El orden inverso también debe funcionar: guardar corte único después
    de la serie no debe borrarla."""
    save_financial_statement_series("AAPL", _sample_series(), cache_path=tmp_path)
    file_path = save_financial_statement(
        "AAPL", _sample_financial_statement(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "financial_statement_series" in data


def test_save_overwrites_only_the_series_section_on_repeated_save(
    tmp_path: Path,
) -> None:
    save_financial_statement_series("AAPL", _sample_series(), cache_path=tmp_path)

    newer_series = FinancialStatementSeries(
        ticker="AAPL",
        statements=[
            FinancialStatement(
                revenue=2_000_000.0,
                net_income=300_000.0,
                debt=500_000.0,
                source="fmp",
                period_end=date(2026, 3, 31),
            )
        ],
    )
    file_path = save_financial_statement_series(
        "AAPL", newer_series, cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    statements = data["financial_statement_series"]["statements"]
    assert len(statements) == 1
    assert statements[0]["revenue"] == 2_000_000.0


def test_save_creates_cache_directory_if_missing(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"

    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), cache_path=cache_dir
    )

    assert file_path.parent == cache_dir
    assert file_path.is_file()


def test_save_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        save_financial_statement_series("   ", _sample_series(), cache_path=tmp_path)


def test_save_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}

    file_path = save_financial_statement_series(
        "AAPL", _sample_series(), config=config
    )

    assert file_path == tmp_path / "from_config" / "AAPL.json"
    assert file_path.is_file()


# --- load_financial_statement_series ----------------------------------------


def test_load_returns_none_when_ticker_not_cached(tmp_path: Path) -> None:
    assert load_financial_statement_series("AAPL", cache_path=tmp_path) is None


def test_load_returns_none_when_section_missing(tmp_path: Path) -> None:
    """El archivo existe (tiene financial_statement), pero no la serie."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)

    assert load_financial_statement_series("AAPL", cache_path=tmp_path) is None


def test_load_returns_series_when_fresh(tmp_path: Path) -> None:
    save_financial_statement_series("AAPL", _sample_series(), cache_path=tmp_path)

    result = load_financial_statement_series("AAPL", cache_path=tmp_path)

    assert result == _sample_series()


def test_load_is_case_insensitive_on_ticker(tmp_path: Path) -> None:
    save_financial_statement_series("AAPL", _sample_series(), cache_path=tmp_path)

    result = load_financial_statement_series("aapl", cache_path=tmp_path)

    assert result == _sample_series()


def test_load_preserves_order_of_statements(tmp_path: Path) -> None:
    save_financial_statement_series("AAPL", _sample_series(), cache_path=tmp_path)

    result = load_financial_statement_series("AAPL", cache_path=tmp_path)

    assert [s.period_end for s in result.statements] == [
        date(2025, 12, 31),
        date(2024, 12, 31),
    ]


def test_load_returns_none_when_stale(tmp_path: Path) -> None:
    stale_cached_at = (
        datetime.now(timezone.utc) - DEFAULT_MAX_AGE - timedelta(hours=1)
    ).isoformat()
    _write_series_section(
        tmp_path,
        "AAPL",
        {
            "statements": [
                {
                    "revenue": 1_000_000.0,
                    "net_income": 150_000.0,
                    "debt": 400_000.0,
                    "source": "fmp",
                    "period_end": "2025-12-31",
                }
            ]
        },
        stale_cached_at,
    )

    assert load_financial_statement_series("AAPL", cache_path=tmp_path) is None


def test_load_respects_custom_max_age(tmp_path: Path) -> None:
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_series_section(
        tmp_path,
        "AAPL",
        {
            "statements": [
                {
                    "revenue": 1_000_000.0,
                    "net_income": 150_000.0,
                    "debt": 400_000.0,
                    "source": "fmp",
                    "period_end": "2025-12-31",
                }
            ]
        },
        two_hours_ago,
    )

    assert (
        load_financial_statement_series(
            "AAPL", cache_path=tmp_path, max_age=timedelta(hours=1)
        )
        is None
    )
    assert (
        load_financial_statement_series(
            "AAPL", cache_path=tmp_path, max_age=timedelta(days=1)
        )
        is not None
    )


def test_load_raises_when_cached_at_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "AAPL.json"
    file_path.write_text(
        json.dumps(
            {
                "financial_statement_series": {
                    "statements": [
                        {
                            "revenue": 1_000_000.0,
                            "net_income": 150_000.0,
                            "debt": 400_000.0,
                            "source": "fmp",
                            "period_end": "2025-12-31",
                        }
                    ]
                }
            }
        )
    )

    with pytest.raises(CacheError, match="cached_at"):
        load_financial_statement_series("AAPL", cache_path=tmp_path)


def test_load_raises_when_cached_at_invalid(tmp_path: Path) -> None:
    _write_series_section(
        tmp_path,
        "AAPL",
        {
            "statements": [
                {
                    "revenue": 1_000_000.0,
                    "net_income": 150_000.0,
                    "debt": 400_000.0,
                    "source": "fmp",
                    "period_end": "2025-12-31",
                }
            ]
        },
        "no-es-una-fecha",
    )

    with pytest.raises(CacheError, match="formato no reconocible"):
        load_financial_statement_series("AAPL", cache_path=tmp_path)


def test_load_raises_when_a_statement_is_missing_fields(tmp_path: Path) -> None:
    _write_series_section(
        tmp_path,
        "AAPL",
        {"statements": [{"revenue": 1_000_000.0}]},  # faltan varios campos
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_financial_statement_series("AAPL", cache_path=tmp_path)


def test_load_raises_when_a_statement_has_invalid_date(tmp_path: Path) -> None:
    _write_series_section(
        tmp_path,
        "AAPL",
        {
            "statements": [
                {
                    "revenue": 1_000_000.0,
                    "net_income": 150_000.0,
                    "debt": 400_000.0,
                    "source": "fmp",
                    "period_end": "not-a-date",
                }
            ]
        },
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_financial_statement_series("AAPL", cache_path=tmp_path)


def test_load_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        load_financial_statement_series("   ", cache_path=tmp_path)


def test_load_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}
    save_financial_statement_series("AAPL", _sample_series(), config=config)

    result = load_financial_statement_series("AAPL", config=config)

    assert result == _sample_series()


def test_load_roundtrips_alongside_existing_single_cut_sections(tmp_path: Path) -> None:
    """Guardar y leer la serie no debe afectar el roundtrip ya existente
    de financial_statement/market_data (Fase 1), ni viceversa."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)
    save_market_data("AAPL", _sample_market_data(), cache_path=tmp_path)
    save_financial_statement_series("AAPL", _sample_series(), cache_path=tmp_path)

    statement = load_financial_statement("AAPL", cache_path=tmp_path)
    market_data = load_market_data("AAPL", cache_path=tmp_path)
    series = load_financial_statement_series("AAPL", cache_path=tmp_path)

    assert statement == _sample_financial_statement()
    assert market_data == _sample_market_data()
    assert series == _sample_series()
