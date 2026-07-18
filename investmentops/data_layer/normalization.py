"""Transformación de datos crudos de un proveedor a los modelos de dominio
"Estados financieros normalizados" (FinancialStatement), "Datos de
mercado" (MarketData) y, desde esta tarea, "Serie de estados financieros
normalizados" (FinancialStatementSeries).

Cubre las tareas "Implementar la transformación de datos crudos del
proveedor al modelo 'Estados financieros normalizados'" e "Implementar la
transformación de datos crudos al modelo 'Datos de mercado'" (TASKS.md,
Fase 1, "Normalización y almacenamiento"), y "Implementar la
transformación de la respuesta cruda histórica al modelo de series
temporales" (TASKS.md, Fase 3, "Normalización"). Todas viven en el mismo
módulo, siguiendo la recomendación dejada en PROGRESS.md tras implementar
la primera: son responsabilidades del mismo tipo (traducir el
`RawProviderData` que entrega `investmentops.data_providers.fundamentals`
a un modelo de dominio normalizado) y fragmentarlas en módulos separados
no aporta claridad adicional.

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

Fuera de alcance de este módulo:
- El cálculo de múltiplos de valoración (P/E, P/B, etc.): responsabilidad
  del agente de análisis de valoración (ver TASKS.md, "Agente de
  análisis: valoración"), no de esta capa. `market_data_from_raw` deja
  `MarketData.multiples` vacío por esta razón.
- El cacheo/persistencia de los datos normalizados (corte único o serie):
  tareas separadas ("Normalización y almacenamiento" en Fase 1, y
  "Extender la caché local para persistir series históricas" en Fase 3).
- Series históricas de `MarketData`: `ARCHITECTURE.md`/`ROADMAP.md`
  centran la Fase 3 explícitamente en ingresos y beneficios, no en
  precio de mercado (ver también
  `investmentops/data_providers/HISTORICAL_DATA.md`).
- Cualquier proveedor distinto de FMP: este módulo asume la forma
  concreta del `payload` que entregan `FMPFundamentalsProvider.fetch` y
  `.fetch_historical` (ver investmentops/data_providers/fundamentals.py).
  Si en el futuro se agrega otro proveedor de datos, su propia
  transformación es una tarea aparte, sin modificar esta.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_providers.contracts import RawProviderData


class NormalizationError(RuntimeError):
    """Error al transformar datos crudos de un proveedor al modelo interno.

    Cubre el caso en que el `payload` crudo no trae los campos
    imprescindibles para construir el modelo normalizado correspondiente
    (ej. falta el estado de resultados, falta la cotización, no incluye
    la fecha de corte, o la fecha/timestamp no tiene un formato
    reconocible). Se distingue de `DataProviderError`
    (investmentops.data_providers.contracts) porque el fallo no ocurre al
    consultar al proveedor -esa consulta ya tuvo éxito, `RawProviderData`
    ya existe-, sino al traducir su respuesta al modelo de dominio
    interno.
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
