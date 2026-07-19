# InvestmentOps — Progreso

**Última actualización:** 2026-07-19

## Última tarea completada

Fase 3, "Orquestador" → "Registrar la invocación de
`assemble_trend_analysis` en el flujo de análisis del orquestador,
conforme a la decisión de integración ya tomada, sin modificar los
motores existentes (salud financiera, valoración)" (TASKS.md).

### Qué se implementó

`investmentops/core/orchestrator.py` gana, sobre la decisión ya
documentada en `investmentops/core/TREND_INTEGRATION.md`:

- **`TREND_ANALYSIS_AI_PROVIDER = "none"` / `TREND_ANALYSIS_AI_MODEL =
  "deterministic"`**: constantes con los valores centinela de
  procedencia ya decididos en `TREND_INTEGRATION.md`.
- **`_trend_analysis_result_to_analysis_result(trend_result, *,
  generated_at=None) -> AnalysisResult`**: adaptador puro que envuelve
  un `TrendAnalysisResult` (sin `provenance`, ver
  `investmentops.analysis_engines.trends`) en un `AnalysisResult`
  normal, copiando `analysis_id`/`findings`/`supporting_metrics`/
  `limitations` tal cual y construyendo una `AnalysisProvenance`
  centinela (`ai_provider="none"`, `ai_model="deterministic"`,
  `generated_at` = momento de la llamada si no se indica). No modifica
  `AnalysisResult`, `AnalysisProvenance` ni `TrendAnalysisResult`.
- **`run_trend_analysis_engine(ticker, *, config=None, provider=None,
  period="annual", limit=5) -> AnalysisResult`**: pieza que "registra la
  invocación" del motor de evolución de ingresos y beneficios en el
  flujo del orquestador. Encadena `fetch_and_normalize_historical(ticker,
  ...)` (ya implementada en la tarea anterior de esta misma sección) →
  `investmentops.analysis_engines.trends.assemble_trend_analysis(series)`
  (motor ya implementado, sin modificar) →
  `_trend_analysis_result_to_analysis_result(...)`. No captura
  `DataProviderError` ni `NormalizationError`: las propaga tal cual,
  mismo criterio ya usado por `fetch_and_normalize`/
  `fetch_and_normalize_historical`.

Ninguno de los motores existentes (`run_analysis_engines`,
`analyze_financial_health`, `analyze_valuation`) se modificó.
`run_trend_analysis_engine` **todavía no se invoca** desde
`investigate`/`assemble_research_result`: su resultado no forma parte
hoy de ningún `ResearchResult` ensamblado. Esa incorporación, con manejo
de fallos parciales (serie histórica no disponible, error de
normalización) sin detener el resto del flujo, queda para la tarea
siguiente y separada de esta misma sección de `TASKS.md`.

Se agregó también `investmentops/tests/test_core_orchestrator_trend_analysis.py`,
cubriendo tanto el adaptador (`_trend_analysis_result_to_analysis_result`:
procedencia centinela, preservación de contenido, inmutabilidad) como
`run_trend_analysis_engine` (encadenado correcto, paso de `period`/
`limit`, propagación de `DataProviderError`, y equivalencia con invocar
`assemble_trend_analysis` directamente sobre la serie ya normalizada).

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (nuevas constantes
  `TREND_ANALYSIS_AI_PROVIDER`/`TREND_ANALYSIS_AI_MODEL`, nuevas
  funciones `_trend_analysis_result_to_analysis_result`/
  `run_trend_analysis_engine`, más imports de `AnalysisProvenance` y de
  `investmentops.analysis_engines.trends`; docstring del módulo
  actualizado)
- `TASKS.md` (tarea marcada como completada, con referencia a las
  funciones nuevas)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_core_orchestrator_trend_analysis.py`

No modificados: `investmentops/analysis_engines/trends.py`,
`investmentops/data_layer/normalization.py`,
`investmentops/data_providers/fundamentals.py`,
`investmentops/core/research_result.py`, ni ningún contrato de Fase
1/2, ni `ROADMAP.md`, `GOALS.md`, `ARCHITECTURE.md`.

## Próxima tarea recomendada

Fase 3, "Orquestador" → "Incluir el resultado de evolución de ingresos y
beneficios en el `ResearchResult` ensamblado, incluyendo el manejo de
fallos parciales (serie histórica no disponible, error de
normalización) sin detener el resto del flujo, siguiendo el mismo
criterio ya usado por `investigate` para los demás agentes."

Esta tarea consumirá `run_trend_analysis_engine` (recién implementada)
dentro de `investigate`, capturando `DataProviderError`/
`NormalizationError` de forma independiente a los demás agentes (mismo
patrón try/except ya usado para salud financiera/valoración) y
agregando el `AnalysisResult` resultante (o el `ResearchFailure`
correspondiente) a lo que ya ensambla `assemble_research_result`.