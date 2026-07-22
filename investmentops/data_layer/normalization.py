"""Transformación de datos crudos de un proveedor a los modelos de dominio
"Estados financieros normalizados" (FinancialStatement), "Datos de
mercado" (MarketData), "Serie de estados financieros normalizados"
(FinancialStatementSeries), "Noticias" (News) y, desde esta tarea,
"Comparables" (Comparables/PeerComparable).

Cubre las tareas "Implementar la transformación de datos crudos del
proveedor al modelo 'Estados financieros normalizados'" e "Implementar la
transformación de datos crudos al modelo 'Datos de mercado'" (TASKS.md,
Fase 1, "Normalización y almacenamiento"), "Implementar la
transformación de la respuesta cruda histórica al modelo de series
temporales" (TASKS.md, Fase 3, "Normalización"), "Implementar la
transformación de noticias crudas al modelo normalizado" (TASKS.md, Fase
4, "Normalización"), y "Implementar la transformación de los datos
crudos de comparables al modelo normalizado" (TASKS.md, Fase 5,
"Normalización"). Todas viven en el mismo módulo, siguiendo la
recomendación dejada en PROGRESS.md tras implementar la primera: son
responsabilidades del mismo tipo (traducir el `RawProviderData` que
entregan los proveedores concretos de `investmentops.data_providers` a un
modelo de dominio normalizado) y fragmentarlas en módulos separados no
aporta claridad adicional.

`financial_statement_from_raw` traduce las claves ``"income_statement"``
y ``"balance_sheet_statement"`` del payload de `FMPFundamentalsProvider.fetch`
(un único corte); `market_data_from_raw` traduce la clave ``"quote"``.
Ambas toman el corte más reciente disponible (primer elemento de la lista
correspondiente, tal como las entrega FMP), sin series históricas (eso
era alcance explícito y posterior de la Fase 3, ya cubierto por
`financial_statement_series_from_raw`, ver más abajo).

## Transformación de la serie histórica (`financial_statement_series_from_raw`)

Traduce el `RawProviderData` que entrega
`investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch_historical`
(varios periodos en `payload["income_statement"]`/
`payload["balance_sheet_statement"]`, cada punto ya con su propia
procedencia — `"source"`, `"queried_at"` — adjuntada por
`_attach_point_provenance`) a un `FinancialStatementSeries`
(`investmentops.data_layer.financial_statement_series`).

Construye un `FinancialStatement` por cada elemento de
`income_statement`, combinándolo con el elemento de
`balance_sheet_statement` que comparta la misma fecha (`"date"`) —no por
posición/índice—, ya que no hay garantía de que ambos endpoints de FMP
devuelvan sus periodos en exactamente el mismo orden o cantidad. Si para
la fecha de un periodo de `income_statement` no hay un `balance_sheet_statement`
correspondiente (o le falta `totalDebt`), se señala `NormalizationError`
identificando explícitamente qué periodo falló, en vez de omitir ese
punto en silencio o interpolar un valor.

El `source` de cada `FinancialStatement` de la serie se toma del propio
punto (`income_entry["source"]`, ya adjuntado por `fetch_historical`), no
de un valor fijo ni del `metadata.source` de nivel superior — aunque en
la práctica ambos coinciden hoy (todos los puntos de una misma consulta
comparten procedencia), tomar el valor por punto es lo correcto de cara a
un futuro proveedor que combine datos de varias fuentes en una misma
serie. Si un punto no trae `"source"` (no debería ocurrir viniendo de
`fetch_historical`, pero esta función no depende de esa garantía), se usa
`raw.metadata.source` como respaldo.

`FinancialStatementSeries.statements` conserva el mismo orden en que
llegaron los elementos de `income_statement` (del más reciente al más
antiguo, tal como ya devuelve FMP y ya asume `FinancialStatementSeries`,
ver su propio docstring): esta función no reordena ni valida huecos o
continuidad entre periodos (alcance explícito de
`financial_statement_series.py`, no de esta transformación).

## Transformación de noticias crudas (`news_from_raw`)

Traduce el `RawProviderData` que entrega
`investmentops.data_providers.news.FMPNewsProvider.fetch` (una lista
cruda de noticias, cada una ya con su propia procedencia — `"source"`,
`"queried_at"` — adjuntada por `_attach_news_provenance`) a una lista de
`News` (`investmentops.data_layer.news`).

A diferencia de `financial_statement_from_raw`/`market_data_from_raw`
(que construyen un único objeto a partir del corte más reciente),
`news_from_raw` construye **una `News` por cada elemento** del payload
crudo, conservando el mismo orden en que FMP entrega las noticias (no se
reordena ni se filtra por relevancia: eso es responsabilidad del futuro
motor de análisis de noticias, ver TASKS.md, "Motor de análisis:
noticias relevantes").

Mapeo de campos (payload crudo de FMP -> `News`):

- ``"title"`` -> `News.title`.
- ``"text"`` -> `News.summary` (el resumen/cuerpo de la noticia).
- ``"site"`` -> `News.source` (el medio que publicó la noticia, ej.
  ``"Reuters"``; **no** el proveedor de datos que la entregó, que ya vive
  en `ProviderMetadata.source`/el campo `"source"` adjuntado por
  `_attach_news_provenance` — ver el docstring de
  `investmentops.data_layer.news.News.source` para la misma distinción
  ya documentada allí).
- ``"publishedDate"`` -> `News.published_at`, interpretada como fecha y
  hora (FMP la entrega con el formato ``"YYYY-MM-DD HH:MM:SS"``, que
  `datetime.fromisoformat` ya interpreta correctamente en Python 3.11).
- ``"url"`` -> `News.url`.

Conforme a `investmentops/data_providers/news.py` ("'No devuelve
resultados' (lista vacía) NO es un error"), una lista de noticias vacía o
ausente en `raw.payload` produce una lista vacía de `News`, sin levantar
ninguna excepción: una empresa sin noticias recientes es un caso válido,
no un fallo de normalización.

`NormalizationError` se levanta únicamente si una noticia individual (no
toda la respuesta) no trae alguno de los cinco campos imprescindibles, o
si `publishedDate` no tiene un formato de fecha/hora reconocible,
identificando en el mensaje qué noticia (por posición) falló, mismo
criterio ya aplicado por `financial_statement_series_from_raw` para
identificar qué periodo concreto falla en una serie.

## Transformación de comparables (`comparables_from_raw`, esta tarea)

Traduce el `RawProviderData` que entrega
`investmentops.data_providers.comparables.FMPComparablesProvider.fetch`
(una lista con, a lo sumo, un único elemento con `"peersList"`, ver
`investmentops/data_providers/comparables.py`, "Forma del payload
crudo") a un `Comparables` (`investmentops.data_layer.comparables`).

A diferencia de las demás transformaciones de este módulo, el payload
crudo de comparables **no** trae las cifras financieras de cada empresa
par (`FinancialStatement`/`MarketData`): solo trae sus tickers. Esas
cifras ya se obtienen y normalizan reutilizando `fetch_and_normalize`
para cada par (ver `investmentops.core.orchestrator.fetch_peer_key_metrics`,
Fase 5, tarea anterior de esta misma sección). Por eso
`comparables_from_raw` recibe, además de `raw`, un segundo parámetro
`peer_data`: un mapeo `{ticker: (FinancialStatement, MarketData)}` con
las cifras ya normalizadas de cada par, obtenidas por quien invoque esta
función (típicamente el orquestador).

Esta función **no** importa nada de `investmentops.core` (en particular,
no depende de `investmentops.core.orchestrator.PeerMetrics`): hacerlo
invertiría la regla de dependencia de `ARCHITECTURE.md` (`core` depende
de `data_layer`, no al revés). `peer_data` se tipa con los mismos
modelos de dominio ya existentes (`FinancialStatement`, `MarketData`),
sin acoplarse a ningún tipo de una capa superior.

Mapeo:

- Los tickers pares se extraen de `raw.payload[0]["peersList"]` (misma
  forma ya conocida y ya usada por
  `investmentops.core.orchestrator.fetch_peer_tickers`), preservando su
  orden. `raw.payload` vacío (FMP no encontró pares) produce un
  `Comparables` con `peers=[]`, sin error — caso válido, mismo criterio
  ya aplicado por `news_from_raw` para "sin noticias".
- Por cada ticker par, se busca su entrada en `peer_data`. Si falta (el
  llamador no obtuvo/normalizó las cifras de ese par), se señala
  `NormalizationError` identificando el ticker par afectado, en vez de
  omitirlo en silencio o inventar cifras — mismo criterio ya aplicado en
  todo este módulo.
- `Comparables.ticker` se toma de `raw.ticker` (la empresa investigada,
  no un par), mismo campo que ya expone `RawProviderData`.

Fuera de alcance de este módulo:
- El cálculo de múltiplos de valoración (P/E, P/B, etc.): responsabilidad
  del agente de análisis de valoración (ver TASKS.md, "Agente de
  análisis: valoración"), no de esta capa. `market_data_from_raw` deja
  `MarketData.multiples` vacío por esta razón.
- El cacheo/persistencia de los datos normalizados (corte único, serie,
  noticias o comparables): tareas separadas ("Normalización y
  almacenamiento" en Fase 1, "Extender la caché local para persistir
  series históricas" en Fase 3, "Implementar el guardado de noticias
  normalizadas..." en Fase 4, y "Implementar el guardado de comparables
  normalizados..." en Fase 5).
- Series históricas de `MarketData`: `ARCHITECTURE.md`/`ROADMAP.md`
  centran la Fase 3 explícitamente en ingresos y beneficios, no en
  precio de mercado (ver también
  `investmentops/data_providers/HISTORICAL_DATA.md`).
- Cualquier filtrado o interpretación de relevancia de las noticias
  normalizadas: responsabilidad del futuro motor de análisis de noticias
  (ver TASKS.md, Fase 4, "Motor de análisis: noticias relevantes").
- Decidir si `investmentops.core.orchestrator.fetch_peer_key_metrics`
  pasa a construir/usar `Comparables` (en vez de, o además de,
  `PeerMetrics`): decisión de una tarea posterior, no de esta.
- Cualquier proveedor distinto de FMP: este módulo asume la forma
  concreta del `payload` que entregan `FMPFundamentalsProvider.fetch`,
  `.fetch_historical`, `FMPNewsProvider.fetch` y
  `FMPComparablesProvider.fetch` (ver
  investmentops/data_providers/fundamentals.py,
  investmentops/data_providers/news.py y
  investmentops/data_providers/comparables.py). Si en el futuro se
  agrega otro proveedor de datos, su propia transformación es una tarea
  aparte, sin modificar esta.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Mapping

from investmentops.data_layer.comparables import Comparables, PeerComparable
from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.news import News
from investmentops.data_providers.contracts import RawProviderData


class NormalizationError(RuntimeError):
    """Error al transformar datos crudos de un proveedor al modelo interno.

    Cubre el caso en que el `payload` crudo no trae los campos
    imprescindibles para construir el modelo normalizado correspondiente
    (ej. falta el estado de resultados, falta la cotización, no incluye
    la fecha de corte, a una noticia le falta el título, la fecha/
    timestamp no tiene un formato reconocible, o faltan las cifras
    normalizadas de una empresa par al construir `Comparables`). Se
    distingue de `DataProviderError` (investmentops.data_providers.contracts)
    porque el fallo no ocurre al consultar al proveedor -esa consulta ya
    tuvo éxito, `RawProviderData` ya existe-, sino al traducir su
    respuesta al modelo de dominio interno.
    """


def financial_statement_from_raw(raw: RawProviderData) -> FinancialStatement:
    """Construye un `FinancialStatement` a partir de datos crudos de FMP.

    Toma el corte más reciente disponible: el primer elemento de
    `raw.payload["income_statement"]` para ingresos y beneficio neto, y el
    primer elemento de `raw.payload["balance_sheet_statement"]` para la
    deuda total. La fecha de corte (`period_end`) se toma del campo
    ``"date"`` del estado de resultados más reciente.

    Parameters
    ----------
    raw:
        Datos crudos ya obtenidos de un proveedor (ver
        `investmentops.data_providers.contracts.RawProviderData`),
        típicamente el resultado de
        `FMPFundamentalsProvider.fetch(ticker)`.

    Returns
    -------
    FinancialStatement
        El modelo de dominio normalizado, con `source` tomado de
        `raw.metadata.source` (no de un valor fijo), para no acoplar este
        módulo a un único proveedor concreto.

    Raises
    ------
    NormalizationError
        Si falta el estado de resultados, si faltan los campos
        imprescindibles (ingresos, beneficio neto, deuda, fecha de
        corte), o si la fecha de corte no tiene un formato reconocible
        (se espera ``"YYYY-MM-DD"``, el formato que entrega FMP).
    """
    income_statement = raw.payload.get("income_statement") or []
    if not income_statement:
        raise NormalizationError(
            "No se puede construir 'Estados financieros normalizados' "
            f"para '{raw.ticker}': el payload crudo no trae "
            "'income_statement'."
        )
    latest_income = income_statement[0]

    balance_sheet = raw.payload.get("balance_sheet_statement") or []
    latest_balance = balance_sheet[0] if balance_sheet else {}

    revenue = latest_income.get("revenue")
    net_income = latest_income.get("netIncome")
    debt = latest_balance.get("totalDebt")
    period_end_raw = latest_income.get("date")

    missing = [
        field_name
        for field_name, value in (
            ("revenue", revenue),
            ("net_income", net_income),
            ("debt", debt),
            ("period_end (date)", period_end_raw),
        )
        if value is None
    ]
    if missing:
        raise NormalizationError(
            "No se puede construir 'Estados financieros normalizados' "
            f"para '{raw.ticker}': faltan campos imprescindibles en el "
            f"payload crudo: {', '.join(missing)}."
        )

    try:
        period_end = date.fromisoformat(str(period_end_raw))
    except ValueError as exc:
        raise NormalizationError(
            "No se puede construir 'Estados financieros normalizados' "
            f"para '{raw.ticker}': la fecha de corte '{period_end_raw}' "
            "no tiene un formato reconocible (se espera 'YYYY-MM-DD')."
        ) from exc

    return FinancialStatement(
        revenue=float(revenue),
        net_income=float(net_income),
        debt=float(debt),
        source=raw.metadata.source,
        period_end=period_end,
    )


def market_data_from_raw(raw: RawProviderData) -> MarketData:
    """Construye un `MarketData` a partir de datos crudos de FMP.

    Toma el corte más reciente disponible: el primer elemento de
    `raw.payload["quote"]` (ver
    `investmentops.data_providers.fundamentals.FMPFundamentalsProvider`),
    leyendo ``"price"`` y ``"marketCap"`` para precio y capitalización, y
    ``"timestamp"`` (timestamp Unix en segundos, tal como lo entrega el
    endpoint `/quote` de FMP) para la fecha de corte (`as_of`).

    `MarketData.multiples` se deja siempre vacío: el cálculo de múltiplos
    de valoración (P/E, P/B, etc.) es responsabilidad del agente de
    análisis de valoración (ver ARCHITECTURE.md, componente 5, y
    TASKS.md, "Agente de análisis: valoración"), no de esta capa de
    normalización.

    Parameters
    ----------
    raw:
        Datos crudos ya obtenidos de un proveedor (ver
        `investmentops.data_providers.contracts.RawProviderData`),
        típicamente el resultado de
        `FMPFundamentalsProvider.fetch(ticker)`.

    Returns
    -------
    MarketData
        El modelo de dominio normalizado, con `source` tomado de
        `raw.metadata.source` (no de un valor fijo) y `multiples` vacío.

    Raises
    ------
    NormalizationError
        Si falta la cotización, si faltan los campos imprescindibles
        (precio, capitalización, timestamp de cotización), o si el
        timestamp no tiene un formato reconocible (se espera un
        timestamp Unix en segundos).
    """
    quote = raw.payload.get("quote") or []
    if not quote:
        raise NormalizationError(
            "No se puede construir 'Datos de mercado' "
            f"para '{raw.ticker}': el payload crudo no trae 'quote'."
        )
    latest_quote = quote[0]

    price = latest_quote.get("price")
    market_cap = latest_quote.get("marketCap")
    timestamp_raw = latest_quote.get("timestamp")

    missing = [
        field_name
        for field_name, value in (
            ("price", price),
            ("market_cap", market_cap),
            ("as_of (timestamp)", timestamp_raw),
        )
        if value is None
    ]
    if missing:
        raise NormalizationError(
            "No se puede construir 'Datos de mercado' "
            f"para '{raw.ticker}': faltan campos imprescindibles en el "
            f"payload crudo: {', '.join(missing)}."
        )

    try:
        as_of = datetime.fromtimestamp(float(timestamp_raw), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError) as exc:
        raise NormalizationError(
            "No se puede construir 'Datos de mercado' "
            f"para '{raw.ticker}': el timestamp de cotización "
            f"'{timestamp_raw}' no tiene un formato reconocible (se "
            "espera un timestamp Unix en segundos)."
        ) from exc

    return MarketData(
        price=float(price),
        market_cap=float(market_cap),
        multiples={},
        source=raw.metadata.source,
        as_of=as_of,
    )


def financial_statement_series_from_raw(
    raw: RawProviderData,
) -> FinancialStatementSeries:
    """Construye un `FinancialStatementSeries` a partir de datos históricos de FMP.

    Traduce el `RawProviderData` que entrega
    `FMPFundamentalsProvider.fetch_historical(ticker, ...)` -varios
    periodos en `raw.payload["income_statement"]`/
    `raw.payload["balance_sheet_statement"]`, cada punto ya con su propia
    procedencia (`"source"`, `"queried_at"`)- a una serie de
    `FinancialStatement` (ver `investmentops.data_layer.FinancialStatementSeries`).

    Construye un `FinancialStatement` por cada elemento de
    `income_statement`, emparejándolo con el elemento de
    `balance_sheet_statement` que comparta la misma fecha (`"date"`), no
    por posición: no hay garantía de que ambas listas vengan alineadas
    por índice. El `source` de cada punto se toma del propio elemento
    (`"source"`, ya adjuntado por `fetch_historical`); si un punto no lo
    trae, se usa `raw.metadata.source` como respaldo.

    Parameters
    ----------
    raw:
        Datos crudos ya obtenidos de un proveedor (ver
        `investmentops.data_providers.contracts.RawProviderData`),
        típicamente el resultado de
        `FMPFundamentalsProvider.fetch_historical(ticker, ...)`.

    Returns
    -------
    FinancialStatementSeries
        La serie normalizada, con `ticker=raw.ticker` y un
        `FinancialStatement` por periodo, en el mismo orden en que
        llegaron en `income_statement` (del más reciente al más antiguo,
        sin reordenar ni validar continuidad).

    Raises
    ------
    NormalizationError
        Si `raw.payload["income_statement"]` está vacío o ausente, si a
        algún periodo le faltan campos imprescindibles (ingresos,
        beneficio neto, deuda -incluyendo no encontrar un
        `balance_sheet_statement` con la misma fecha-, fecha de corte), o
        si la fecha de algún periodo no tiene un formato reconocible (se
        espera ``"YYYY-MM-DD"``).
    """
    income_statement = raw.payload.get("income_statement") or []
    if not income_statement:
        raise NormalizationError(
            "No se puede construir 'Serie de estados financieros "
            f"normalizados' para '{raw.ticker}': el payload crudo no "
            "trae 'income_statement'."
        )

    balance_by_date: dict[str, dict] = {}
    for balance_entry in raw.payload.get("balance_sheet_statement") or []:
        entry_date = balance_entry.get("date")
        if entry_date is not None:
            balance_by_date[entry_date] = balance_entry

    statements: list[FinancialStatement] = []

    for income_entry in income_statement:
        period_end_raw = income_entry.get("date")
        revenue = income_entry.get("revenue")
        net_income = income_entry.get("netIncome")

        balance_entry = balance_by_date.get(period_end_raw) if period_end_raw is not None else None
        debt = balance_entry.get("totalDebt") if balance_entry is not None else None

        missing = [
            field_name
            for field_name, value in (
                ("revenue", revenue),
                ("net_income", net_income),
                ("debt", debt),
                ("period_end (date)", period_end_raw),
            )
            if value is None
        ]
        if missing:
            raise NormalizationError(
                "No se puede construir 'Serie de estados financieros "
                f"normalizados' para '{raw.ticker}': faltan campos "
                f"imprescindibles en el periodo con fecha "
                f"{period_end_raw!r}: {', '.join(missing)}."
            )

        try:
            period_end = date.fromisoformat(str(period_end_raw))
        except ValueError as exc:
            raise NormalizationError(
                "No se puede construir 'Serie de estados financieros "
                f"normalizados' para '{raw.ticker}': la fecha de corte "
                f"'{period_end_raw}' no tiene un formato reconocible (se "
                "espera 'YYYY-MM-DD')."
            ) from exc

        source = income_entry.get("source") or raw.metadata.source

        statements.append(
            FinancialStatement(
                revenue=float(revenue),
                net_income=float(net_income),
                debt=float(debt),
                source=source,
                period_end=period_end,
            )
        )

    return FinancialStatementSeries(ticker=raw.ticker, statements=statements)


def news_from_raw(raw: RawProviderData) -> list[News]:
    """Construye una lista de `News` a partir de datos crudos de noticias de FMP.

    Traduce el `RawProviderData` que entrega
    `investmentops.data_providers.news.FMPNewsProvider.fetch(ticker)`
    (`raw.payload` es la lista cruda de noticias, cada una ya con
    `"source"`/`"queried_at"` adjuntados por `_attach_news_provenance`) a
    una lista de `News` (ver `investmentops.data_layer.News`), una por
    cada elemento del payload, en el mismo orden en que las entrega FMP.

    A diferencia de `financial_statement_from_raw`/`market_data_from_raw`
    (que toman solo el corte más reciente), esta función normaliza
    **todas** las noticias del payload: no hay un único "dato más
    reciente" que tenga sentido aquí, ya que el futuro motor de análisis
    de noticias relevantes (ver TASKS.md, Fase 4) necesita ver el
    conjunto completo para poder filtrar/priorizar.

    Parameters
    ----------
    raw:
        Datos crudos ya obtenidos del proveedor de noticias (ver
        `investmentops.data_providers.contracts.RawProviderData`),
        típicamente el resultado de `FMPNewsProvider.fetch(ticker)`.

    Returns
    -------
    list[News]
        Una `News` por cada noticia cruda del payload, en el mismo orden
        recibido. Lista vacía si `raw.payload` está vacío o ausente: una
        empresa sin noticias recientes es una respuesta válida (ver
        `investmentops.data_providers.news`, "'No devuelve resultados'
        (lista vacía) NO es un error"), no algo que esta función deba
        señalar como fallo de normalización.

    Raises
    ------
    NormalizationError
        Si a alguna noticia cruda le faltan campos imprescindibles
        (título, resumen, medio/fuente, fecha de publicación, URL), o si
        su fecha de publicación no tiene un formato reconocible. El
        mensaje identifica la posición (índice, comenzando en 1) de la
        noticia afectada dentro del payload.
    """
    items = raw.payload or []

    news_list: list[News] = []

    for index, item in enumerate(items, start=1):
        title = item.get("title")
        summary = item.get("text")
        source = item.get("site")
        published_at_raw = item.get("publishedDate")
        url = item.get("url")

        missing = [
            field_name
            for field_name, value in (
                ("title", title),
                ("summary (text)", summary),
                ("source (site)", source),
                ("published_at (publishedDate)", published_at_raw),
                ("url", url),
            )
            if value is None
        ]
        if missing:
            raise NormalizationError(
                "No se puede construir 'Noticias' normalizadas para "
                f"'{raw.ticker}': faltan campos imprescindibles en la "
                f"noticia cruda #{index}: {', '.join(missing)}."
            )

        try:
            published_at = datetime.fromisoformat(str(published_at_raw))
        except ValueError as exc:
            raise NormalizationError(
                "No se puede construir 'Noticias' normalizadas para "
                f"'{raw.ticker}': la fecha de publicación de la noticia "
                f"#{index} ('{published_at_raw}') no tiene un formato "
                "reconocible (se espera 'YYYY-MM-DD HH:MM:SS')."
            ) from exc

        news_list.append(
            News(
                title=str(title),
                summary=str(summary),
                source=str(source),
                published_at=published_at,
                url=str(url),
            )
        )

    return news_list


def comparables_from_raw(
    raw: RawProviderData,
    peer_data: Mapping[str, tuple[FinancialStatement, MarketData]],
) -> Comparables:
    """Construye un `Comparables` a partir de datos crudos de comparables de FMP.

    Traduce el `RawProviderData` que entrega
    `investmentops.data_providers.comparables.FMPComparablesProvider.fetch(ticker)`
    (`raw.payload` es una lista con, a lo sumo, un único elemento con
    `"peersList"`) a un `Comparables`/`PeerComparable` (ver
    `investmentops.data_layer.comparables`).

    A diferencia de las demás funciones de este módulo, el payload crudo
    de comparables no trae las cifras financieras de cada empresa par:
    solo trae sus tickers. `peer_data` provee esas cifras, ya obtenidas y
    normalizadas por quien invoque esta función (típicamente
    reutilizando `investmentops.core.orchestrator.fetch_and_normalize`
    para cada ticker par, ver
    `investmentops.core.orchestrator.fetch_peer_key_metrics`). Esta
    función no depende de ningún tipo de `investmentops.core` (mantiene
    la regla de dependencia de `ARCHITECTURE.md`: `data_layer` no conoce
    `core`).

    Parameters
    ----------
    raw:
        Datos crudos ya obtenidos del proveedor de comparables (ver
        `investmentops.data_providers.contracts.RawProviderData`),
        típicamente el resultado de
        `FMPComparablesProvider.fetch(ticker)`.
    peer_data:
        Mapeo `{ticker_par: (FinancialStatement, MarketData)}` con las
        cifras ya normalizadas de cada empresa par mencionada en
        `raw.payload[0]["peersList"]`. Solo se consultan los tickers
        presentes en la lista de pares; entradas adicionales en
        `peer_data` que no aparezcan ahí se ignoran.

    Returns
    -------
    Comparables
        `ticker=raw.ticker` (la empresa investigada) y `peers` con un
        `PeerComparable` por cada ticker par, en el mismo orden en que
        aparecen en `"peersList"`. `peers` es una lista vacía si
        `raw.payload` está vacío o no trae `"peersList"` (la empresa no
        tiene pares según el proveedor, ver `FMPComparablesProvider.fetch`,
        "Una lista vacía es una respuesta válida"), sin lanzar ninguna
        excepción.

    Raises
    ------
    NormalizationError
        Si algún ticker par de `"peersList"` no tiene una entrada
        correspondiente en `peer_data` (faltan sus cifras normalizadas),
        identificando explícitamente qué ticker par falló, en vez de
        omitirlo en silencio o inventar cifras.
    """
    payload = raw.payload or []
    if not payload:
        peer_tickers: list[str] = []
    else:
        peer_tickers = [str(peer_ticker) for peer_ticker in (payload[0].get("peersList") or [])]

    peers: list[PeerComparable] = []

    for peer_ticker in peer_tickers:
        data = peer_data.get(peer_ticker)
        if data is None:
            raise NormalizationError(
                "No se puede construir 'Comparables' para "
                f"'{raw.ticker}': faltan las cifras normalizadas de la "
                f"empresa par '{peer_ticker}'."
            )

        peer_financial_statement, peer_market_data = data
        peers.append(
            PeerComparable(
                ticker=peer_ticker,
                financial_statement=peer_financial_statement,
                market_data=peer_market_data,
            )
        )

    return Comparables(ticker=raw.ticker, peers=peers)