# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Motor de análisis: evolución de ingresos y beneficios →
*"Implementar el cálculo de variación periodo a periodo de beneficios."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo anterior:
`investmentops/analysis_engines/trends.py` (el módulo canónico, ver la
tarea anterior en este mismo archivo) solo tenía
`calculate_revenue_growth`; no existía ninguna función que calculara
`net_income_growth`.

Nota sobre duplicación detectada en el repositorio: además de
`investmentops/analysis_engines/trends.py` (con
`RevenueGrowthPoint`/`RevenueGrowthResult`, campo `points`), el
repositorio también contiene `investmentops/analysis_engines/trend.py`
(con `PeriodGrowth`/`RevenueGrowthResult`, campo `values`), un módulo
distinto que cubre la misma tarea con una API diferente e incompatible,
junto con sus propios archivos de prueba
(`test_analysis_engines_trend.py`, `test_analysis_engines_trend_revenue.py`).
Esto no fue creado en esta sesión. Se continuó extendiendo
`investmentops/analysis_engines/trends.py`, ya que es el módulo que
`PROGRESS.md` documenta explícitamente como la implementación de la
tarea anterior ("Implementar el cálculo de variación periodo a periodo
de ingresos") y el que recomienda extender a continuación. `trend.py`
(singular) no se tocó ni se usó como base; se deja señalado aquí para
que una futura limpieza decida si debe eliminarse o consolidarse, ya que
tener dos módulos que resuelven la misma tarea con contratos distintos
es una fuente de confusión, no una decisión de diseño deliberada.

## Qué se implementó

**`investmentops/analysis_engines/trends.py`** (modificado):

- `calculate_net_income_growth(series: FinancialStatementSeries) -> NetIncomeGrowthResult`:
  cálculo puramente determinístico (sin IA), que sigue exactamente el
  mismo patrón ya usado por `calculate_revenue_growth`, aplicado a
  `net_income` en vez de `revenue`: recorre `series.statements` en pares
  consecutivos y calcula, para cada uno, `net_income_growth =
  (net_income_t - net_income_{t-1}) / abs(net_income_{t-1})`, la fórmula
  ya fijada en `investmentops/analysis_engines/TREND_METRICS.md`.
- `NetIncomeGrowthPoint` (dataclass inmutable): mismo shape que
  `RevenueGrowthPoint` (`period_end`, `previous_period_end`,
  `net_income_growth`, `classification`, `warning`).
- `NetIncomeGrowthResult` (dataclass inmutable): agrupa `points` y
  `warnings`, mismo shape que `RevenueGrowthResult`.
- Reutiliza `_classify` (ya existente en el módulo, usada también por
  `calculate_revenue_growth`) para la clasificación por signo puro
  (creciente/decreciente/estable), sin duplicar esa lógica.
- Mismo manejo de casos degenerados que la variación de ingresos:
  - **Periodo base con `net_income == 0`:** ese punto concreto devuelve
    `net_income_growth`/`classification` en `None`, con una advertencia
    adjunta al propio punto, sin lanzar `ZeroDivisionError` ni afectar a
    los demás pares de la serie.
  - **Serie con menos de dos periodos:** se devuelve `points=()` junto
    con `NET_INCOME_SINGLE_PERIOD_WARNING` (constante nueva, análoga a
    `SINGLE_PERIOD_WARNING` ya existente para ingresos) a nivel de serie.
- No detecta tendencia agregada para toda la serie ni ensambla ningún
  `AnalysisResult`: fuera de alcance explícito de esta tarea concreta
  (tareas siguientes ya listadas en `TASKS.md`).

**`investmentops/tests/test_analysis_engines_trends_net_income.py`** (nuevo):
cubre el caso de dos periodos consecutivos, varios periodos (varios
saltos en el mismo orden que `statements`), las tres clasificaciones
(creciente/decreciente/estable), el caso de mejora desde una base
negativa (uso de `abs()` en el denominador), el periodo base en cero
(incluyendo que solo afecta al salto correspondiente, no a los demás),
la ausencia de `ZeroDivisionError`, la serie de un único periodo y la
serie vacía, e inmutabilidad de ambos dataclasses — mismo patrón de
pruebas ya usado en `test_analysis_engines_trends.py` para
`calculate_revenue_growth`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_analysis_engines_trends_net_income.py` (nuevo)

Modificados:
- `investmentops/analysis_engines/trends.py` (se agregaron
  `NetIncomeGrowthPoint`, `NetIncomeGrowthResult`,
  `NET_INCOME_SINGLE_PERIOD_WARNING` y `calculate_net_income_growth`;
  `RevenueGrowthPoint`/`RevenueGrowthResult`/`calculate_revenue_growth`
  no cambiaron de comportamiento, solo se reordenó el docstring del
  módulo para cubrir ambas funciones)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Motor de análisis:
  evolución de ingresos y beneficios")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `TREND_METRICS.md`,
`investmentops/analysis_engines/trend.py` (módulo duplicado, ver nota
arriba), ni ningún otro módulo de código Python existente.

## Problemas encontrados

Se detectó la duplicación de módulos `trends.py`/`trend.py` descrita
arriba (dos implementaciones distintas de la misma tarea de variación de
ingresos, con contratos incompatibles y sus propios archivos de prueba
cada una). No se resolvió en esta sesión porque la instrucción es
implementar solo la tarea pendiente actual sin rediseñar la
arquitectura; queda anotado para que una tarea futura decida
explícitamente cuál de los dos módulos conservar. Se mantiene también el
hallazgo ya anotado en actualizaciones anteriores sobre la duplicación
de carpetas de pruebas (`tests/` vs. `investmentops/tests/`).

## Próxima tarea recomendada

La siguiente tarea pendiente en la misma sección de `TASKS.md` ("Motor
de análisis: evolución de ingresos y beneficios") es:

> "Implementar la detección simple de tendencia (creciente, decreciente,
> estable) para cada serie."

Esta tarea es distinta de la clasificación por salto individual que ya
existe (`RevenueGrowthPoint.classification`/
`NetIncomeGrowthPoint.classification`): se trata de sintetizar, para
toda la serie de saltos calculados, si la tendencia general es
consistentemente creciente, consistentemente decreciente, o mixta (ver
`TREND_METRICS.md`, que ya deja explícito que esta síntesis es alcance
de esta tarea, no de la anterior). Antes de implementar, conviene
resolver primero (o al menos decidir explícitamente cómo tratar) la
duplicación `trends.py`/`trend.py` señalada arriba, para no construir la
detección de tendencia sobre un módulo que podría descartarse.
