# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Motor de análisis: evolución de ingresos y beneficios →
*"Implementar el cálculo de variación periodo a periodo de ingresos."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo anterior:
no existía ningún módulo de código bajo `investmentops/analysis_engines/`
que calculara variación de ingresos; solo existía la definición de diseño
(`TREND_METRICS.md`, tarea previa) y el modelo de dominio de entrada
(`FinancialStatementSeries`, Fase 3 "Normalización"), pero ningún motor
de análisis los consumía todavía. Era trabajo nuevo, no una tarea ya
cubierta.

## Qué se implementó

**`investmentops/analysis_engines/trends.py`** (nuevo):

- `calculate_revenue_growth(series: FinancialStatementSeries) -> RevenueGrowthResult`:
  cálculo puramente determinístico (sin IA, conforme a `ARCHITECTURE.md`),
  que recorre `series.statements` en pares consecutivos y calcula, para
  cada uno, `revenue_growth = (revenue_t - revenue_{t-1}) /
  abs(revenue_{t-1})`, exactamente la fórmula ya fijada en
  `investmentops/analysis_engines/TREND_METRICS.md`.
- `RevenueGrowthPoint` (dataclass inmutable): un punto por cada salto
  entre periodos consecutivos, con `period_end`, `previous_period_end`,
  `revenue_growth`, `classification` (`"creciente"`/`"decreciente"`/
  `"estable"`, por signo puro, sin banda de tolerancia) y `warning`
  (`None` salvo que ese salto concreto no se pudo calcular).
- `RevenueGrowthResult` (dataclass inmutable): agrupa `points` (uno por
  par consecutivo) y `warnings` (advertencias a nivel de toda la serie).
- Manejo de casos degenerados, exactamente como los fija
  `TREND_METRICS.md`:
  - **Periodo base con `revenue == 0`:** ese punto concreto devuelve
    `revenue_growth`/`classification` en `None`, con una advertencia
    adjunta al propio punto (`RevenueGrowthPoint.warning`), sin lanzar
    `ZeroDivisionError` ni afectar a los demás pares de la serie.
  - **Serie con menos de dos periodos (uno solo, o vacía):** no hay
    ningún par consecutivo; se devuelve `points=()` junto con
    `SINGLE_PERIOD_WARNING` a nivel de serie (`RevenueGrowthResult.warnings`).
- No calcula `net_income_growth` (tarea siguiente), no detecta tendencia
  agregada para toda la serie, ni ensambla ningún `AnalysisResult`: fuera
  de alcance explícito de esta tarea concreta.

**`investmentops/tests/test_analysis_engines_trends.py`** (nuevo):
cubre el caso de dos periodos consecutivos, varios periodos (varios
saltos en el mismo orden que `statements`), las tres clasificaciones
(creciente/decreciente/estable), el caso de mejora desde una base
negativa (uso de `abs()` en el denominador), el periodo base en cero
(incluyendo que solo afecta al salto correspondiente, no a los demás),
la ausencia de `ZeroDivisionError`, la serie de un único periodo y la
serie vacía, e inmutabilidad de ambos dataclasses.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/trends.py` (nuevo)
- `investmentops/tests/test_analysis_engines_trends.py` (nuevo)

Modificados:
- `TASKS.md` (tarea marcada como completada, Fase 3, "Motor de análisis:
  evolución de ingresos y beneficios")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `TREND_METRICS.md`, ni ningún
otro módulo de código Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

La siguiente tarea pendiente en la misma sección de `TASKS.md` ("Motor
de análisis: evolución de ingresos y beneficios") es:

> "Implementar el cálculo de variación periodo a periodo de beneficios."

Debe seguir exactamente el mismo patrón ya usado en
`calculate_revenue_growth`/`RevenueGrowthResult`/`RevenueGrowthPoint`
(`investmentops/analysis_engines/trends.py`), aplicado a `net_income` en
vez de `revenue` (misma fórmula con `abs()` en el denominador, misma
clasificación por signo puro, mismo manejo de periodo base en cero y de
series con menos de dos periodos), probablemente como un
`calculate_net_income_growth`/`NetIncomeGrowthResult`/
`NetIncomeGrowthPoint` en el mismo módulo, para mantener juntas ambas
piezas de "variación periodo a periodo" antes de la tarea de detección
de tendencia agregada.
