# InvestmentOps — Progreso

**Última actualización:** 2026-07-18

## Última tarea completada

Fase 3 → Motor de análisis: evolución de ingresos y beneficios →
*"Implementar la detección simple de tendencia (creciente, decreciente,
estable) para cada serie."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo anterior:
`investmentops/analysis_engines/trends.py` (el módulo canónico, ver
tareas anteriores en este mismo archivo) ya tenía
`calculate_revenue_growth`/`calculate_net_income_growth`, cada uno con
una clasificación **por salto** (`RevenueGrowthPoint.classification`/
`NetIncomeGrowthPoint.classification`), pero no existía ninguna función
que sintetizara una única tendencia agregada para **toda la serie**. Esa
distinción ya está explícita en `TREND_METRICS.md` ("Clasificación de
tendencia": *"esta clasificación es por salto... esa síntesis... es
explícitamente el alcance de la tarea siguiente"*), por lo que la tarea
es trabajo nuevo.

Se mantiene la nota de duplicación ya señalada en la actualización
anterior: `investmentops/analysis_engines/trend.py` (singular) es un
módulo distinto e incompatible que cubre parte de la misma sección con
otra API (`PeriodGrowth`/`RevenueGrowthResult` con campo `values`). No se
tocó en esta sesión, siguiendo el mismo criterio ya documentado: se
continuó extendiendo `trends.py` (plural), el módulo que `PROGRESS.md` ya
documenta como la implementación vigente.

## Qué se implementó

**`investmentops/analysis_engines/trends.py`** (modificado):

- `SeriesTrend` (dataclass inmutable): tipo de salida común a
  `detect_revenue_trend`/`detect_net_income_trend`. Campos: `trend`
  (``"creciente"``/``"decreciente"``/``"estable"``/``"mixta"``/``None``)
  y `warning` (texto explícito cuando `trend` es `None`, o `None` en caso
  contrario).
- `detect_revenue_trend(result: RevenueGrowthResult) -> SeriesTrend`:
  sintetiza, a partir de las clasificaciones por salto ya calculadas por
  `calculate_revenue_growth`, una única etiqueta de tendencia para toda
  la serie:
  - Ignora los puntos sin clasificación calculable
    (`classification is None`, producidos por un periodo base en cero):
    no rompen una tendencia por lo demás consistente ni cuentan como
    "mixta".
  - Si todos los puntos con clasificación calculable coinciden, esa es
    la tendencia (`"creciente"`/`"decreciente"`/`"estable"`).
  - Si difieren entre sí, la tendencia es `"mixta"`.
  - Si no hay ningún punto con clasificación calculable (serie vacía, de
    un solo periodo, o todos los saltos degenerados por periodo base en
    cero), devuelve `trend=None` junto con `NO_REVENUE_TREND_WARNING`,
    en vez de inventar una etiqueta o fallar.
- `detect_net_income_trend(result: NetIncomeGrowthResult) -> SeriesTrend`:
  mismo criterio exacto que `detect_revenue_trend`, aplicado a
  `net_income_growth`/`NetIncomeGrowthResult`; usa
  `NO_NET_INCOME_TREND_WARNING` (mensaje propio, distinto del de
  ingresos) cuando no hay clasificación calculable.
- `_aggregate_classifications(classifications) -> str` (función interna):
  compartida por ambas funciones públicas, evita duplicar el criterio de
  síntesis (todas iguales → esa etiqueta; distintas → `"mixta"`).
- `NO_REVENUE_TREND_WARNING`/`NO_NET_INCOME_TREND_WARNING` (constantes
  nuevas): advertencias explícitas y distinguibles entre ingresos y
  beneficios para el caso "sin datos suficientes".
- No se modificó el comportamiento de `calculate_revenue_growth`/
  `calculate_net_income_growth`/`_classify` ya existentes; solo se
  reordenó/amplió el docstring del módulo para cubrir la nueva sección.

**`investmentops/tests/test_analysis_engines_trend_detection.py`** (nuevo):
cubre, para ambas métricas (ingresos y beneficios): tendencia
consistentemente creciente/decreciente/estable, tendencia mixta, serie de
un único punto, saltos degenerados ignorados sin romper una tendencia
consistente, ausencia total de clasificación calculable (`trend=None` con
la advertencia correspondiente), inmutabilidad de `SeriesTrend`, y que los
mensajes de advertencia de ingresos y beneficios son textos distintos
(para no confundir a quien lea el resultado).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_analysis_engines_trend_detection.py` (nuevo)

Modificados:
- `investmentops/analysis_engines/trends.py` (se agregaron `SeriesTrend`,
  `detect_revenue_trend`, `detect_net_income_trend`,
  `_aggregate_classifications`, `NO_REVENUE_TREND_WARNING`,
  `NO_NET_INCOME_TREND_WARNING`; `RevenueGrowthPoint`/
  `RevenueGrowthResult`/`calculate_revenue_growth`/
  `NetIncomeGrowthPoint`/`NetIncomeGrowthResult`/
  `calculate_net_income_growth`/`_classify` no cambiaron de
  comportamiento)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Motor de análisis:
  evolución de ingresos y beneficios")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `TREND_METRICS.md`,
`investmentops/analysis_engines/trend.py` (módulo duplicado, ver nota
arriba), ni ningún otro módulo de código Python existente.

## Verificación realizada

Se ejecutaron las 15 pruebas nuevas (`test_analysis_engines_trend_detection.py`)
en un entorno mínimo aislado (stubs de `FinancialStatement`/
`FinancialStatementSeries`, sin llamadas de red), con resultado 15/15
exitosas. Se corrió además un script de verificación manual end-to-end
encadenando `calculate_revenue_growth`/`calculate_net_income_growth` →
`detect_revenue_trend`/`detect_net_income_trend` sobre una serie de tres
periodos consistentemente creciente, confirmando que el resultado final
es coherente (`SeriesTrend(trend='creciente', warning=None)` para ambas
métricas).

## Problemas encontrados

Se mantiene sin resolver la duplicación de módulos `trends.py`/`trend.py`
ya señalada en la actualización anterior de `PROGRESS.md` (dos
implementaciones distintas de la variación de ingresos con contratos
incompatibles, cada una con sus propios archivos de prueba). No se
resolvió en esta sesión por el mismo motivo ya documentado: la
instrucción es implementar solo la tarea pendiente actual sin rediseñar
la arquitectura. Se mantiene también el hallazgo, ya anotado en
actualizaciones previas, sobre la duplicación de carpetas de pruebas
(`tests/` vs. `investmentops/tests/`).

## Próxima tarea recomendada

La siguiente tarea pendiente en la misma sección de `TASKS.md` ("Motor
de análisis: evolución de ingresos y beneficios") es:

> "Ensamblar el resultado estructurado del motor (hallazgos, métricas de
> soporte, advertencias si hay huecos en la serie)."

Esta tarea cierra el motor de análisis de evolución: tomar
`RevenueGrowthResult`/`NetIncomeGrowthResult` y las `SeriesTrend` ya
calculadas y producir un `AnalysisResult` (mismo contrato ya usado por
los agentes de salud financiera y valoración de la Fase 1), incluyendo
advertencias explícitas si se detectan huecos en el calendario entre
periodos (ver `TREND_METRICS.md`, "Huecos en la serie": esta definición
no los distingue de periodos verdaderamente consecutivos, y detectarlos
queda explícitamente para esta tarea de ensamblado). Antes de
implementarla, sigue pendiente la decisión (no bloqueante, pero señalada
repetidamente) de qué hacer con el módulo duplicado `trend.py`.
