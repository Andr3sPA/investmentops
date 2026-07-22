# investmentops/data_layer/cache.py
"""Guardado y lectura en caché local de datos normalizados (Data Layer).

Cubre las tareas (TASKS.md, Fase 1, "Normalización y almacenamiento"):

- "Implementar el guardado de los datos normalizados en la caché tras
  cada consulta."
- "Implementar la lectura desde caché para evitar una nueva llamada al
  proveedor si el dato ya existe y es reciente."

TASKS.md, Fase 3, "Normalización":

- "Extender la caché local para persistir series históricas sin romper
  los datos ya guardados de Fase 1."

TASKS.md, Fase 4, "Normalización":

- "Implementar el guardado de noticias normalizadas en la caché local
  tras cada consulta."

Y, desde esta tarea, TASKS.md, Fase 5, "Normalización":

- "Implementar el guardado de comparables normalizados en la caché
  local tras cada consulta." (ya completada, ver PROGRESS.md).
- "Implementar la lectura de comparables normalizados desde caché para
  evitar una nueva llamada al proveedor si el dato ya existe y es
  reciente." (esta tarea).

Implementa el mecanismo ya decidido y documentado en
`investmentops/data_layer/CACHE.md`: un archivo JSON por ticker, bajo la
ruta configurada en `config.local.toml` ([cache].path, ver
CONFIGURATION.md), con una clave por modelo de dominio cacheado
(``"financial_statement"``, ``"market_data"``,
``"financial_statement_series"``, ``"news"``, y ``"comparables"``) y un
campo ``cached_at`` propio de la caché (no del modelo de dominio) que
registra cuándo se escribió esa sección.

Guardar una sección nunca sobrescribe las demás secciones ya cacheadas
para el mismo ticker (ver CACHE.md, "Estructura del archivo"): el
contenido existente del archivo se lee primero y se fusiona con la nueva
sección antes de volver a escribirlo.

## Lectura y frescura

`load_financial_statement`/`load_market_data`/`load_financial_statement_series`/
`load_news`/`load_comparables` leen la sección correspondiente de
`<cache_path>/<TICKER>.json`, reconstruyen el modelo de dominio (inverso
de la serialización de `_save_section`/`save_financial_statement_series`/
`save_news`/`save_comparables`) y lo devuelven solo si su `cached_at`
sigue siendo "reciente" según `max_age`. Si la sección no existe, o
existe pero está vencida, devuelven ``None`` — quien las invoca (el
futuro orquestador/proveedor de datos) interpreta un ``None`` como "hay
que consultar al proveedor de nuevo", nunca como un error. Un archivo o
sección corrupta (`cached_at` no interpretable, campos imprescindibles
ausentes) sí se señala mediante `CacheError`, porque en ese caso el
problema no es la ausencia del dato sino la caché en un estado
inconsistente que no debe usarse en silencio.

`DEFAULT_MAX_AGE` (24 horas) es el umbral de frescura elegido para el
MVP, reutilizado tal cual por la serie histórica, por las noticias y por
los comparables: no hay hoy evidencia de que estos datos deban
considerarse "viejos" con un umbral distinto al de un corte único, y
agregar un umbral separado antes de tener ese caso de uso real iría
contra el criterio de no sobre-diseñar ya aplicado en el resto de este
módulo.

## Caché de series históricas (`save_financial_statement_series`/`load_financial_statement_series`)

Cubre la extensión ya anticipada en `CACHE.md`: *"Extenderla a series es
tarea explícita de la Fase 3... podrá representarse como una lista dentro
de la misma clave... sin romper este formato de archivo por ticker"*.

- **Clave nueva:** `"financial_statement_series"`, junto a
  `"financial_statement"` y `"market_data"` ya existentes, en el mismo
  archivo `<TICKER>.json`. Guardar una serie no toca ni sobrescribe las
  otras dos secciones (mismo comportamiento de fusión ya usado por
  `_save_section`).
- **Forma de la sección:** un objeto con dos claves: `"statements"` (la
  lista ordenada de estados financieros de la serie, del más reciente al
  más antiguo, cada uno serializado con los mismos campos que
  `FinancialStatement` — `revenue`, `net_income`, `debt`, `source`,
  `period_end` en ISO 8601 — más `"cached_at"` (metadato de la caché, no
  del modelo de dominio, mismo criterio que las demás secciones). El
  campo `ticker` de `FinancialStatementSeries` no se serializa dentro de
  la sección: el propio nombre del archivo (`<TICKER>.json`) ya lo
  identifica, igual criterio implícito ya usado por `financial_statement`/
  `market_data` (ninguna de esas dos secciones repite el ticker tampoco).
- **No se reutiliza `_save_section`/`_load_section` tal cual para el
  cuerpo de la sección:** `_save_section` usa `dataclasses.asdict` sobre
  un único dataclass plano; una serie es una lista de dataclasses
  anidados con un campo `date`, que `asdict` no serializa a texto por sí
  solo. Esta extensión construye la lista de estados serializados
  explícitamement (mismo patrón manual ya usado en
  `financial_statement_series_from_raw` para construir el modelo desde
  datos crudos), pero sí reutiliza `_resolve_cache_dir`, `_ticker_file`,
  `_read_existing` y `_load_section` (para la lectura y el chequeo de
  frescura vía `cached_at`), sin duplicar esa infraestructura.
- **Manejo de fallos:** mismo criterio que las demás secciones
  (`CacheError` ante ticker vacío, fallos de E/S, o una sección cacheada
  corrupta/incompleta — por ejemplo, un elemento de `"statements"` sin
  alguno de sus campos imprescindibles, o con una fecha no interpretable).

## Caché de noticias normalizadas (`save_news`/`load_news`)

Cubre la tarea "Implementar el guardado de noticias normalizadas en la
caché local tras cada consulta" (TASKS.md, Fase 4, "Normalización"),
sobre el modelo `News` (`investmentops.data_layer.news`) y su
transformación ya implementada (`news_from_raw`, ver
`investmentops/data_layer/normalization.py`).

- **Clave nueva:** `"news"`, junto a `"financial_statement"`,
  `"market_data"` y `"financial_statement_series"` ya existentes, en el
  mismo archivo `<TICKER>.json`. Guardar noticias no toca ni sobrescribe
  las demás secciones (misma fusión ya usada por `_save_section`/
  `save_financial_statement_series`).
- **Forma de la sección:** mismo patrón que
  `"financial_statement_series"` — un objeto con `"items"` (la lista de
  noticias, en el mismo orden recibido, cada una serializada con los
  campos de `News` — `title`, `summary`, `source`, `published_at` en ISO
  8601, `url`) más `"cached_at"`. Una lista vacía (empresa sin noticias
  recientes, ver `investmentops.data_providers.news`, "'No devuelve
  resultados' NO es un error") es una sección válida y cacheable: se
  guarda igual que una lista no vacía, para que una lectura posterior no
  vuelva a disparar la consulta al proveedor solo porque no había
  noticias.
- **No se reutiliza `_save_section`** por la misma razón que la serie
  histórica: `News` tiene un campo `datetime` que `dataclasses.asdict`
  no serializa a texto por sí solo, y es una lista de dataclasses, no un
  único dataclass plano. Se construye la lista serializada
  explícitamente, reutilizando `_resolve_cache_dir`, `_ticker_file`,
  `_read_existing` y `_load_section` sin duplicar esa infraestructura,
  mismo criterio que `save_financial_statement_series`.
- **Manejo de fallos:** mismo criterio que las demás secciones
  (`CacheError` ante ticker vacío, fallos de E/S, o una sección cacheada
  corrupta/incompleta — a algún elemento de `"items"` le falta un campo
  imprescindible, o `published_at` no tiene un formato interpretable).

## Caché de comparables normalizados (`save_comparables`/`load_comparables`)

Cubre las tareas "Implementar el guardado de comparables normalizados en
la caché local tras cada consulta" (ya completada) e "Implementar la
lectura de comparables normalizados desde caché para evitar una nueva
llamada al proveedor si el dato ya existe y es reciente" (esta tarea),
ambas de TASKS.md, Fase 5, "Normalización", sobre el modelo
`Comparables`/`PeerComparable` (`investmentops.data_layer.comparables`) y
su transformación ya implementada (`comparables_from_raw`, ver
`investmentops/data_layer/normalization.py`).

- **Clave:** `"comparables"`, junto a `"financial_statement"`,
  `"market_data"`, `"financial_statement_series"` y `"news"` ya
  existentes, en el mismo archivo `<TICKER>.json`.
- **Forma de la sección:** un objeto con `"peers"` (la lista de empresas
  pares, en el mismo orden recibido en `Comparables.peers`) más
  `"cached_at"`. Cada elemento de `"peers"` serializa explícitamente un
  `PeerComparable`: `"ticker"`, `"financial_statement"` (mismos campos
  que la sección `"financial_statement"` ya existente: `revenue`,
  `net_income`, `debt`, `source`, `period_end` en ISO 8601) y
  `"market_data"` (mismos campos que la sección `"market_data"` ya
  existente: `price`, `market_cap`, `multiples`, `source`, `as_of` en
  ISO 8601). El campo `ticker` de `Comparables` (la empresa investigada,
  no un par) no se serializa dentro de la sección: el propio nombre del
  archivo (`<TICKER>.json`) ya lo identifica, mismo criterio ya aplicado
  por `"financial_statement_series"`. Una lista de pares vacía (empresa
  sin comparables según el proveedor, ver `FMPComparablesProvider.fetch`,
  "Una lista vacía es una respuesta válida") es una sección válida y
  cacheable, mismo criterio ya aplicado a `save_news` con `items=[]`.
- **`load_comparables` (esta tarea):** reconstruye `Comparables`
  (`ticker` normalizado a mayúsculas, mismo criterio que
  `load_financial_statement_series`) y un `PeerComparable` por cada
  elemento de `"peers"`, con su propio `FinancialStatement`/`MarketData`
  reconstruidos igual que las secciones `"financial_statement"`/
  `"market_data"` ya existentes. Devuelve ``None`` si no hay nada
  cacheado o si venció según `max_age`; levanta `CacheError` si falta
  `cached_at`, si no es interpretable, o si algún par tiene campos
  faltantes o fechas no interpretables — mismo criterio que las demás
  secciones. Una lista de pares vacía cacheada se reconstruye como
  `Comparables(peers=[])`, no como ``None`` (mismo criterio que
  `load_news` con `items=[]`: "se consultó y no había pares" es distinto
  de "no hay nada cacheado").
- **No se reutiliza `_save_section`/una reconstrucción genérica**, misma
  razón ya documentada para la serie histórica y las noticias:
  `Comparables` es una lista de dataclasses anidados
  (`PeerComparable`, que a su vez anida `FinancialStatement`/
  `MarketData`, ambos con campos `date`). Se reutilizan
  `_resolve_cache_dir`, `_ticker_file`, `_read_existing` y `_load_section`
  sin duplicar esa infraestructura, mismo criterio que
  `save_financial_statement_series`/`save_news`.
- **Manejo de fallos:** mismo criterio que las demás secciones
  (`CacheError` ante ticker vacío, fallos de E/S, o una sección cacheada
  corrupta/incompleta).

Fuera de alcance de este módulo:
- Decidir qué hace el orquestador/proveedor cuando `load_*` devuelve
  ``None`` (es decir, disparar la llamada real al proveedor de datos):
  eso es responsabilidad de quien invoque estas funciones, no de este
  módulo.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from investmentops.config import load_config
from investmentops.data_layer.comparables import Comparables, PeerComparable
from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.news import News

#: Valor por defecto si no se indica una ruta de caché ni se puede leer
#: `config.local.toml` (mismo valor documentado como ejemplo en
#: `config.example.toml`, sección `[cache]`).
DEFAULT_CACHE_PATH = ".investmentops_cache/"

#: Umbral por defecto de frescura para la lectura desde caché: una
#: sección cacheada se considera "reciente" si su `cached_at` tiene menos
#: de este tiempo transcurrido (ver CACHE.md, "Qué determina 'reciente'",
#: decisión tomada como parte de esta tarea). Reutilizado tal cual por la
#: caché de series históricas, de noticias y de comparables (ver
#: docstring del módulo).
DEFAULT_MAX_AGE = timedelta(hours=24)

#: Nombre de la sección usada para la serie histórica de estados
#: financieros dentro de `<TICKER>.json`, junto a `"financial_statement"`
#: y `"market_data"` ya existentes.
_FINANCIAL_STATEMENT_SERIES_SECTION = "financial_statement_series"

#: Nombre de la sección usada para las noticias normalizadas dentro de
#: `<TICKER>.json`, junto a las tres secciones ya existentes.
_NEWS_SECTION = "news"

#: Nombre de la sección usada para los comparables normalizados dentro
#: de `<TICKER>.json`, junto a las cuatro secciones ya existentes.
_COMPARABLES_SECTION = "comparables"


class CacheError(RuntimeError):
    """Error al persistir o leer datos normalizados en la caché local.

    Cubre fallos de E/S al escribir/leer la caché (ej. no se puede crear
    el directorio configurado, no se puede escribir o leer el archivo
    `<TICKER>.json`), el caso de un ticker vacío (para el que no existe
    un nombre de archivo válido), y el caso de una sección cacheada cuyo
    contenido está corrupto o incompleto para reconstruir el modelo de
    dominio correspondiente (ej. falta `cached_at`, tiene un formato de
    fecha no reconocible, o le faltan campos imprescindibles). No cubre
    el caso de "dato no cacheado" ni "dato cacheado mas vencido": esos
    casos son válidos y se señalan devolviendo ``None`` desde `load_*`,
    no levantando esta excepción.
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


