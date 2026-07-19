# InvestmentOps — Progreso

**Última actualización:** 2026-07-19

## Última tarea completada

Fase 3 → Motor de análisis: evolución de ingresos y beneficios →
*"Ensamblar el resultado estructurado del motor (hallazgos, métricas de
soporte, advertencias si hay huecos en la serie)."*

## Resolución previa: duplicación `trends.py`/`trend.py`

Antes de esta sesión, quedaba pendiente de confirmación del usuario la
duplicación ya señalada en actualizaciones anteriores de este archivo:
`investmentops/analysis_engines/trend.py` (singular) era un módulo
incompatible y no canónico que cubría parcialmente la misma sección con
otra API (`PeriodGrowth`/`RevenueGrowthResult` con campo `values`), junto
a sus propios archivos de prueba. El usuario confirmó y eliminó
`trend.py` y sus tests asociados antes de esta sesión. `trends.py`
(plural) queda como la única implementación vigente de este motor de
análisis, sin ambigüedad para trabajo futuro.

## Verificación previa (sin duplicar trabajo)

Se confirmó que la tarea de ensamblado **no** estaba satisfecha por
trabajo anterior: `trends.py` ya tenía `calculate_revenue_growth`,
`calculate_net_income_growth`, `detect_revenue_trend` y
`detect_net_income_trend`, pero ninguna función empaquetaba esos
resultados en una única estructura de salida con hallazgos, métricas de
soporte y advertencias de huecos — exactamente lo que pide esta tarea, y
que `TREND_METRICS.md` ya dejaba explícitamente para "la tarea de
ensamblado del motor".

## Qué se implementó

**`investmentops/analysis_engines/trends.py`** (modificado):

- `TrendAnalysisResult` (dataclass inmutable): tipo de salida de
  `assemble_trend_analysis`. Campos: `analysis_id` (siempre `AGENT_ID`,
  `"trend_analysis"`), `findings` (dos hallazgos, ingresos y beneficios),
  `supporting_metrics` (mapeo) y `limitations` (advertencias). **No**
  incluye `provenance`: a diferencia de los motores de salud
  financiera/valoración (Fase 1), `TASKS.md` no define para este motor
  ninguna tarea de "escribir prompt" ni "invocar proveedor de IA" — esta
  tarea concreta solo pide ensamblar hallazgos/métricas/advertencias a
  partir de cálculos ya deterministas. Forzar el contrato común
  `AnalysisResult`/`AnalysisProvenance` (que exige proveedor y modelo de
  IA) habría implicado fabricar una procedencia de IA inexistente, algo
  que el proyecto evita explícitamente en otros lugares (ver
  `FINANCIAL_HEALTH_METRICS.md`, "no se inventa una aproximación"). Cómo
  este resultado se incorpora al `ResearchResult` común (que hoy solo
  acepta `AnalysisResult`) queda para la tarea separada "Orquestador" de
  esta misma fase.
- `assemble_trend_analysis(series) -> TrendAnalysisResult`: encadena
  `calculate_revenue_growth`, `calculate_net_income_growth`,
  `detect_revenue_trend`, `detect_net_income_trend` (ya existentes) y
  `_detect_series_gaps` (nueva). Construye:
  - `findings`: dos hallazgos en lenguaje natural (uno para ingresos, uno
    para beneficios), generados por plantilla determinista (`_describe_trend`)
    a partir de `SeriesTrend.trend` — no producidos por un modelo de
    lenguaje.
  - `supporting_metrics`: `revenue_trend`/`net_income_trend` (tendencia
    agregada) y `revenue_growth_by_period`/`net_income_growth_by_period`
    (variación por periodo, keyed por `period_end` en ISO 8601).
  - `limitations`: agrega, sin perder ninguna, las advertencias de nivel
    de serie (`SINGLE_PERIOD_WARNING`/`NET_INCOME_SINGLE_PERIOD_WARNING`),
    las advertencias por punto degenerado (periodo base en cero), las
    advertencias de tendencia no determinable
    (`NO_REVENUE_TREND_WARNING`/`NO_NET_INCOME_TREND_WARNING`) y las
    advertencias de huecos irregulares.
- `_detect_series_gaps(series) -> list[str]` (función interna): con al
  menos tres periodos (al menos dos saltos consecutivos), calcula la
  mediana de los intervalos en días entre periodos consecutivos como
  estimación robusta de la periodicidad esperada de la serie (anual,
  trimestral, u otra), y marca como "hueco irregular" cualquier salto
  fuera de `[0.5, 1.5] × mediana`, o que sea cero o negativo (periodos
  duplicados o fuera de orden). Con menos de tres periodos no hay base
  para estimar una periodicidad esperada, así que no se reporta ninguna
  advertencia de huecos en ese caso (documentado explícitamente como
  limitación de la propia detección, no como ausencia de huecos
  confirmada). No se inventa un umbral fijo de días (ej. "siempre 365"),
  ya que eso no serviría para series trimestrales.
