"""Motor de análisis: evolución de ingresos y beneficios — cálculo de
variación periodo a periodo.

Cubre dos tareas de TASKS.md, Fase 3, "Motor de análisis: evolución de
ingresos y beneficios":

- "Implementar el cálculo de variación periodo a periodo de ingresos."
  (`calculate_revenue_growth`, ya completada, ver PROGRESS.md).
- "Implementar el cálculo de variación periodo a periodo de beneficios."
  (`calculate_net_income_growth`, esta tarea).

Ambas funciones viven sobre la definición ya fijada en
`investmentops/analysis_engines/TREND_METRICS.md`.

Implementan únicamente el cálculo determinístico de variación
(`revenue_growth`/`net_income_growth`) para cada par de periodos
consecutivos de un `FinancialStatementSeries`
(investmentops.data_layer.FinancialStatementSeries), sin invocar ningún
proveedor de IA, conforme a `ARCHITECTURE.md` ("La IA es un mecanismo
central, no un accesorio... El cálculo determinístico de métricas... es
una entrada para el agente, no un sustituto de su interpretación").

## Fórmula y manejo de casos degenerados (ver TREND_METRICS.md)

Para cada par de periodos consecutivos `t` (más reciente) y `t-1`
(inmediatamente anterior) en `series.statements` (ordenada del periodo
más reciente al más antiguo, mismo orden que ya asume
`FinancialStatementSeries`):

    revenue_growth = (revenue_t - revenue_{t-1}) / abs(revenue_{t-1})
    net_income_growth = (net_income_t - net_income_{t-1}) / abs(net_income_{t-1})

Clasificación por signo puro, sin banda de tolerancia (ver
TREND_METRICS.md, "no se inventa un umbral sin caso de uso que lo
justifique"), compartida por ambas métricas vía `_classify`:

- ``"creciente"`` si el resultado es ``> 0``
- ``"decreciente"`` si el resultado es ``< 0``
- ``"estable"`` si el resultado es ``== 0``

Casos degenerados (mismo criterio ya aplicado en
`calculate_financial_health_metrics`/`calculate_valuation_metrics`):

- Si el periodo base (`revenue_{t-1}` o `net_income_{t-1}`) es ``0``: no
  calculable para ese salto concreto; la variación y la clasificación son
  ``None`` para ese punto, con una advertencia explícita adjunta al
  propio punto, en vez de lanzar `ZeroDivisionError` o inventar un valor.
- Si la serie tiene menos de dos periodos (uno solo, o ninguno): no hay
  ningún par consecutivo del que calcular variación; se devuelve una
  lista de puntos vacía junto con una advertencia explícita a nivel de
  serie (`*GrowthResult.warnings`), en vez de fallar o inventar un punto.

Esta función no distingue huecos reales en el calendario entre periodos
(ej. un año faltante): trata cualquier par adyacente en
`series.statements` como "consecutivo" a efectos del cálculo, exactamente
como ya lo documenta `TREND_METRICS.md` ("esta definición no distingue
huecos... eso es responsabilidad de la tarea de ensamblado del motor").

`calculate_net_income_growth` reutiliza `_classify` (ya usada por
`calculate_revenue_growth`) sin duplicar la lógica de clasificación:
ambas métricas comparten exactamente el mismo criterio de signo puro.

Fuera de alcance de este módulo:
- La detección de tendencia agregada para toda la serie (si el conjunto
  de saltos es consistentemente creciente/decreciente/mixto): tarea
  separada y posterior.
- El ensamblado del resultado estructurado del motor (hallazgos,
  advertencias por huecos, invocación a un proveedor de IA si aplica):
  tarea separada y posterior en la misma sección de `TASKS.md`.
- Cualquier umbral de tolerancia, CAGR, proyecciones o suavizado
  estadístico: descartados explícitamente para el MVP (ver
  TREND_METRICS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)

#: Advertencia usada cuando la serie no tiene al menos dos periodos, por
#: lo que no existe ningún par consecutivo del que calcular variación de
#: ingresos (ver TREND_METRICS.md, "Serie con un único periodo").
SINGLE_PERIOD_WARNING = (
    "La serie tiene un único periodo (o ninguno): no hay ningún par de "
    "periodos consecutivos del que calcular variación de ingresos."
)

#: Misma advertencia que `SINGLE_PERIOD_WARNING`, pero para la variación
#: de beneficios (`calculate_net_income_growth`), mismo criterio de
#: TREND_METRICS.md aplicado a `net_income` en vez de `revenue`.
NET_INCOME_SINGLE_PERIOD_WARNING = (
    "La serie tiene un único periodo (o ninguno): no hay ningún par de "
    "periodos consecutivos del que calcular variación de beneficios."
)


@dataclass(frozen=True)
class RevenueGrowthPoint:
    """Variación de ingresos entre un periodo y el inmediatamente anterior.

    Attributes
    ----------
    period_end:
        Fecha de corte del periodo más reciente del par (``t``).
    previous_period_end:
        Fecha de corte del periodo inmediatamente anterior del par
        (``t-1``).
    revenue_growth:
        Variación relativa de ingresos
        (``(revenue_t - revenue_{t-1}) / abs(revenue_{t-1})``), o
        ``None`` si no se pudo calcular porque ``revenue_{t-1} == 0``
        (ver `warning`).
    classification:
        ``"creciente"``, ``"decreciente"`` o ``"estable"`` según el
        signo de `revenue_growth`, o ``None`` si `revenue_growth` es
        ``None``.
    warning:
        Advertencia explícita si `revenue_growth` no se pudo calcular
        para este par concreto (periodo base con ``revenue == 0``), o
        ``None`` si se calculó sin problema.
    """

    period_end: date
    previous_period_end: date
    revenue_growth: float | None
    classification: str | None
    warning: str | None


@dataclass(frozen=True)
class RevenueGrowthResult:
    """Resultado del cálculo de variación de ingresos para una serie completa.

    Attributes
    ----------
    points:
        Un `RevenueGrowthPoint` por cada par de periodos consecutivos de
        la serie, en el mismo orden que `series.statements` (del par más
        reciente al más antiguo). Vacío si la serie tiene menos de dos
        periodos.
    warnings:
        Advertencias a nivel de serie completa (ej. serie de un único
        periodo). No incluye las advertencias por punto, que ya viven en
        `RevenueGrowthPoint.warning`.
    """

    points: Sequence[RevenueGrowthPoint]
    warnings: Sequence[str]


@dataclass(frozen=True)
class NetIncomeGrowthPoint:
    """Variación de beneficios entre un periodo y el inmediatamente anterior.

    Misma forma que `RevenueGrowthPoint`, aplicada a `net_income` en vez
    de `revenue` (ver TREND_METRICS.md: ambas métricas comparten
    exactamente la misma definición y manejo de casos degenerados).

    Attributes
    ----------
    period_end:
        Fecha de corte del periodo más reciente del par (``t``).
    previous_period_end:
        Fecha de corte del periodo inmediatamente anterior del par
        (``t-1``).
    net_income_growth:
        Variación relativa de beneficios
        (``(net_income_t - net_income_{t-1}) / abs(net_income_{t-1})``),
        o ``None`` si no se pudo calcular porque
        ``net_income_{t-1} == 0`` (ver `warning`).
    classification:
        ``"creciente"``, ``"decreciente"`` o ``"estable"`` según el
        signo de `net_income_growth`, o ``None`` si `net_income_growth`
        es ``None``.
    warning:
        Advertencia explícita si `net_income_growth` no se pudo calcular
        para este par concreto (periodo base con ``net_income == 0``), o
        ``None`` si se calculó sin problema.
    """

    period_end: date
    previous_period_end: date
    net_income_growth: float | None
    classification: str | None
    warning: str | None


@dataclass(frozen=True)
class NetIncomeGrowthResult:
    """Resultado del cálculo de variación de beneficios para una serie completa.

    Misma forma que `RevenueGrowthResult`, aplicada a `net_income`.

    Attributes
    ----------
    points:
        Un `NetIncomeGrowthPoint` por cada par de periodos consecutivos
        de la serie, en el mismo orden que `series.statements` (del par
        más reciente al más antiguo). Vacío si la serie tiene menos de
        dos periodos.
    warnings:
        Advertencias a nivel de serie completa (ej. serie de un único
        periodo). No incluye las advertencias por punto, que ya viven en
        `NetIncomeGrowthPoint.warning`.
    """

    points: Sequence[NetIncomeGrowthPoint]
    warnings: Sequence[str]


def _classify(growth: float) -> str:
    """Clasifica una variación según su signo puro (ver TREND_METRICS.md).

    Compartida por `calculate_revenue_growth` y
    `calculate_net_income_growth`: ambas métricas usan exactamente el
    mismo criterio de clasificación (signo puro, sin banda de
    tolerancia).
    """
    if growth > 0:
        return "creciente"
    if growth < 0:
        return "decreciente"
    return "estable"


def calculate_revenue_growth(series: FinancialStatementSeries) -> RevenueGrowthResult:
    """Calcula la variación de ingresos periodo a periodo de una serie.

    Cálculo puramente determinístico (sin IA), conforme a
    `TREND_METRICS.md`. Recorre `series.statements` (ordenada del periodo
    más reciente al más antiguo) en pares consecutivos, calculando
    `revenue_growth` para cada uno.

    Parameters
    ----------
    series:
        La `FinancialStatementSeries` (ver
        `investmentops.data_layer.FinancialStatementSeries`) de la que se
        deriva esta variación.

    Returns
    -------
    RevenueGrowthResult
        Un punto por cada par consecutivo, más advertencias a nivel de
        serie. Si `series.statements` tiene menos de dos elementos,
        `points` es una lista vacía y `warnings` contiene
        `SINGLE_PERIOD_WARNING`, sin lanzar ninguna excepción ni inventar
        un valor.
    """
    statements = series.statements

    if len(statements) < 2:
        return RevenueGrowthResult(points=(), warnings=(SINGLE_PERIOD_WARNING,))

    points: list[RevenueGrowthPoint] = []

    for current, previous in zip(statements, statements[1:]):
        if previous.revenue == 0:
            points.append(
                RevenueGrowthPoint(
                    period_end=current.period_end,
                    previous_period_end=previous.period_end,
                    revenue_growth=None,
                    classification=None,
                    warning=(
                        "No se pudo calcular 'revenue_growth' entre "
                        f"{previous.period_end.isoformat()} y "
                        f"{current.period_end.isoformat()}: los ingresos "
                        "del periodo base son 0, lo que produciría una "
                        "división por cero."
                    ),
                )
            )
            continue

        growth = (current.revenue - previous.revenue) / abs(previous.revenue)
        points.append(
            RevenueGrowthPoint(
                period_end=current.period_end,
                previous_period_end=previous.period_end,
                revenue_growth=growth,
                classification=_classify(growth),
                warning=None,
            )
        )

    return RevenueGrowthResult(points=tuple(points), warnings=())


def calculate_net_income_growth(
    series: FinancialStatementSeries,
) -> NetIncomeGrowthResult:
    """Calcula la variación de beneficios periodo a periodo de una serie.

    Cálculo puramente determinístico (sin IA), conforme a
    `TREND_METRICS.md`. Sigue exactamente el mismo patrón ya usado por
    `calculate_revenue_growth`, aplicado a `net_income` en vez de
    `revenue`: recorre `series.statements` (ordenada del periodo más
    reciente al más antiguo) en pares consecutivos, calculando
    `net_income_growth` para cada uno.

    Parameters
    ----------
    series:
        La `FinancialStatementSeries` (ver
        `investmentops.data_layer.FinancialStatementSeries`) de la que se
        deriva esta variación.

    Returns
    -------
    NetIncomeGrowthResult
        Un punto por cada par consecutivo, más advertencias a nivel de
        serie. Si `series.statements` tiene menos de dos elementos,
        `points` es una lista vacía y `warnings` contiene
        `NET_INCOME_SINGLE_PERIOD_WARNING`, sin lanzar ninguna excepción
        ni inventar un valor. Si el periodo base de un salto concreto
        tiene `net_income == 0`, ese punto devuelve
        `net_income_growth`/`classification` en ``None`` con una
        advertencia adjunta, sin afectar a los demás pares de la serie.
    """
    statements = series.statements

    if len(statements) < 2:
        return NetIncomeGrowthResult(
            points=(), warnings=(NET_INCOME_SINGLE_PERIOD_WARNING,)
        )

    points: list[NetIncomeGrowthPoint] = []

    for current, previous in zip(statements, statements[1:]):
        if previous.net_income == 0:
            points.append(
                NetIncomeGrowthPoint(
                    period_end=current.period_end,
                    previous_period_end=previous.period_end,
                    net_income_growth=None,
                    classification=None,
                    warning=(
                        "No se pudo calcular 'net_income_growth' entre "
                        f"{previous.period_end.isoformat()} y "
                        f"{current.period_end.isoformat()}: el beneficio "
                        "neto del periodo base es 0, lo que produciría "
                        "una división por cero."
                    ),
                )
            )
            continue

        growth = (current.net_income - previous.net_income) / abs(
            previous.net_income
        )
        points.append(
            NetIncomeGrowthPoint(
                period_end=current.period_end,
                previous_period_end=previous.period_end,
                net_income_growth=growth,
                classification=_classify(growth),
                warning=None,
            )
        )

    return NetIncomeGrowthResult(points=tuple(points), warnings=())
