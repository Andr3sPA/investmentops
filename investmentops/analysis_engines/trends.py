"""Motor de análisis: evolución de ingresos y beneficios — cálculo de
variación periodo a periodo, detección simple de tendencia agregada, y
ensamblado del resultado estructurado del motor.

Cubre cuatro tareas de TASKS.md, Fase 3, "Motor de análisis: evolución de
ingresos y beneficios":

- "Implementar el cálculo de variación periodo a periodo de ingresos."
  (`calculate_revenue_growth`, ya completada, ver PROGRESS.md).
- "Implementar el cálculo de variación periodo a periodo de beneficios."
  (`calculate_net_income_growth`, ya completada, ver PROGRESS.md).
- "Implementar la detección simple de tendencia (creciente, decreciente,
  estable) para cada serie." (`detect_revenue_trend`,
  `detect_net_income_trend`, ya completada, ver PROGRESS.md).
- "Ensamblar el resultado estructurado del motor (hallazgos, métricas de
  soporte, advertencias si hay huecos en la serie)."
  (`assemble_trend_analysis`, `TrendAnalysisResult`, esta tarea).

Todas viven sobre la definición ya fijada en
`investmentops/analysis_engines/TREND_METRICS.md`.

Las dos primeras funciones implementan únicamente el cálculo
determinístico de variación (`revenue_growth`/`net_income_growth`) para
cada par de periodos consecutivos de un `FinancialStatementSeries`
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
Esa detección de huecos ya se implementa en esta tarea, ver
`_detect_series_gaps` más abajo.

`calculate_net_income_growth` reutiliza `_classify` (ya usada por
`calculate_revenue_growth`) sin duplicar la lógica de clasificación:
ambas métricas comparten exactamente el mismo criterio de signo puro.

## Detección simple de tendencia agregada (`detect_revenue_trend`/`detect_net_income_trend`)

Cubre la tarea "Implementar la detección simple de tendencia (creciente,
decreciente, estable) para cada serie" (TASKS.md, Fase 3). Es una síntesis
distinta de la clasificación **por salto** ya calculada en cada
`RevenueGrowthPoint.classification`/`NetIncomeGrowthPoint.classification`
(ver TREND_METRICS.md, "Clasificación de tendencia": *"Esta clasificación
es por salto entre periodos consecutivos, no un resumen único de toda la
serie... esa síntesis... es explícitamente el alcance de la tarea
siguiente"*).

Dado el `RevenueGrowthResult`/`NetIncomeGrowthResult` ya producido por
`calculate_revenue_growth`/`calculate_net_income_growth`, estas funciones
sintetizan una única etiqueta de tendencia para **toda la serie de
saltos**:

- **``"creciente"``**: todos los saltos con clasificación calculable son
  ``"creciente"``.
- **``"decreciente"``**: todos los saltos con clasificación calculable
  son ``"decreciente"``.
- **``"estable"``**: todos los saltos con clasificación calculable son
  ``"estable"``.
- **``"mixta"``**: los saltos con clasificación calculable no son todos
  iguales entre sí (ej. algunos crecientes y otros decrecientes/
  estables).

Se usa exclusivamente el **signo puro** de cada salto (misma decisión ya
tomada en `TREND_METRICS.md` para la clasificación por salto, sin
inventar un umbral de tolerancia adicional aquí): esta síntesis no
recalcula nada, solo agrega las clasificaciones (`classification`) ya
producidas por `calculate_revenue_growth`/`calculate_net_income_growth`.

### Manejo de casos degenerados

- **Puntos sin clasificación calculable** (`classification is None`,
  producidos por un periodo base en cero, ver arriba): se **ignoran** al
  sintetizar la tendencia agregada -no cuentan como "mixta" ni rompen una
  tendencia por lo demás consistente-, ya que no aportan información
  sobre la dirección del cambio. Si el resto de los saltos de la serie sí
  son consistentes entre sí, la tendencia agregada refleja esa
  consistencia con normalidad.
- **Ningún salto con clasificación calculable** (serie vacía o de un
  solo periodo -`points == ()`-, o todos los saltos degenerados por
  periodo base en cero): no hay ninguna base para sintetizar una
  tendencia. Se devuelve `trend=None` junto con una advertencia
  explícita, en vez de inventar una etiqueta o fallar.

## Ensamblado del resultado estructurado del motor (`assemble_trend_analysis`)

Cubre la tarea "Ensamblar el resultado estructurado del motor (hallazgos,
métricas de soporte, advertencias si hay huecos en la serie)" (TASKS.md,
Fase 3). Dado un único `FinancialStatementSeries`, esta función encadena
todo lo ya construido en este módulo (`calculate_revenue_growth`,
`calculate_net_income_growth`, `detect_revenue_trend`,
`detect_net_income_trend`) y produce un `TrendAnalysisResult`:

- **`findings`**: dos hallazgos en lenguaje natural (uno para ingresos,
  uno para beneficios), generados por plantilla determinista a partir de
  `SeriesTrend.trend` (ver `_describe_trend`). No son producidos por un
  modelo de lenguaje: a diferencia de los motores de salud financiera y
  valoración (Fase 1), `TASKS.md` no define para este motor ninguna tarea
  de "escribir prompt" ni "invocar proveedor de IA" — solo pide ensamblar
  hallazgos, métricas de soporte y advertencias a partir de los cálculos
  ya deterministas de este mismo módulo. Por eso este motor no usa la
  interfaz de proveedores de IA en esta tarea.
- **`supporting_metrics`**: la tendencia agregada de cada serie
  (`revenue_trend`, `net_income_trend`) más la variación de cada periodo,
  como mapeos `{period_end (ISO 8601): variación|None}`
  (`revenue_growth_by_period`, `net_income_growth_by_period`).
- **`limitations`**: agrega, sin perder ninguna, las advertencias ya
  producidas por las piezas anteriores (advertencias de nivel de serie de
  `calculate_revenue_growth`/`calculate_net_income_growth`, advertencias
  por punto degenerado, advertencias de `detect_revenue_trend`/
  `detect_net_income_trend` cuando no hay tendencia calculable), más las
  advertencias de huecos en el calendario producidas por
  `_detect_series_gaps` (ver más abajo).

### Por qué no se usa `AnalysisResult`/`AnalysisProvenance`

`investmentops.analysis_engines.contracts.AnalysisResult` exige una
`AnalysisProvenance` (proveedor y modelo de IA que generó la
interpretación). Como este motor, en esta tarea, no invoca ningún
proveedor de IA (ver punto anterior), forzar ese contrato implicaría
fabricar una procedencia de IA inexistente — algo que el proyecto evita
explícitamente en otros lugares (ej. `FINANCIAL_HEALTH_METRICS.md`, "no
se inventa una aproximación"). Por eso se define aquí un tipo de
resultado propio, `TrendAnalysisResult`, con exactamente los tres campos
que pide la tarea (`findings`, `supporting_metrics`, `limitations`) más
un `analysis_id` para identificar este motor, sin `provenance`. Cómo este
resultado se incorpora al `ResearchResult` común (que hoy solo acepta
`AnalysisResult`) es una decisión que corresponde a la tarea siguiente y
separada de "Orquestador" (TASKS.md, Fase 3: "Registrar el nuevo motor de
análisis en el flujo del orquestador... Incluir el nuevo resultado en el
'Resultado de investigación' ensamblado"), no a esta.

### Detección de huecos en la serie (`_detect_series_gaps`)

`TREND_METRICS.md` ya dejaba explícito que la definición de variación
periodo a periodo no distingue huecos reales del calendario (un periodo
faltante) de periodos verdaderamente consecutivos, y que detectarlos
quedaba para esta tarea de ensamblado.

Criterio elegido, sin inventar un umbral fijo de días (ej. "siempre 365
días" no sirve para series trimestrales): con al menos tres periodos (al
menos dos saltos consecutivos, la cantidad mínima para tener una base de
comparación), se calcula la **mediana** de los intervalos en días entre
periodos consecutivos de la serie, como estimación robusta de la
periodicidad esperada (anual, trimestral, u otra). Cualquier salto cuyo
intervalo esté fuera de ``[0.5 × mediana, 1.5 × mediana]``, o que sea
cero o negativo (periodos duplicados o fuera de orden), se reporta como
advertencia de "hueco irregular" identificando explícitamente qué par de
periodos lo produjo.

Con menos de tres periodos (cero o un salto) no hay base para estimar una
periodicidad esperada — inventar un umbral fijo sin esa base violaría el
mismo principio ya aplicado para "estable" en `TREND_METRICS.md` ("no hay
hoy ningún caso de uso... que justifique un umbral concreto"). En ese
caso, `_detect_series_gaps` no reporta ninguna advertencia de huecos (no
implica que no pueda haberlos, solo que no hay información suficiente
para decidirlo).

Fuera de alcance de este módulo:
- Cualquier invocación a un proveedor de IA para este motor (ver "Por qué
  no se usa `AnalysisResult`" arriba): si en el futuro se decide que este
  motor también debe interpretar sus métricas vía IA (siguiendo el
  patrón de salud financiera/valoración), esa sería una tarea explícita y
  separada, no anticipada aquí.
- Registrar este motor en el orquestador e incorporar su resultado al
  `ResearchResult` (tarea separada y posterior, ver TASKS.md, "Fase 3 >
  Orquestador").
- La presentación de este resultado en los reportes Markdown/HTML (tarea
  separada y posterior, ver TASKS.md, "Fase 3 > Reportes").
- Cualquier umbral de tolerancia para "estable", CAGR, proyecciones o
  suavizado estadístico: descartados explícitamente para el MVP (ver
  TREND_METRICS.md).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)

#: Identificador de este motor de análisis, usado como
#: `TrendAnalysisResult.analysis_id`. No se usa para localizar un archivo
#: de prompt (este motor no invoca ningún proveedor de IA en esta tarea,
#: ver "Por qué no se usa AnalysisResult" en el docstring del módulo).
AGENT_ID = "trend_analysis"

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

#: Advertencia usada cuando `detect_revenue_trend` no encuentra ningún
#: salto con clasificación calculable (serie de un solo periodo, vacía, o
#: todos los saltos degenerados por periodo base en cero) del que
#: sintetizar una tendencia agregada de ingresos.
NO_REVENUE_TREND_WARNING = (
    "No hay suficientes variaciones de ingresos calculables en la serie "
    "para determinar una tendencia agregada."
)

#: Misma advertencia que `NO_REVENUE_TREND_WARNING`, pero para la
#: tendencia agregada de beneficios (`detect_net_income_trend`).
NO_NET_INCOME_TREND_WARNING = (
    "No hay suficientes variaciones de beneficios calculables en la "
    "serie para determinar una tendencia agregada."
)

#: Factor mínimo/máximo aceptado entre un salto de la serie y la mediana
#: de todos los saltos, antes de considerarlo un "hueco irregular" (ver
#: "Detección de huecos en la serie" en el docstring del módulo).
_GAP_TOLERANCE_LOWER = 0.5
_GAP_TOLERANCE_UPPER = 1.5


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


@dataclass(frozen=True)
class SeriesTrend:
    """Tendencia agregada de una serie completa de variaciones periodo a periodo.

    Es el tipo de salida de `detect_revenue_trend`/`detect_net_income_trend`
    (ver "Detección simple de tendencia agregada" en el docstring del
    módulo): sintetiza, a partir de las clasificaciones por salto ya
    calculadas (`RevenueGrowthPoint.classification`/
    `NetIncomeGrowthPoint.classification`), una única etiqueta para toda
    la serie.

    Attributes
    ----------
    trend:
        ``"creciente"``, ``"decreciente"`` o ``"estable"`` si todos los
        saltos con clasificación calculable de la serie coinciden;
        ``"mixta"`` si hay clasificaciones distintas entre sí; ``None``
        si no hay ningún salto con clasificación calculable del que
        sintetizar una tendencia (ver `warning`).
    warning:
        Advertencia explícita cuando `trend` es ``None`` (no hay ningún
        salto con clasificación calculable: serie de un solo periodo,
        vacía, o todos los saltos degenerados por periodo base en cero).
        ``None`` si `trend` sí se pudo determinar.
    """

    trend: str | None
    warning: str | None


@dataclass(frozen=True)
class TrendAnalysisResult:
    """Resultado estructurado del motor de análisis de evolución de
    ingresos y beneficios (ver "Ensamblado del resultado estructurado del
    motor" en el docstring del módulo).

    A diferencia de `investmentops.analysis_engines.contracts.AnalysisResult`
    (usado por los motores de salud financiera y valoración, Fase 1), este
    tipo no lleva `provenance`: este motor, en esta tarea, no invoca
    ningún proveedor de IA (ver "Por qué no se usa AnalysisResult/
    AnalysisProvenance" en el docstring del módulo).

    Attributes
    ----------
    analysis_id:
        Identificador de este motor de análisis (siempre `AGENT_ID`,
        ``"trend_analysis"``).
    findings:
        Hallazgos en lenguaje natural, generados por plantilla
        determinista (no por un modelo de lenguaje) a partir de la
        tendencia agregada de ingresos y de beneficios.
    supporting_metrics:
        Métricas de soporte: tendencia agregada de cada serie y variación
        por periodo, ver `assemble_trend_analysis`.
    limitations:
        Advertencias explícitas: de nivel de serie, por punto degenerado,
        de tendencia no determinable, y de huecos irregulares detectados
        en el calendario de la serie.
    """

    analysis_id: str
    findings: Sequence[str]
    supporting_metrics: Mapping[str, Any]
    limitations: Sequence[str]


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


def _aggregate_classifications(
    classifications: Sequence[str],
) -> str:
    """Sintetiza una única etiqueta de tendencia a partir de clasificaciones por salto.

    Compartida por `detect_revenue_trend` y `detect_net_income_trend`:
    ambas funciones usan exactamente el mismo criterio de síntesis (ver
    "Detección simple de tendencia agregada" en el docstring del módulo).
    Asume que `classifications` ya excluye los saltos sin clasificación
    calculable (``None``) y que tiene al menos un elemento; el manejo del
    caso vacío vive en las funciones que llaman a esta.
    """
    unique = set(classifications)
    if len(unique) == 1:
        return unique.pop()
    return "mixta"


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


def detect_revenue_trend(result: RevenueGrowthResult) -> SeriesTrend:
    """Sintetiza una tendencia agregada de ingresos a partir de un `RevenueGrowthResult`.

    Ver "Detección simple de tendencia agregada" en el docstring del
    módulo para el criterio completo. Ignora los puntos sin clasificación
    calculable (`classification is None`, ver `calculate_revenue_growth`)
    al sintetizar; si ninguno de los puntos tiene clasificación
    calculable, devuelve `trend=None` con `NO_REVENUE_TREND_WARNING`.

    Parameters
    ----------
    result:
        El `RevenueGrowthResult` ya producido por `calculate_revenue_growth`
        para una serie.

    Returns
    -------
    SeriesTrend
        - `trend="creciente"`/`"decreciente"`/`"estable"` si todos los
          puntos con clasificación calculable coinciden.
        - `trend="mixta"` si hay clasificaciones distintas entre sí.
        - `trend=None` con `warning=NO_REVENUE_TREND_WARNING` si
          `result.points` está vacío o ningún punto tiene una
          clasificación calculable.
    """
    classifications = [
        point.classification for point in result.points if point.classification is not None
    ]

    if not classifications:
        return SeriesTrend(trend=None, warning=NO_REVENUE_TREND_WARNING)

    return SeriesTrend(trend=_aggregate_classifications(classifications), warning=None)


def detect_net_income_trend(result: NetIncomeGrowthResult) -> SeriesTrend:
    """Sintetiza una tendencia agregada de beneficios a partir de un `NetIncomeGrowthResult`.

    Mismo criterio que `detect_revenue_trend`, aplicado a
    `NetIncomeGrowthResult` (ver "Detección simple de tendencia agregada"
    en el docstring del módulo).

    Parameters
    ----------
    result:
        El `NetIncomeGrowthResult` ya producido por
        `calculate_net_income_growth` para una serie.

    Returns
    -------
    SeriesTrend
        - `trend="creciente"`/`"decreciente"`/`"estable"` si todos los
          puntos con clasificación calculable coinciden.
        - `trend="mixta"` si hay clasificaciones distintas entre sí.
        - `trend=None` con `warning=NO_NET_INCOME_TREND_WARNING` si
          `result.points` está vacío o ningún punto tiene una
          clasificación calculable.
    """
    classifications = [
        point.classification for point in result.points if point.classification is not None
    ]

    if not classifications:
        return SeriesTrend(trend=None, warning=NO_NET_INCOME_TREND_WARNING)

    return SeriesTrend(trend=_aggregate_classifications(classifications), warning=None)


def _describe_trend(label: str, trend: SeriesTrend) -> str:
    """Genera un hallazgo en lenguaje natural a partir de una `SeriesTrend`.

    Plantilla determinista, no generada por un modelo de lenguaje (ver
    "Ensamblado del resultado estructurado del motor" en el docstring del
    módulo). Compartida por `assemble_trend_analysis` para ingresos y
    beneficios.

    Parameters
    ----------
    label:
        Sustantivo plural a insertar en el texto (``"ingresos"`` o
        ``"beneficios"``).
    trend:
        La `SeriesTrend` ya sintetizada por `detect_revenue_trend`/
        `detect_net_income_trend`.
    """
    if trend.trend is None:
        return f"No hay suficientes datos para determinar una tendencia de {label}."

    descriptions = {
        "creciente": f"Los {label} muestran una tendencia creciente en los periodos analizados.",
        "decreciente": f"Los {label} muestran una tendencia decreciente en los periodos analizados.",
        "estable": f"Los {label} se han mantenido estables en los periodos analizados.",
        "mixta": (
            f"Los {label} muestran una tendencia mixta (sin una dirección "
            "consistente) en los periodos analizados."
        ),
    }
    return descriptions[trend.trend]


def _detect_series_gaps(series: FinancialStatementSeries) -> list[str]:
    """Detecta huecos irregulares en el calendario de una serie.

    Ver "Detección de huecos en la serie" en el docstring del módulo para
    el criterio completo: con al menos tres periodos, calcula la mediana
    de los intervalos en días entre periodos consecutivos como estimación
    de la periodicidad esperada, y marca como "hueco irregular" cualquier
    intervalo fuera de ``[0.5, 1.5] × mediana``, o que sea cero o
    negativo.

    Parameters
    ----------
    series:
        La `FinancialStatementSeries` a inspeccionar.

    Returns
    -------
    list[str]
        Una advertencia por cada par de periodos consecutivos cuyo
        intervalo se considera irregular. Lista vacía si la serie tiene
        menos de tres periodos (sin base para estimar periodicidad) o si
        todos los intervalos son consistentes entre sí.
    """
    statements = series.statements

    if len(statements) < 3:
        return []

    gaps_days = [
        (current.period_end - previous.period_end).days
        for current, previous in zip(statements, statements[1:])
    ]

    median_gap = statistics.median(gaps_days)

    warnings: list[str] = []
    for (current, previous), gap_days in zip(zip(statements, statements[1:]), gaps_days):
        is_out_of_order = gap_days <= 0
        is_irregular = median_gap > 0 and not (
            _GAP_TOLERANCE_LOWER * median_gap <= gap_days <= _GAP_TOLERANCE_UPPER * median_gap
        )
        if is_out_of_order or is_irregular:
            warnings.append(
                "Se detectó un hueco irregular en la serie entre "
                f"{previous.period_end.isoformat()} y "
                f"{current.period_end.isoformat()} (brecha de {gap_days} "
                f"días; el resto de la serie sugiere una periodicidad de "
                f"~{median_gap:.0f} días)."
            )

    return warnings


def assemble_trend_analysis(series: FinancialStatementSeries) -> TrendAnalysisResult:
    """Ensambla el resultado estructurado del motor de evolución de
    ingresos y beneficios para una serie.

    Encadena `calculate_revenue_growth`, `calculate_net_income_growth`,
    `detect_revenue_trend`, `detect_net_income_trend` y
    `_detect_series_gaps` (todas ya implementadas en este módulo), y
    empaqueta sus resultados en un `TrendAnalysisResult` (ver "Ensamblado
    del resultado estructurado del motor" en el docstring del módulo).

    Parameters
    ----------
    series:
        La `FinancialStatementSeries` (ver
        `investmentops.data_layer.FinancialStatementSeries`) a analizar.

    Returns
    -------
    TrendAnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"trend_analysis"``).
        - `findings`: dos hallazgos, uno para ingresos y uno para
          beneficios (ver `_describe_trend`).
        - `supporting_metrics`: `revenue_trend`, `net_income_trend`
          (tendencias agregadas) y `revenue_growth_by_period`,
          `net_income_growth_by_period` (variación por periodo, keyed
          por `period_end` en ISO 8601, valor `None` si no fue
          calculable para ese salto).
        - `limitations`: advertencias de nivel de serie, por punto
          degenerado, de tendencia no determinable, y de huecos
          irregulares en el calendario (ver `_detect_series_gaps`).
    """
    revenue_result = calculate_revenue_growth(series)
    net_income_result = calculate_net_income_growth(series)
    revenue_trend = detect_revenue_trend(revenue_result)
    net_income_trend = detect_net_income_trend(net_income_result)
    gap_warnings = _detect_series_gaps(series)

    findings = [
        _describe_trend("ingresos", revenue_trend),
        _describe_trend("beneficios", net_income_trend),
    ]

    supporting_metrics: dict[str, Any] = {
        "revenue_trend": revenue_trend.trend,
        "net_income_trend": net_income_trend.trend,
        "revenue_growth_by_period": {
            point.period_end.isoformat(): point.revenue_growth
            for point in revenue_result.points
        },
        "net_income_growth_by_period": {
            point.period_end.isoformat(): point.net_income_growth
            for point in net_income_result.points
        },
    }

    limitations: list[str] = []
    limitations.extend(revenue_result.warnings)
    limitations.extend(net_income_result.warnings)
    limitations.extend(
        point.warning for point in revenue_result.points if point.warning is not None
    )
    limitations.extend(
        point.warning for point in net_income_result.points if point.warning is not None
    )
    if revenue_trend.warning is not None:
        limitations.append(revenue_trend.warning)
    if net_income_trend.warning is not None:
        limitations.append(net_income_trend.warning)
    limitations.extend(gap_warnings)

    return TrendAnalysisResult(
        analysis_id=AGENT_ID,
        findings=findings,
        supporting_metrics=supporting_metrics,
        limitations=limitations,
    )
