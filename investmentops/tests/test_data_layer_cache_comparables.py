# investmentops/tests/test_data_layer_cache_comparables.py
"""Pruebas para el guardado y la lectura en caché local de comparables
normalizados (investmentops.data_layer.cache.save_comparables /
load_comparables).

Cubre las tareas "Implementar el guardado de comparables normalizados en
la caché local tras cada consulta" (ya completada) e "Implementar la
lectura de comparables normalizados desde caché para evitar una nueva
llamada al proveedor si el dato ya existe y es reciente" (esta tarea),
ambas de TASKS.md, Fase 5, "Normalización". No prueba de nuevo el
guardado/lectura de las demás secciones (`financial_statement`/
`market_data`/`financial_statement_series`/`news`, ya cubiertos en
`test_data_layer_cache.py`/`test_data_layer_cache_series.py`/
`test_data_layer_cache_news.py`): eso debe seguir pasando sin cambios,
ya que ese es precisamente el criterio de no-ruptura de esta extensión.
"""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from investmentops.data_layer import (
    Comparables,
    FinancialStatement,
    MarketData,
    PeerComparable,
)
from investmentops.data_layer.cache import (
    DEFAULT_MAX_AGE,
    CacheError,
    load_comparables,
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


def _write_comparables_section(
    tmp_path: Path, ticker: str, data: dict, cached_at: str
) -> Path:
    """Escribe directamente un archivo de caché con un `cached_at` dado,
    para simular datos vencidos o corruptos sin depender del reloj real
    ni de `save_comparables`."""
    file_path = tmp_path / f"{ticker}.json"
    payload = {"comparables": {**data, "cached_at": cached_at}}
    file_path.write_text(json.dumps(payload))
    return file_path


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


# --- load_comparables ---------------------------------------------------------


def test_load_returns_none_when_ticker_not_cached(tmp_path: Path) -> None:
    assert load_comparables("AAPL", cache_path=tmp_path) is None


def test_load_returns_none_when_section_missing(tmp_path: Path) -> None:
    """El archivo existe (tiene financial_statement), pero no comparables."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)

    assert load_comparables("AAPL", cache_path=tmp_path) is None


def test_load_returns_comparables_when_fresh(tmp_path: Path) -> None:
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    result = load_comparables("AAPL", cache_path=tmp_path)

    assert result == _sample_comparables()


def test_load_returns_empty_peers_not_none_when_no_peers_were_cached(
    tmp_path: Path,
) -> None:
    """Distingue "se consultó y no había pares" (`peers=[]`) de "no hay
    nada cacheado" (`None`), mismo criterio ya aplicado por `load_news`."""
    save_comparables("AAPL", Comparables(ticker="AAPL", peers=[]), cache_path=tmp_path)

    result = load_comparables("AAPL", cache_path=tmp_path)

    assert result is not None
    assert result.peers == []


def test_load_is_case_insensitive_on_ticker(tmp_path: Path) -> None:
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    result = load_comparables("aapl", cache_path=tmp_path)

    assert result == _sample_comparables()


def test_load_preserves_order_of_peers(tmp_path: Path) -> None:
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    result = load_comparables("AAPL", cache_path=tmp_path)

    assert [peer.ticker for peer in result.peers] == ["MSFT", "GOOGL"]


def test_load_reconstructs_each_peer_financial_statement_and_market_data(
    tmp_path: Path,
) -> None:
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    result = load_comparables("AAPL", cache_path=tmp_path)

    first = result.peers[0]
    assert first.financial_statement == FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )
    assert first.market_data == MarketData(
        price=300.0,
        market_cap=2_500_000_000_000.0,
        multiples={"pe": 25.0},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def test_load_returns_none_when_stale(tmp_path: Path) -> None:
    stale_cached_at = (
        datetime.now(timezone.utc) - DEFAULT_MAX_AGE - timedelta(hours=1)
    ).isoformat()
    _write_comparables_section(
        tmp_path,
        "AAPL",
        {
            "peers": [
                {
                    "ticker": "MSFT",
                    "financial_statement": {
                        "revenue": 1_000_000.0,
                        "net_income": 150_000.0,
                        "debt": 400_000.0,
                        "source": "fmp",
                        "period_end": "2025-12-31",
                    },
                    "market_data": {
                        "price": 300.0,
                        "market_cap": 2_500_000_000_000.0,
                        "multiples": {},
                        "source": "fmp",
                        "as_of": "2025-12-31",
                    },
                }
            ]
        },
        stale_cached_at,
    )

    assert load_comparables("AAPL", cache_path=tmp_path) is None


def test_load_respects_custom_max_age(tmp_path: Path) -> None:
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_comparables_section(
        tmp_path,
        "AAPL",
        {
            "peers": [
                {
                    "ticker": "MSFT",
                    "financial_statement": {
                        "revenue": 1_000_000.0,
                        "net_income": 150_000.0,
                        "debt": 400_000.0,
                        "source": "fmp",
                        "period_end": "2025-12-31",
                    },
                    "market_data": {
                        "price": 300.0,
                        "market_cap": 2_500_000_000_000.0,
                        "multiples": {},
                        "source": "fmp",
                        "as_of": "2025-12-31",
                    },
                }
            ]
        },
        two_hours_ago,
    )

    assert (
        load_comparables("AAPL", cache_path=tmp_path, max_age=timedelta(hours=1))
        is None
    )
    assert (
        load_comparables("AAPL", cache_path=tmp_path, max_age=timedelta(days=1))
        is not None
    )


def test_load_raises_when_cached_at_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "AAPL.json"
    file_path.write_text(
        json.dumps(
            {
                "comparables": {
                    "peers": [
                        {
                            "ticker": "MSFT",
                            "financial_statement": {
                                "revenue": 1_000_000.0,
                                "net_income": 150_000.0,
                                "debt": 400_000.0,
                                "source": "fmp",
                                "period_end": "2025-12-31",
                            },
                            "market_data": {
                                "price": 300.0,
                                "market_cap": 2_500_000_000_000.0,
                                "multiples": {},
                                "source": "fmp",
                                "as_of": "2025-12-31",
                            },
                        }
                    ]
                }
            }
        )
    )

    with pytest.raises(CacheError, match="cached_at"):
        load_comparables("AAPL", cache_path=tmp_path)


def test_load_raises_when_cached_at_invalid(tmp_path: Path) -> None:
    _write_comparables_section(
        tmp_path,
        "AAPL",
        {
            "peers": [
                {
                    "ticker": "MSFT",
                    "financial_statement": {
                        "revenue": 1_000_000.0,
                        "net_income": 150_000.0,
                        "debt": 400_000.0,
                        "source": "fmp",
                        "period_end": "2025-12-31",
                    },
                    "market_data": {
                        "price": 300.0,
                        "market_cap": 2_500_000_000_000.0,
                        "multiples": {},
                        "source": "fmp",
                        "as_of": "2025-12-31",
                    },
                }
            ]
        },
        "no-es-una-fecha",
    )

    with pytest.raises(CacheError, match="formato no reconocible"):
        load_comparables("AAPL", cache_path=tmp_path)


def test_load_raises_when_a_peer_is_missing_fields(tmp_path: Path) -> None:
    _write_comparables_section(
        tmp_path,
        "AAPL",
        {"peers": [{"ticker": "MSFT"}]},  # faltan financial_statement/market_data
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_comparables("AAPL", cache_path=tmp_path)


def test_load_raises_when_a_peer_has_invalid_date(tmp_path: Path) -> None:
    _write_comparables_section(
        tmp_path,
        "AAPL",
        {
            "peers": [
                {
                    "ticker": "MSFT",
                    "financial_statement": {
                        "revenue": 1_000_000.0,
                        "net_income": 150_000.0,
                        "debt": 400_000.0,
                        "source": "fmp",
                        "period_end": "not-a-date",
                    },
                    "market_data": {
                        "price": 300.0,
                        "market_cap": 2_500_000_000_000.0,
                        "multiples": {},
                        "source": "fmp",
                        "as_of": "2025-12-31",
                    },
                }
            ]
        },
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_comparables("AAPL", cache_path=tmp_path)


def test_load_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        load_comparables("   ", cache_path=tmp_path)


def test_load_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}
    save_comparables("AAPL", _sample_comparables(), config=config)

    result = load_comparables("AAPL", config=config)

    assert result == _sample_comparables()


def test_load_roundtrips_alongside_existing_single_cut_sections(tmp_path: Path) -> None:
    """Guardar y leer comparables no debe afectar el roundtrip ya
    existente de financial_statement, ni viceversa."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)
    save_comparables("AAPL", _sample_comparables(), cache_path=tmp_path)

    statement = save_financial_statement.__wrapped__ if False else None  # no-op guard
    from investmentops.data_layer.cache import load_financial_statement

    loaded_statement = load_financial_statement("AAPL", cache_path=tmp_path)
    loaded_comparables = load_comparables("AAPL", cache_path=tmp_path)

    assert loaded_statement == _sample_financial_statement()
    assert loaded_comparables == _sample_comparables()