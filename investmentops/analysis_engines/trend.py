"""Motor de análisis: evolución de ingresos y beneficios — cálculo
determinístico de variación periodo a periodo de ingresos.

Cubre la tarea "Implementar el cálculo de variación periodo a periodo de
ingresos" (TASKS.md, Fase 3, "Motor de análisis: evolución de ingresos y
beneficios"), sobre la base de diseño ya fijada en
`investmentops/analysis_engines/TREND_METRICS.md`. No implementa todavía
la variación de beneficios (`net_income_growth`, tarea siguiente de la
misma sección), ni la detección de tendencia agregada, ni el ensamblado
del resultado estructurado del motor (`AnalysisResult`): esas son tareas
separadas y posteriores de la misma sección.

## Qué calcula (`calculate_revenue_growth`)

Para cada par de periodos **consecutivos** de
`FinancialStatementSeries.statements` (el periodo `t` y el
inmediatamente anterior `t-1`, en el mismo orden ya usado por la serie —
más reciente primero), calcula:

``revenue_growth = (revenue_t - revenue_{t-1}) / abs(revenue_{t-1})``

conforme a `TREND_METRICS.md`, "Métrica base elegida". Se usa
``abs(...)`` en el denominador para que el signo del resultado siempre
refleje si los ingresos crecieron o decrecieron en términos absolutos,
incluso cuando el periodo base es negativo.

Este cálculo es puro Python, sin invocar ningún proveedor de IA,
conforme a `ARCHITECTURE.md` ("La IA es un mecanismo central, no un
accesorio" / "El cálculo determinístico de métricas... es una entrada
para el agente, no un sustituto de su interpretación").

## Manejo de casos degenerados (ya fijados en `TREND_METRICS.md`)

- **Periodo base en cero** (``revenue_{t-1} == 0``): produciría una
  división por cero. Para ese salto concreto, `growth` se devuelve como
  ``None`` y se agrega una advertencia explícita identificando los dos
  periodos involucrados, en vez de lanzar `ZeroDivisionError` o inventar
  un valor — mismo criterio ya aplicado en
  `calculate_financial_health_metrics`/`calculate_valuation_metrics`
  para `revenue == 0`/`net_income <= 0`.
- **Serie con menos de dos periodos:** no hay ningún par consecutivo,
  por lo que no se puede calcular ninguna variación. `values` queda
  vacío y se agrega una advertencia explícita (conforme a
  `TREND_METRICS.md`, "Serie con un único periodo": "no es un error...
  pero no contiene evolución que analizar").

## Qué no hace este módulo (fuera de alcance, ver `TREND_METRICS.md`)

- No clasifica cada salto como creciente/decreciente/estable (tarea
  siguiente: "Implementar la detección simple de tendencia").
- No calcula variación de beneficios (`net_income_growth`, tarea
  separada de la misma sección).
- No valida huecos en el calendario entre periodos "consecutivos" de la
  lista (cualquier par adyacente en `statements` se trata como
  consecutivo a efectos del cálculo; detectar huecos reales es alcance
  de la tarea de ensamblado del motor, ya prevista por separado).
- No ensambla ningún `AnalysisResult` (tarea de ensamblado, posterior).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)


@dataclass(frozen=True)
class PeriodGrowth:
    """Variación relativa de una métrica entre dos periodos consecutivos.

    Estructura genérica (no acoplada a "ingresos" específicamente) para
    poder reutilizarse, sin cambios, cuando se implemente la variación de
    beneficios (`net_income_growth`, tarea siguiente de la misma sección
    de TASKS.md): ambas métricas comparten exactamente la misma forma
    (un valor de variación entre un periodo y el inmediatamente
    anterior), conforme a `TREND_METRICS.md`.

    Attributes
    ----------
    period_end:
        Fecha de corte del periodo más reciente del par (`t`).
    previous_period_end:
        Fecha de corte del periodo inmediatamente anterior del par
        (`t-1`).
    growth:
        Variación relativa (`(valor_t - valor_{t-1}) / abs(valor_{t-1})`),
        o ``None`` si no se pudo calcular porque el periodo base
        (`t-1`) es cero (ver "Manejo de casos degenerados" en el
        docstring del módulo).
    """

    period_end: date
    previous_period_end: date
    growth: float | None


@dataclass(frozen=True)
class RevenueGrowthResult:
    """Resultado de calcular la variación periodo a periodo de ingresos.

    Es el tipo de salida de `calculate_revenue_growth`, pensado para
    alimentar, en tareas posteriores de esta misma sección, la detección
    de tendencia agregada y el ensamblado del resultado estructurado del
    motor de análisis.

    Attributes
    ----------
    values:
        Una `PeriodGrowth` por cada par consecutivo de
        `FinancialStatementSeries.statements`, en el mismo orden de la
        serie (del salto más reciente al más antiguo). Vacío si la serie
        tiene menos de dos periodos.
    warnings:
        Advertencias explícitas: una por cada salto cuyo periodo base
        tenía ingresos en cero (`growth is None` para ese elemento de
        `values`), más, si la serie tiene menos de dos periodos, una
        advertencia adicional indicando que no hay variación calculable
        para esa serie. Vacío si todos los saltos se calcularon sin
        problema y la serie tiene al menos dos periodos.
    """

    values: Sequence[PeriodGrowth]
    warnings: Sequence[str]


def calculate_revenue_growth(series: FinancialStatementSeries) -> RevenueGrowthResult:
    """Calcula la variación de ingresos entre cada par de periodos consecutivos.

    Cálculo puramente determinístico (sin IA), conforme a
    `TREND_METRICS.md`: para cada índice ``i`` en
    ``series.statements[:-1]``, compara ``statements[i]`` (periodo `t`)
    con ``statements[i + 1]`` (periodo `t-1`, el inmediatamente
    anterior en el mismo orden de la serie).

    Parameters
    ----------
    series:
        La `FinancialStatementSeries` ya normalizada (ver
        `investmentops.data_layer`), con `statements` ordenados del
        periodo más reciente al más antiguo.

    Returns
    -------
    RevenueGrowthResult
        Una `PeriodGrowth` por cada par consecutivo (``growth=None`` con
        advertencia si el periodo base tiene `revenue == 0`), o un
        resultado vacío con una advertencia explícita si la serie tiene
        menos de dos periodos.
    """
    statements = series.statements

    if len(statements) < 2:
        return RevenueGrowthResult(
            values=(),
            warnings=(
                "No se pudo calcular ninguna variación de ingresos: la "
                "serie tiene menos de dos periodos disponibles.",
            ),
        )

    values: list[PeriodGrowth] = []
    warnings: list[str] = []

    for current, previous in zip(statements, statements[1:]):
        if previous.revenue == 0:
            values.append(
                PeriodGrowth(
                    period_end=current.period_end,
                    previous_period_end=previous.period_end,
                    growth=None,
                )
            )
            warnings.append(
                "No se pudo calcular la variación de ingresos entre "
                f"{previous.period_end.isoformat()} y "
                f"{current.period_end.isoformat()}: los ingresos del "
                "periodo base (revenue) son 0, lo que produciría una "
                "división por cero."
            )
            continue

        growth = (current.revenue - previous.revenue) / abs(previous.revenue)
        values.append(
            PeriodGrowth(
                period_end=current.period_end,
                previous_period_end=previous.period_end,
                growth=growth,
            )
        )

    return RevenueGrowthResult(values=tuple(values), warnings=tuple(warnings))