def load_financial_statement(
    ticker: str,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> FinancialStatement | None:
    """Lee un `FinancialStatement` desde la caché local, si existe y es reciente.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a buscar en caché (ej. ``"AAPL"``).
        Se normaliza a mayúsculas, igual criterio que `save_*`.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas.
    max_age:
        Antigüedad máxima aceptada desde `cached_at` para considerar el
        dato "reciente". Por defecto, `DEFAULT_MAX_AGE` (24 horas).

    Returns
    -------
    FinancialStatement | None
        El `FinancialStatement` reconstruido si hay una sección cacheada
        y no ha vencido según `max_age`; ``None`` si no hay nada
        cacheado para este ticker o si el dato cacheado ya es demasiado
        viejo (en ambos casos, quien invoca esta función debe consultar
        de nuevo al proveedor de datos).

    Raises
    ------
    CacheError
        Si el ticker está vacío, si ocurre un fallo de E/S al leer el
        archivo, o si la sección cacheada existe pero está corrupta o
        incompleta (falta `cached_at`, tiene un formato no reconocible,
        o faltan campos imprescindibles del modelo).
    """
    section = _load_section(
        ticker,
        "financial_statement",
        cache_path=cache_path,
        config=config,
        max_age=max_age,
    )
    if section is None:
        return None

    try:
        return FinancialStatement(
            revenue=float(section["revenue"]),
            net_income=float(section["net_income"]),
            debt=float(section["debt"]),
            source=section["source"],
            period_end=date.fromisoformat(section["period_end"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CacheError(
            f"La sección 'financial_statement' cacheada para '{ticker}' "
            f"está corrupta o incompleta: {exc}"
        ) from exc


def load_market_data(
    ticker: str,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> MarketData | None:
    """Lee un `MarketData` desde la caché local, si existe y es reciente.

    Misma semántica que `load_financial_statement`, pero para la sección
    ``"market_data"`` del archivo `<TICKER>.json`.
    """
    section = _load_section(
        ticker,
        "market_data",
        cache_path=cache_path,
        config=config,
        max_age=max_age,
    )
    if section is None:
        return None

    try:
        return MarketData(
            price=float(section["price"]),
            market_cap=float(section["market_cap"]),
            multiples=dict(section.get("multiples") or {}),
            source=section["source"],
            as_of=date.fromisoformat(section["as_of"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CacheError(
            f"La sección 'market_data' cacheada para '{ticker}' está "
            f"corrupta o incompleta: {exc}"
        ) from exc


def save_financial_statement_series(
    ticker: str,
    series: FinancialStatementSeries,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Persiste un `FinancialStatementSeries` en la caché local del ticker.

    Escribe la sección ``"financial_statement_series"`` de
    `<cache_path>/<TICKER>.json` (ver "Caché de series históricas" en el
    docstring del módulo), sin afectar las secciones
    ``"financial_statement"``/``"market_data"`` ya cacheadas para el
    mismo ticker (mismo criterio de fusión ya usado por
    `save_financial_statement`/`save_market_data`).

    Parameters
    ----------
    ticker:
        Identificador de la empresa (ej. ``"AAPL"``). Se normaliza a
        mayúsculas para el nombre del archivo, mismo criterio que las
        demás funciones `save_*` de este módulo.
    series:
        El `FinancialStatementSeries` ya normalizado a persistir (ver
        `investmentops.data_layer.financial_statement_series_from_raw`).
        El orden de `series.statements` se conserva tal cual al guardar.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas sin depender de un
        `config.local.toml` real en disco.

    Returns
    -------
    Path
        La ruta del archivo `<TICKER>.json` escrito.

    Raises
    ------
    CacheError
        Si el ticker está vacío o si ocurre un fallo de E/S al escribir.
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

    statements_data = [
        {
            "revenue": statement.revenue,
            "net_income": statement.net_income,
            "debt": statement.debt,
            "source": statement.source,
            "period_end": statement.period_end.isoformat(),
        }
        for statement in series.statements
    ]
    section_data = {
        "statements": statements_data,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    existing[_FINANCIAL_STATEMENT_SERIES_SECTION] = section_data

    try:
        with file_path.open("w", encoding="utf-8") as cache_file:
            json.dump(existing, cache_file, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise CacheError(
            f"No se pudo escribir el archivo de caché '{file_path}': {exc}"
        ) from exc

    return file_path


def load_financial_statement_series(
    ticker: str,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> FinancialStatementSeries | None:
    """Lee un `FinancialStatementSeries` desde la caché local, si existe y es reciente.

    Misma semántica de frescura/ausencia que `load_financial_statement`/
    `load_market_data` (ver docstring del módulo): devuelve ``None`` si no
    hay nada cacheado para este ticker o si la sección cacheada ya superó
    `max_age`, y levanta `CacheError` solo ante una sección corrupta o un
    fallo de E/S.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a buscar en caché (ej. ``"AAPL"``).
        Se normaliza a mayúsculas, igual criterio que las demás
        funciones `load_*`.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas.
    max_age:
        Antigüedad máxima aceptada desde `cached_at` para considerar la
        serie "reciente". Por defecto, `DEFAULT_MAX_AGE` (24 horas).

    Returns
    -------
    FinancialStatementSeries | None
        La serie reconstruida (con `ticker` normalizado a mayúsculas y
        `statements` en el mismo orden en que se guardaron) si hay una
        sección cacheada y no ha vencido según `max_age`; ``None`` en
        caso contrario.

    Raises
    ------
    CacheError
        Si el ticker está vacío, si ocurre un fallo de E/S al leer el
        archivo, o si la sección cacheada existe pero está corrupta o
        incompleta (falta `cached_at`, algún elemento de `"statements"`
        no tiene un formato de fecha reconocible, o le faltan campos
        imprescindibles).
    """
    section = _load_section(
        ticker,
        _FINANCIAL_STATEMENT_SERIES_SECTION,
        cache_path=cache_path,
        config=config,
        max_age=max_age,
    )
    if section is None:
        return None

    try:
        statements = [
            FinancialStatement(
                revenue=float(item["revenue"]),
                net_income=float(item["net_income"]),
                debt=float(item["debt"]),
                source=item["source"],
                period_end=date.fromisoformat(item["period_end"]),
            )
            for item in section["statements"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise CacheError(
            f"La sección '{_FINANCIAL_STATEMENT_SERIES_SECTION}' cacheada "
            f"para '{ticker}' está corrupta o incompleta: {exc}"
        ) from exc

    return FinancialStatementSeries(
        ticker=ticker.strip().upper(), statements=statements
    )


def save_news(
    ticker: str,
    news_items: list[News],
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Persiste una lista de `News` normalizadas en la caché local del ticker.

    Escribe la sección ``"news"`` de `<cache_path>/<TICKER>.json` (ver
    "Caché de noticias normalizadas" en el docstring del módulo), sin
    afectar las demás secciones (`"financial_statement"`, `"market_data"`,
    `"financial_statement_series"`) ya cacheadas para el mismo ticker
    (mismo criterio de fusión ya usado por las demás funciones `save_*`).

    Parameters
    ----------
    ticker:
        Identificador de la empresa (ej. ``"AAPL"``). Se normaliza a
        mayúsculas para el nombre del archivo, mismo criterio que las
        demás funciones `save_*` de este módulo.
    news_items:
        La lista de `News` ya normalizadas a persistir (ver
        `investmentops.data_layer.normalization.news_from_raw`), en el
        mismo orden en que se recibieron. Una lista vacía (empresa sin
        noticias recientes) es un valor válido y se guarda igual que
        cualquier otro, para no volver a consultar al proveedor
        únicamente por no haber noticias.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas sin depender de un
        `config.local.toml` real en disco.

    Returns
    -------
    Path
        La ruta del archivo `<TICKER>.json` escrito.

    Raises
    ------
    CacheError
        Si el ticker está vacío o si ocurre un fallo de E/S al escribir.
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

    items_data = [
        {
            "title": item.title,
            "summary": item.summary,
            "source": item.source,
            "published_at": item.published_at.isoformat(),
            "url": item.url,
        }
        for item in news_items
    ]
    section_data = {
        "items": items_data,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    existing[_NEWS_SECTION] = section_data

    try:
        with file_path.open("w", encoding="utf-8") as cache_file:
            json.dump(existing, cache_file, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise CacheError(
            f"No se pudo escribir el archivo de caché '{file_path}': {exc}"
        ) from exc

    return file_path


def load_news(
    ticker: str,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> list[News] | None:
    """Lee una lista de `News` desde la caché local, si existe y es reciente.

    Misma semántica de frescura/ausencia que las demás funciones
    `load_*` de este módulo: devuelve ``None`` si no hay nada cacheado
    para este ticker o si la sección cacheada ya superó `max_age`, y
    levanta `CacheError` solo ante una sección corrupta o un fallo de
    E/S. Una lista vacía cacheada (empresa sin noticias recientes) se
    devuelve tal cual (``[]``), no como ``None``: son dos cosas
    distintas — ``[]`` significa "se consultó y no había noticias";
    ``None`` significa "no hay nada cacheado (o está vencido), hay que
    consultar de nuevo".

    Parameters
    ----------
    ticker:
        Identificador de la empresa a buscar en caché (ej. ``"AAPL"``).
        Se normaliza a mayúsculas, igual criterio que las demás
        funciones `load_*`.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas.
    max_age:
        Antigüedad máxima aceptada desde `cached_at` para considerar las
        noticias "recientes". Por defecto, `DEFAULT_MAX_AGE` (24 horas).

    Returns
    -------
    list[News] | None
        La lista de `News` reconstruida (en el mismo orden en que se
        guardaron) si hay una sección cacheada y no ha vencido según
        `max_age`; ``None`` en caso contrario.

    Raises
    ------
    CacheError
        Si el ticker está vacío, si ocurre un fallo de E/S al leer el
        archivo, o si la sección cacheada existe pero está corrupta o
        incompleta (falta `cached_at`, algún elemento de `"items"` no
        tiene un campo imprescindible, o `published_at` no tiene un
        formato reconocible).
    """
    section = _load_section(
        ticker,
        _NEWS_SECTION,
        cache_path=cache_path,
        config=config,
        max_age=max_age,
    )
    if section is None:
        return None

    try:
        news_list = [
            News(
                title=item["title"],
                summary=item["summary"],
                source=item["source"],
                published_at=datetime.fromisoformat(item["published_at"]),
                url=item["url"],
            )
            for item in section["items"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise CacheError(
            f"La sección '{_NEWS_SECTION}' cacheada para '{ticker}' está "
            f"corrupta o incompleta: {exc}"
        ) from exc

    return news_list


def save_comparables(
    ticker: str,
    comparables: Comparables,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Persiste un `Comparables` en la caché local del ticker.

    Escribe la sección ``"comparables"`` de `<cache_path>/<TICKER>.json`
    (ver "Caché de comparables normalizados" en el docstring del
    módulo), sin afectar las demás secciones (`"financial_statement"`,
    `"market_data"`, `"financial_statement_series"`, `"news"`) ya
    cacheadas para el mismo ticker (mismo criterio de fusión ya usado
    por las demás funciones `save_*` de este módulo).

    Parameters
    ----------
    ticker:
        Identificador de la empresa investigada (ej. ``"AAPL"``). Se
        normaliza a mayúsculas para el nombre del archivo, mismo
        criterio que las demás funciones `save_*` de este módulo.
    comparables:
        El `Comparables` ya normalizado a persistir (ver
        `investmentops.data_layer.normalization.comparables_from_raw`).
        El orden de `comparables.peers` se conserva tal cual al guardar.
        Una lista de pares vacía (empresa sin comparables según el
        proveedor) es un valor válido y se guarda igual que cualquier
        otro, para no volver a consultar al proveedor únicamente por no
        haber pares.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas sin depender de un
        `config.local.toml` real en disco.

    Returns
    -------
    Path
        La ruta del archivo `<TICKER>.json` escrito.

    Raises
    ------
    CacheError
        Si el ticker está vacío o si ocurre un fallo de E/S al escribir.
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

    peers_data = [
        {
            "ticker": peer.ticker,
            "financial_statement": {
                "revenue": peer.financial_statement.revenue,
                "net_income": peer.financial_statement.net_income,
                "debt": peer.financial_statement.debt,
                "source": peer.financial_statement.source,
                "period_end": peer.financial_statement.period_end.isoformat(),
            },
            "market_data": {
                "price": peer.market_data.price,
                "market_cap": peer.market_data.market_cap,
                "multiples": dict(peer.market_data.multiples),
                "source": peer.market_data.source,
                "as_of": peer.market_data.as_of.isoformat(),
            },
        }
        for peer in comparables.peers
    ]
    section_data = {
        "peers": peers_data,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    existing[_COMPARABLES_SECTION] = section_data

    try:
        with file_path.open("w", encoding="utf-8") as cache_file:
            json.dump(existing, cache_file, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise CacheError(
            f"No se pudo escribir el archivo de caché '{file_path}': {exc}"
        ) from exc

    return file_path


def load_comparables(
    ticker: str,
    *,
    cache_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> Comparables | None:
    """Lee un `Comparables` desde la caché local, si existe y es reciente.

    Misma semántica de frescura/ausencia que las demás funciones
    `load_*` de este módulo: devuelve ``None`` si no hay nada cacheado
    para este ticker o si la sección cacheada ya superó `max_age`, y
    levanta `CacheError` solo ante una sección corrupta o un fallo de
    E/S. Una lista de pares vacía cacheada (empresa sin comparables) se
    devuelve tal cual (`Comparables(peers=[])`), no como ``None``: son
    dos cosas distintas, mismo criterio ya aplicado por `load_news` con
    `items=[]`.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a buscar en caché (ej. ``"AAPL"``).
        Se normaliza a mayúsculas, igual criterio que las demás
        funciones `load_*`.
    cache_path:
        Ruta al directorio de caché. Si no se indica, se resuelve desde
        `config.local.toml` (sección `[cache]`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas.
    max_age:
        Antigüedad máxima aceptada desde `cached_at` para considerar los
        comparables "recientes". Por defecto, `DEFAULT_MAX_AGE` (24 horas).

    Returns
    -------
    Comparables | None
        El `Comparables` reconstruido (con `ticker` normalizado a
        mayúsculas y `peers` en el mismo orden en que se guardaron) si
        hay una sección cacheada y no ha vencido según `max_age`;
        ``None`` en caso contrario.

    Raises
    ------
    CacheError
        Si el ticker está vacío, si ocurre un fallo de E/S al leer el
        archivo, o si la sección cacheada existe pero está corrupta o
        incompleta (falta `cached_at`, algún elemento de `"peers"` no
        tiene un campo imprescindible, o alguna fecha no tiene un
        formato reconocible).
    """
    section = _load_section(
        ticker,
        _COMPARABLES_SECTION,
        cache_path=cache_path,
        config=config,
        max_age=max_age,
    )
    if section is None:
        return None

    try:
        peers = [
            PeerComparable(
                ticker=peer["ticker"],
                financial_statement=FinancialStatement(
                    revenue=float(peer["financial_statement"]["revenue"]),
                    net_income=float(peer["financial_statement"]["net_income"]),
                    debt=float(peer["financial_statement"]["debt"]),
                    source=peer["financial_statement"]["source"],
                    period_end=date.fromisoformat(
                        peer["financial_statement"]["period_end"]
                    ),
                ),
                market_data=MarketData(
                    price=float(peer["market_data"]["price"]),
                    market_cap=float(peer["market_data"]["market_cap"]),
                    multiples=dict(peer["market_data"].get("multiples") or {}),
                    source=peer["market_data"]["source"],
                    as_of=date.fromisoformat(peer["market_data"]["as_of"]),
                ),
            )
            for peer in section["peers"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise CacheError(
            f"La sección '{_COMPARABLES_SECTION}' cacheada para '{ticker}' "
            f"está corrupta o incompleta: {exc}"
        ) from exc

    return Comparables(ticker=ticker.strip().upper(), peers=peers)


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


def _load_section(
    ticker: str,
    section: str,
    *,
    cache_path: str | Path | None,
    config: dict[str, Any] | None,
    max_age: timedelta,
) -> dict[str, Any] | None:
    """Lee una sección de `<TICKER>.json`, si existe y no ha vencido.

    Devuelve ``None`` si el archivo no existe todavía, si existe pero no
    tiene la sección pedida, o si la tiene pero su `cached_at` ya superó
    `max_age`. Levanta `CacheError` si la sección existe pero le falta
    `cached_at` o este no tiene un formato interpretable, o ante
    cualquier fallo de E/S al leer el archivo (ver `_read_existing`).
    """
    if not ticker or not ticker.strip():
        raise CacheError("El ticker no puede estar vacío.")

    cache_dir = _resolve_cache_dir(cache_path, config)
    file_path = _ticker_file(cache_dir, ticker)

    existing = _read_existing(file_path)
    section_data = existing.get(section)
    if section_data is None:
        return None

    cached_at_raw = section_data.get("cached_at")
    if cached_at_raw is None:
        raise CacheError(
            f"La sección '{section}' cacheada para '{ticker}' no tiene "
            "un campo 'cached_at'."
        )

    try:
        cached_at = datetime.fromisoformat(cached_at_raw)
    except (TypeError, ValueError) as exc:
        raise CacheError(
            f"La sección '{section}' cacheada para '{ticker}' tiene un "
            f"'cached_at' con un formato no reconocible: {cached_at_raw!r}."
        ) from exc

    if datetime.now(timezone.utc) - cached_at > max_age:
        return None

    return section_data


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
    dato cacheado para ese ticker, o ninguna consulta previa a leerlo).
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