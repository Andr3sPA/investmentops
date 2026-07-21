# investmentops/tests/test_data_layer_cache_news.py
"""Pruebas para el guardado y la lectura en caché local de noticias
normalizadas (investmentops.data_layer.cache.save_news / load_news).

Cubre la tarea "Implementar el guardado de noticias normalizadas en la
caché local tras cada consulta" (TASKS.md, Fase 4, "Normalización"). No
prueba de nuevo el guardado/lectura de las demás secciones
(`financial_statement`/`market_data`/`financial_statement_series`,
ya cubiertos en `test_data_layer_cache.py`/`test_data_layer_cache_series.py`):
eso debe seguir pasando sin cambios, ya que ese es precisamente el
criterio de no-ruptura de esta extensión. Tampoco prueba la lectura de
noticias desde caché para decidir si hace falta una nueva consulta al
proveedor: esa decisión es responsabilidad de quien invoque estas
funciones (ver TASKS.md, futuro consumidor en la Fase 4).
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investmentops.data_layer import FinancialStatement, News
from investmentops.data_layer.cache import (
    DEFAULT_MAX_AGE,
    CacheError,
    load_financial_statement,
    load_news,
    save_financial_statement,
    save_news,
)


def _sample_news() -> list[News]:
    return [
        News(
            title="Apple anuncia nuevo producto",
            summary="Resumen de la noticia...",
            source="example_news_site",
            published_at=datetime(2026, 7, 15, 9, 0, 0),
            url="https://example.test/news/1",
        ),
        News(
            title="Analistas comentan resultados trimestrales",
            summary="Otro resumen...",
            source="another_site",
            published_at=datetime(2026, 7, 14, 8, 0, 0),
            url="https://example.test/news/2",
        ),
    ]


def _sample_financial_statement() -> FinancialStatement:
    from datetime import date

    return FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def _write_news_section(
    tmp_path: Path, ticker: str, data: dict, cached_at: str
) -> Path:
    """Escribe directamente un archivo de caché con un `cached_at` dado."""
    file_path = tmp_path / f"{ticker}.json"
    payload = {"news": {**data, "cached_at": cached_at}}
    file_path.write_text(json.dumps(payload))
    return file_path


# --- save_news ---------------------------------------------------------------


def test_save_writes_ticker_file(tmp_path: Path) -> None:
    file_path = save_news("AAPL", _sample_news(), cache_path=tmp_path)

    assert file_path == tmp_path / "AAPL.json"
    with file_path.open() as f:
        data = json.load(f)

    section = data["news"]
    assert len(section["items"]) == 2
    assert "cached_at" in section


def test_save_serializes_each_news_item_with_expected_fields(tmp_path: Path) -> None:
    file_path = save_news("AAPL", _sample_news(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    first = data["news"]["items"][0]
    assert first["title"] == "Apple anuncia nuevo producto"
    assert first["summary"] == "Resumen de la noticia..."
    assert first["source"] == "example_news_site"
    assert first["published_at"] == "2026-07-15T09:00:00"
    assert first["url"] == "https://example.test/news/1"


def test_save_preserves_order_of_news_items(tmp_path: Path) -> None:
    file_path = save_news("AAPL", _sample_news(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    titles = [item["title"] for item in data["news"]["items"]]
    assert titles == [
        "Apple anuncia nuevo producto",
        "Analistas comentan resultados trimestrales",
    ]


def test_save_normalizes_ticker_to_uppercase_filename(tmp_path: Path) -> None:
    file_path = save_news("aapl", _sample_news(), cache_path=tmp_path)

    assert file_path == tmp_path / "AAPL.json"


def test_save_accepts_empty_news_list_as_a_valid_value(tmp_path: Path) -> None:
    """Una empresa sin noticias recientes es un valor válido y cacheable."""
    file_path = save_news("AAPL", [], cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    assert data["news"]["items"] == []


def test_save_does_not_overwrite_existing_financial_statement_section(
    tmp_path: Path,
) -> None:
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)
    file_path = save_news("AAPL", _sample_news(), cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "news" in data


def test_save_does_not_overwrite_other_sections_when_saved_afterwards(
    tmp_path: Path,
) -> None:
    save_news("AAPL", _sample_news(), cache_path=tmp_path)
    file_path = save_financial_statement(
        "AAPL", _sample_financial_statement(), cache_path=tmp_path
    )

    with file_path.open() as f:
        data = json.load(f)

    assert "financial_statement" in data
    assert "news" in data


def test_save_overwrites_only_the_news_section_on_repeated_save(tmp_path: Path) -> None:
    save_news("AAPL", _sample_news(), cache_path=tmp_path)

    newer_news = [
        News(
            title="Noticia más reciente",
            summary="Resumen nuevo",
            source="example_news_site",
            published_at=datetime(2026, 7, 19, 12, 0, 0),
            url="https://example.test/news/3",
        )
    ]
    file_path = save_news("AAPL", newer_news, cache_path=tmp_path)

    with file_path.open() as f:
        data = json.load(f)

    items = data["news"]["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Noticia más reciente"


def test_save_creates_cache_directory_if_missing(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"

    file_path = save_news("AAPL", _sample_news(), cache_path=cache_dir)

    assert file_path.parent == cache_dir
    assert file_path.is_file()


def test_save_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        save_news("   ", _sample_news(), cache_path=tmp_path)


def test_save_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}

    file_path = save_news("AAPL", _sample_news(), config=config)

    assert file_path == tmp_path / "from_config" / "AAPL.json"
    assert file_path.is_file()


# --- load_news -----------------------------------------------------------------


def test_load_returns_none_when_ticker_not_cached(tmp_path: Path) -> None:
    assert load_news("AAPL", cache_path=tmp_path) is None


def test_load_returns_none_when_section_missing(tmp_path: Path) -> None:
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)

    assert load_news("AAPL", cache_path=tmp_path) is None


def test_load_returns_news_when_fresh(tmp_path: Path) -> None:
    save_news("AAPL", _sample_news(), cache_path=tmp_path)

    result = load_news("AAPL", cache_path=tmp_path)

    assert result == _sample_news()


def test_load_returns_empty_list_not_none_when_no_news_were_cached(
    tmp_path: Path,
) -> None:
    """Distingue "se consultó y no había noticias" (`[]`) de "no hay nada
    cacheado" (`None`)."""
    save_news("AAPL", [], cache_path=tmp_path)

    result = load_news("AAPL", cache_path=tmp_path)

    assert result == []
    assert result is not None


