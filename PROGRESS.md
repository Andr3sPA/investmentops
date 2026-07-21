# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 4, "Orquestador" → "Registrar el nuevo motor de análisis sin
modificar los motores existentes" (TASKS.md).

### Qué se implementó

`run_news_relevance_engine`/`_news_relevance_result_to_analysis_result`
en `investmentops/core/orchestrator.py`, siguiendo exactamente el mismo
patrón ya usado por `run_trend_analysis_engine`/
`_trend_analysis_result_to_analysis_result` (Fase 3) y sobre la misma
justificación ya documentada en `investmentops/core/TREND_INTEGRATION.md`
(no hizo falta una nueva decisión de diseño: el problema —un resultado
de motor sin `AnalysisProvenance`— y su solución —una procedencia
centinela `ai_provider="none"`/`ai_model="deterministic"`— ya eran
idénticos):

- **`_news_relevance_result_to_analysis_result(news_result, ...)`**:
  convierte un `NewsRelevanceResult`
  (`investmentops.analysis_engines.news_relevance`, que no lleva
  `provenance` porque ese motor no invoca ningún proveedor de IA) en un
  `AnalysisResult` normal, con `AnalysisProvenance(ai_provider="none",
  ai_model="deterministic", generated_at=...)`.
- **`run_news_relevance_engine(ticker, ...)`**: encadena
  `fetch_and_normalize_news(ticker, ...)` (ya implementada) →
  `assemble_news_relevance_analysis(...)` (ya implementada) → la
  conversión centinela. Acepta `days`, `now` y `summary_max_length`,
  propagados tal cual a `assemble_news_relevance_analysis`. No captura
  `DataProviderError`/`NormalizationError`: las propaga tal cual, mismo
  criterio ya aplicado por `run_trend_analysis_engine`.

Se agregaron dos constantes nuevas, `NEWS_RELEVANCE_AI_PROVIDER = "none"`
y `NEWS_RELEVANCE_AI_MODEL = "deterministic"`, junto a las ya existentes
`TREND_ANALYSIS_AI_PROVIDER`/`TREND_ANALYSIS_AI_MODEL`.

No se modificó `run_analysis_engines`, `analyze_financial_health`,
`analyze_valuation`, `run_trend_analysis_engine` ni `investigate`:
incorporar el resultado de este motor al `ResearchResult` ensamblado
(con manejo de fallos parciales, siguiendo el mismo criterio ya usado
para el motor de tendencias) queda como la tarea siguiente y separada de
esta misma sección de `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_core_orchestrator_news_relevance.py`

Modificados:
- `investmentops/core/orchestrator.py` (agregado `run_news_relevance_engine`,
  `_news_relevance_result_to_analysis_result`, `NEWS_RELEVANCE_AI_PROVIDER`,
  `NEWS_RELEVANCE_AI_MODEL`, e imports de `news_relevance`; ninguna
  función existente cambió su comportamiento)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Orquestador" → "Incluir el nuevo resultado en el 'Resultado de
investigación'."