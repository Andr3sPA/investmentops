"""Transformación de datos crudos de un proveedor al modelo de dominio
"Estados financieros normalizados" (FinancialStatement).

Cubre la tarea "Implementar la transformación de datos crudos del
proveedor al modelo 'Estados financieros normalizados'" (TASKS.md, Fase
1, "Normalización y almacenamiento"). Traduce el `RawProviderData` que
devuelve `investmentops.data_providers.fundamentals.FMPFundamentalsProvider`
(payload con las claves ``"income_statement"``, ``"balance_sheet_statement"``
y ``"quote"``, ver ese módulo) al modelo `FinancialStatement`
(investmentops.data_layer.financial_statements), tomando el corte más
reciente disponible.

Alcance de esta tarea (Fase 1): un único corte -el más reciente, primer
elemento de la lista `income_statement` tal como lo entrega FMP-, sin
series históricas. Extender esto a series temporales es una tarea
explícita y posterior de la Fase 3 (ver TASKS.md y
investmentops/data_layer/financial_statements.py).

Fuera de alcance de este módulo:
- La transformación al modelo "Datos de mercado" (`MarketData`): tarea
  separada, siguiente en TASKS.md.
- El cacheo/persistencia de los datos normalizados: tarea separada
  posterior (ver TASKS.md, "Normalización y almacenamiento").
- Cualquier proveedor distinto de FMP: este módulo asume la forma
  concreta del `payload` que entrega `FMPFundamentalsProvider` (ver
  investmentops/data_providers/fundamentals.py). Si en el futuro se
  agrega otro proveedor de datos fundamentales, su propia transformación
  a `FinancialStatement` es una tarea aparte, sin modificar esta.
"""

from __future__ import annotations

from datetime import date

from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_providers.contracts import RawProviderData


class NormalizationError(RuntimeError):
    """Error al transformar datos crudos de un proveedor al modelo interno.

    Cubre el caso en que el `payload` crudo no trae los campos
    imprescindibles para construir el modelo normalizado (ej. falta el
    estado de resultados, no incluye la fecha de corte, o la fecha no
    tiene un formato reconocible). Se distingue de `DataProviderError`
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