def test_load_is_case_insensitive_on_ticker(tmp_path: Path) -> None:
    save_news("AAPL", _sample_news(), cache_path=tmp_path)

    result = load_news("aapl", cache_path=tmp_path)

    assert result == _sample_news()


def test_load_preserves_order_of_news_items(tmp_path: Path) -> None:
    save_news("AAPL", _sample_news(), cache_path=tmp_path)

    result = load_news("AAPL", cache_path=tmp_path)

    assert [item.title for item in result] == [
        "Apple anuncia nuevo producto",
        "Analistas comentan resultados trimestrales",
    ]


def test_load_returns_none_when_stale(tmp_path: Path) -> None:
    stale_cached_at = (
        datetime.now(timezone.utc) - DEFAULT_MAX_AGE - timedelta(hours=1)
    ).isoformat()
    _write_news_section(
        tmp_path,
        "AAPL",
        {
            "items": [
                {
                    "title": "Noticia vieja",
                    "summary": "Resumen",
                    "source": "example_news_site",
                    "published_at": "2026-07-01T09:00:00",
                    "url": "https://example.test/news/old",
                }
            ]
        },
        stale_cached_at,
    )

    assert load_news("AAPL", cache_path=tmp_path) is None


def test_load_respects_custom_max_age(tmp_path: Path) -> None:
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_news_section(
        tmp_path,
        "AAPL",
        {
            "items": [
                {
                    "title": "Noticia",
                    "summary": "Resumen",
                    "source": "example_news_site",
                    "published_at": "2026-07-15T09:00:00",
                    "url": "https://example.test/news/1",
                }
            ]
        },
        two_hours_ago,
    )

    assert (
        load_news("AAPL", cache_path=tmp_path, max_age=timedelta(hours=1)) is None
    )
    assert (
        load_news("AAPL", cache_path=tmp_path, max_age=timedelta(days=1)) is not None
    )


def test_load_raises_when_cached_at_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "AAPL.json"
    file_path.write_text(
        json.dumps(
            {
                "news": {
                    "items": [
                        {
                            "title": "Noticia",
                            "summary": "Resumen",
                            "source": "example_news_site",
                            "published_at": "2026-07-15T09:00:00",
                            "url": "https://example.test/news/1",
                        }
                    ]
                }
            }
        )
    )

    with pytest.raises(CacheError, match="cached_at"):
        load_news("AAPL", cache_path=tmp_path)


def test_load_raises_when_cached_at_invalid(tmp_path: Path) -> None:
    _write_news_section(
        tmp_path,
        "AAPL",
        {
            "items": [
                {
                    "title": "Noticia",
                    "summary": "Resumen",
                    "source": "example_news_site",
                    "published_at": "2026-07-15T09:00:00",
                    "url": "https://example.test/news/1",
                }
            ]
        },
        "no-es-una-fecha",
    )

    with pytest.raises(CacheError, match="formato no reconocible"):
        load_news("AAPL", cache_path=tmp_path)


def test_load_raises_when_a_news_item_is_missing_fields(tmp_path: Path) -> None:
    _write_news_section(
        tmp_path,
        "AAPL",
        {"items": [{"title": "Noticia incompleta"}]},
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_news("AAPL", cache_path=tmp_path)


def test_load_raises_when_a_news_item_has_invalid_published_at(tmp_path: Path) -> None:
    _write_news_section(
        tmp_path,
        "AAPL",
        {
            "items": [
                {
                    "title": "Noticia",
                    "summary": "Resumen",
                    "source": "example_news_site",
                    "published_at": "not-a-date",
                    "url": "https://example.test/news/1",
                }
            ]
        },
        datetime.now(timezone.utc).isoformat(),
    )

    with pytest.raises(CacheError, match="corrupta o incompleta"):
        load_news("AAPL", cache_path=tmp_path)


def test_load_rejects_empty_ticker(tmp_path: Path) -> None:
    with pytest.raises(CacheError, match="no puede estar vacío"):
        load_news("   ", cache_path=tmp_path)


def test_load_reads_cache_path_from_config_when_not_given_explicitly(
    tmp_path: Path,
) -> None:
    config = {"cache": {"path": str(tmp_path / "from_config")}}
    save_news("AAPL", _sample_news(), config=config)

    result = load_news("AAPL", config=config)

    assert result == _sample_news()


def test_load_roundtrips_alongside_existing_single_cut_sections(tmp_path: Path) -> None:
    """Guardar y leer noticias no debe afectar el roundtrip ya existente
    de financial_statement, ni viceversa."""
    save_financial_statement("AAPL", _sample_financial_statement(), cache_path=tmp_path)
    save_news("AAPL", _sample_news(), cache_path=tmp_path)

    statement = load_financial_statement("AAPL", cache_path=tmp_path)
    news = load_news("AAPL", cache_path=tmp_path)

    assert statement == _sample_financial_statement()
    assert news == _sample_news()