- `_describe_trend(label, trend) -> str` (función interna): plantilla
  determinista compartida por ingresos y beneficios para redactar el
  hallazgo correspondiente a partir de `SeriesTrend`.
- `AGENT_ID = "trend_analysis"` (constante nueva): identificador de este
  motor, usado como `TrendAnalysisResult.analysis_id`.
- No se modificó el comportamiento de `calculate_revenue_growth`/
  `calculate_net_income_growth`/`detect_revenue_trend`/
  `detect_net_income_trend`/`_classify`/`_aggregate_classifications` ya
  existentes; solo se amplió el docstring del módulo para cubrir la
  nueva sección de ensamblado.

**`investmentops/tests/test_analysis_engines_trend_assembly.py`** (nuevo):
cubre: estructura básica del `TrendAnalysisResult` (analysis_id,
inmutabilidad), hallazgos (uno por métrica, texto de tendencia creciente,
texto de "sin datos suficientes" para series de un solo periodo),
métricas de soporte (tendencias agregadas, variación por periodo keyed
por fecha ISO, caso vacío para series de un solo periodo), advertencias
(de nivel de serie, por punto degenerado, ausencia de limitaciones para
una serie limpia y consistente), y detección de huecos (serie anual
regular sin advertencias, un hueco de dos años en una serie por lo demás
anual, ausencia de detección con menos de tres periodos, y detección de
periodos duplicados/fuera de orden con brecha cero).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_analysis_engines_trend_assembly.py` (nuevo)

Modificados:
- `investmentops/analysis_engines/trends.py` (se agregaron
  `TrendAnalysisResult`, `assemble_trend_analysis`,
  `_detect_series_gaps`, `_describe_trend`, `AGENT_ID`,
  `_GAP_TOLERANCE_LOWER`/`_GAP_TOLERANCE_UPPER`; el resto del módulo no
  cambió de comportamiento)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Motor de análisis:
  evolución de ingresos y beneficios")
- `PROGRESS.md` (este archivo)

Eliminados (por el usuario, antes de esta sesión, confirmado):
- `investmentops/analysis_engines/trend.py`
- Sus archivos de prueba asociados (`test_analysis_engines_trend.py`,
  `test_analysis_engines_trend_revenue.py`)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `TREND_METRICS.md`, ni ningún
otro módulo de código Python existente (en particular, no se tocó
`investmentops/core/orchestrator.py`: registrar este motor en el
orquestador es la tarea siguiente, separada).

## Verificación realizada

Se revisaron manualmente los 24 casos de prueba nuevos
(`test_analysis_engines_trend_assembly.py`) contra la lógica de
`assemble_trend_analysis`/`_detect_series_gaps`/`_describe_trend`,
confirmando en particular:
- Una serie anual consistentemente creciente de 4 periodos produce
  `revenue_trend="creciente"`, `net_income_trend="creciente"`, hallazgos
  con la palabra "creciente", y `limitations == []` (sin huecos, sin
  advertencias de casos degenerados).
- Sustituir un periodo intermedio por un salto de 2 años en una serie
  por lo demás anual produce exactamente una advertencia de "hueco
  irregular" mencionando ambos extremos del salto.
- Una serie de un único periodo produce hallazgos de "no hay suficientes
  datos", `supporting_metrics` con diccionarios de variación vacíos y
  tendencias `None`, y las cuatro advertencias de nivel de serie/
  tendencia esperadas.
- Un periodo duplicado (misma fecha dos veces) se marca siempre como
  hueco irregular (brecha de 0 días), independientemente de la mediana
  del resto de la serie.

No se ejecutó el entorno real de pruebas (`pytest`) en esta sesión por
no tener acceso al repositorio del usuario; los archivos se entregan
como artifacts para que el usuario los copie y corra la suite completa.

## Problemas encontrados

Ninguno nuevo. Se mantiene, ya anotado en actualizaciones previas, el
hallazgo sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`), sin resolver por no ser parte del alcance de
esta tarea.

## Próxima tarea recomendada

La siguiente sección pendiente de `TASKS.md` (Fase 3, "Orquestador") no
tiene tareas marcadas como completadas todavía:

> "Registrar el nuevo motor de análisis en el flujo del orquestador sin
> modificar los motores existentes."
>
> "Incluir el nuevo resultado en el 'Resultado de investigación'
> ensamblado."

Antes de implementarla, conviene decidir explícitamente cómo un
`TrendAnalysisResult` (sin `AnalysisProvenance`) se incorpora a
`ResearchResult.analysis_results`, que hoy es
`Sequence[AnalysisResult]` (contrato que sí exige procedencia de IA).
Esta decisión de diseño no se tomó en la presente sesión porque
correspondía estrictamente a la tarea de ensamblado, no a la de
integración con el orquestador; se deja señalada aquí para que la
siguiente sesión la aborde explícitamente antes de escribir código (por
ejemplo: extender `ResearchResult` para aceptar un tipo de resultado más
general, o construir una `AnalysisProvenance` sintética marcando
`ai_provider="none"`/`ai_model="deterministic"`, u otra alternativa —
ninguna de las tres se ha decidido todavía).
