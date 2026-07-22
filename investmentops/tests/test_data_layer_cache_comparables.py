# investmentops/tests/test_data_layer_cache_comparables.py
"""Pruebas para el guardado en caché local de comparables normalizados
(investmentops.data_layer.cache.save_comparables).

Cubre la tarea "Implementar el guardado de comparables normalizados en
la caché local tras cada consulta" (TASKS.md, Fase 5, "Normalización").
No prueba de nuevo el guardado/lectura de las demás secciones
(`financial_statement`/`market_data`/`financial_statement_series`/`news`,
ya cubiertos en `test_data_layer_cache.py`/`test_data_layer_cache_series.py`/
`test_data_layer_cache_news.py`): eso debe seguir pasando sin cambios,
ya que ese es precisamente el criterio de no-ruptura de esta extensión.
No prueba la lectura de comparables desde caché (`load_comparables`):
esa es la tarea siguiente y separada de la misma sección.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from investmentops.data_layer import (
    Comparables,
    FinancialStatement,
    MarketData,
    PeerComparable,
)
from investmentops.data_layer.cache import (
    CacheError,
    save_comparables,
    save_financial_statement,
    save_news,
)


def _peer(ticker: str = "MSFT") -> PeerComparable:
    return PeerComparable(
        ticker=ticker,
        financial_statement=FinancialStatement(
            revenue=1_000_000.0,
            net_income=150_000.0,
            debt=400_000.0,
            source="fmp",
            period_end=date(2025, 12, 31),
        ),
        market_data=MarketData(
            price=300.0,
            market_cap=2_500_000_000_000.0,
            multiples={"pe": 25.0},
            source="fmp",
            as_of=date(2025, 12, 31),
        ),
    )


def _sample_comparables(ticker: str = "AAPL") -> Comparables:
    return Comparables(ticker=ticker, peers=[_peer("MSFT"), _peer("GOOGL")])


def _sample_financial_statement() -> FinancialStatement:
    return FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def test_save_writes_ticker_file(tmp_path: Path) -> None:
    file_path = save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    assert file_path == tmp_path / "AAPL.json"
    with file_path.open() as f:
        data = json.load(f)

    section = data["comparables"]
    assert len(section["peers"]) == 2
    assert "cached_at" in section


def test_save_serializes_each_peer_with_expected_fields(tmp_path: Path) -> None:
    file_path = save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    first = data["comparables"]["peers"][0]
    assert first["ticker"] == "MSFT"
    assert first["financial_statement"]["revenue"] == 1_000_000.0
    assert first["financial_statement"]["net_income"] == 150_000.0
    assert first["financial_statement"]["debt"] == 400_000.0
    assert first["financial_statement"]["source"] == "fmp"
    assert first["financial_statement"]["period_end"] == "2025-12-31"
    assert first["market_data"]["price"] == 300.0
    assert first["market_data"]["market_cap"] == 2_500_000_000_000.0
    assert first["market_data"]["multiples"] == {"pe": 25.0}
    assert first["market_data"]["source"] == "fmp"
    assert first["market_data"]["as_of"] == "2025-12-31"


def test_save_preserves_order_of_peers(tmp_path: Path) -> None:
    file_path = save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    tickers = [peer["ticker"] for peer in data["comparables"]["peers"]]
    assert tickers == ["MSFT", "GOOGL"]


def test_save_normalizes_ticker_to_uppercase_filename(tmp_path: Path) -> None:
    file_path = save_comparables("aapl", _sample_comparables(), cache_path=tmp_path)

    assert file_path == tmp_path / "AAPL.json"


def test_save_accepts_empty_peers_list_as_a_valid_value(tmp_path: Path) -> None:
    """Una empresa sin comparables según el proveedor es un valor válido
    y cacheable, mismo criterio ya aplicado a `save_news` con `[]`."""
    empty_comparables = Comparables(ticker="AAPL", peers=[])

    file_path = save_comparables("AAPL", empty_comparables, cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    assert data["comparables"]["peers"] == []


def test_save_does_not_overwrite_existing_financial_statement_section(
    tmp_path: Path,
) -> None:
    """Guardar comparables no debe borrar un financial_statement ya
    cacheado para el mismo ticker."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)
    file_path = save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "comparables" in data


def test_save_does_not_overwrite_existing_news_section(tmp_path: Path) -> None:
    save_news("AAPL", [], cache_path=tmp_path)
    file_path = save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    assert "news" in data
    assert "comparables" in data


def test_save_does_not_overwrite_other_sections_when_saved_afterwards(
    tmp_path: Path,
) -> None:
    """El orden inverso también debe funcionar: guardar un
    financial_statement después de comparables no debe borrarlo."""
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)
    file_path = save_financial_statement(
        "AAPL", _sample_financial_statement(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "comparables" in data


def test_save_overwrites_only_the_comparables_section_on_repeated_save(
    tmp_path: Path,
) -> None:
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    newer_comparables = Comparables(ticker="AAPL", peers=[_peer("META")])
    file_path = save_comparables("AAPL", newer_comparables, cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    peers = data["comparables"]["peers"]
    assert len(peers) == 1
    assert peers[0]["ticker"] == "META"


def test_save_creates_cache_directory_if_missing(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"

    file_path = save_comparables(
        "AAPL", _sample_comparables(), cache_path=cache_dir
    )

    assert file_path.parent == cache_dir
    assert file_path.is_file()


def test_save_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        save_comparables("   ", _sample_comparables(), cache_path=tmp_path)


def test_save_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}

    file_path = save_comparables("AAPL", _sample_comparables(), config=config)

    assert file_path == tmp_path / "from_config" / "AAPL.json"
    assert file_path.is_file()