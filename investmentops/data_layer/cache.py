"""Guardado en caché local de datos normalizados (Data Layer).

Cubre la tarea "Implementar el guardado de los datos normalizados en la
caché tras cada consulta" (TASKS.md, Fase 1, "Normalización y
almacenamiento"). Implementa el mecanismo ya decidido y documentado en
`investmentops/data_layer/CACHE.md`: un archivo JSON por ticker, bajo la
ruta configurada en `config.local.toml` ([cache].path, ver
CONFIGURATION.md), con una clave por modelo de dominio cacheado
(``"financial_statement"``, ``"market_data"``) y un campo ``cached_at``
propio de la caché (no del modelo de dominio) que registra cuándo se
escribió esa sección.

Guardar una sección nunca sobrescribe las demás secciones ya cacheadas
para el mismo ticker (ver CACHE.md, "Estructura del archivo"): el
contenido existente del archivo se lee primero y se fusiona con la nueva
sección antes de volver a escribirlo.

Fuera de alcance de este módulo:
- La lectura desde caché y la verificación de frescura de un dato ya
  cacheado (tarea separada y posterior, ver TASKS.md, "Implementar la
  lectura desde caché...").
- Cachear series históricas (varios periodos): igual que
  `FinancialStatement`/`MarketData` hoy, este módulo solo cachea el
  corte más reciente. Extenderlo es tarea explícita de la Fase 3 (ver
  CACHE.md, "Fuera de alcance de esta tarea").
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Valor por defecto si no se indica una ruta de caché ni se puede leer
#: `config.local.toml` (mismo valor documentado como ejemplo en
#: `config.example.toml`, sección `[cache]`).
DEFAULT_CACHE_PATH = ".investmentops_cache/"


class CacheError(RuntimeError):
    """Error al persistir datos normalizados en la caché local.

    Cubre fallos de E/S al escribir la caché (ej. no se puede crear el
    directorio configurado, no se puede escribir o leer el archivo
    `<TICKER>.json`) y el caso de un ticker vacío, para el que no existe
    un nombre de archivo válido.
    """


def save_financial_statement(
    ticker: str,
    statement: FinancialStatement,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Persiste un `FinancialStatement` en la caché local del ticker.

    Parameters
    ----------
    ticker:
        Identificador de la empresa (ej. ``"AAPL"``). Se normaliza a
        mayúsculas para el nombre del archivo, igual criterio que
        `FMPFundamentalsProvider.fetch`.
    statement:
        El `FinancialStatement` ya normalizado a persistir.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas sin depender de un
        `config.local.toml` real en disco (ver `investmentops.config`).

    Returns
    -------
    Path
        La ruta del archivo `<TICKER>.json` escrito.

    Raises
    ------
    CacheError
        Si el ticker está vacío o si ocurre un fallo de E/S al escribir.
    """
    return _save_section(
        ticker,
        "financial_statement",
        statement,
        cache_path=cache_path,
        config=config,
    )


def save_market_data(
    ticker: str,
    market_data: MarketData,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Persiste un `MarketData` en la caché local del ticker.

    Misma semántica que `save_financial_statement`, pero para la sección
    ``"market_data"`` del archivo `<TICKER>.json`.
    """
    return _save_section(
        ticker,
        "market_data",
        market_data,
        cache_path=cache_path,
        config=config,
    )


def _save_section(
    ticker: str,
    section: str,
    model: Any,
    *,
    cache_path: str | Path | None,
    config: dict[str, Any] | None,
) -> Path:
    """Escribe una sección del modelo de dominio en `<TICKER>.json`.

    Lee el contenido existente del archivo (si lo hay), reemplaza solo la
    clave `section` con los datos serializados de `model` más un
    `cached_at` nuevo, y vuelve a escribir el archivo completo, sin
    afectar otras secciones ya cacheadas para el mismo ticker.
    """
    if not ticker or not ticker.strip():
        raise CacheError("El ticker no puede estar vacío.")

    cache_dir = _resolve_cache_dir(cache_path, config)

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CacheError(
            f"No se pudo crear el directorio de caché '{cache_dir}': {exc}"
        ) from exc

    file_path = _ticker_file(cache_dir, ticker)
    existing = _read_existing(file_path)

    section_data = {key: _serialize(value) for key, value in asdict(model).items()}
    section_data["cached_at"] = datetime.now(timezone.utc).isoformat()
    existing[section] = section_data

    try:
        with file_path.open("w", encoding="utf-8") as cache_file:
            json.dump(existing, cache_file, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise CacheError(
            f"No se pudo escribir el archivo de caché '{file_path}': {exc}"
        ) from exc

    return file_path


def _resolve_cache_dir(
    cache_path: str | Path | None, config: dict[str, Any] | None
) -> Path:
    """Resuelve el directorio de caché a usar.

    Prioriza `cache_path` si se indica explícitamente (útil para
    pruebas); en caso contrario, lee `[cache].path` desde la
    configuración ya cargada (`config`) o, si tampoco se indica, desde
    `investmentops.config.load_config()`. Si la configuración no define
    una ruta, cae de vuelta a `DEFAULT_CACHE_PATH`.
    """
    if cache_path is not None:
        return Path(cache_path)

    cfg = config if config is not None else load_config()
    configured_path = cfg.get("cache", {}).get("path")
    return Path(configured_path or DEFAULT_CACHE_PATH)


def _ticker_file(cache_dir: Path, ticker: str) -> Path:
    """Ruta del archivo de caché de un ticker, con el ticker normalizado."""
    return cache_dir / f"{ticker.strip().upper()}.json"


def _read_existing(file_path: Path) -> dict[str, Any]:
    """Lee el contenido actual de un archivo de caché, si ya existe.

    Devuelve un diccionario vacío si el archivo no existe todavía (primer
    dato cacheado para ese ticker).
    """
    if not file_path.is_file():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as cache_file:
            return json.load(cache_file)
    except (ValueError, OSError) as exc:
        raise CacheError(
            f"No se pudo leer el archivo de caché existente '{file_path}': {exc}"
        ) from exc


def _serialize(value: Any) -> Any:
    """Convierte valores no serializables directamente a JSON (ej. `date`)."""
    if isinstance(value, date):
        return value.isoformat()
    return value
