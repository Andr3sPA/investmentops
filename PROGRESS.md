# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Orquestador y CLI" → "Registrar el nuevo motor de
posicionamiento relativo sin modificar los motores existentes."
(TASKS.md).

### Qué se implementó

`run_comparables_engine`/`_comparables_analysis_result_to_analysis_result`
en `investmentops/core/orchestrator.py`, siguiendo exactamente el mismo
patrón ya usado por `run_trend_analysis_engine`/
`_trend_analysis_result_to_analysis_result` (Fase 3) y
`run_news_relevance_engine`/`_news_relevance_result_to_analysis_result`
(Fase 4):

- `_comparables_analysis_result_to_analysis_result(...)`: envuelve un
  `ComparablesAnalysisResult` (que no lleva `provenance`, ya que el
  motor de posicionamiento relativo no invoca ningún proveedor de IA) en
  un `AnalysisResult` normal, con una `AnalysisProvenance` centinela
  (`ai_provider="none"`, `ai_model="deterministic"`), reutilizando sin
  cambios la decisión ya documentada en
  `investmentops/core/TREND_INTEGRATION.md`.
- `run_comparables_engine(ticker, ...)`: encadena `fetch_and_normalize`
  (empresa investigada) + `fetch_and_normalize_comparables` (ya
  implementada en la tarea anterior de esta misma fase) →
  `calculate_relative_positioning` → `assemble_comparables_analysis`
  (ambas ya implementadas en
  `investmentops.analysis_engines.comparables`) → la conversión
  centinela.

Se agregaron también las constantes `COMPARABLES_AI_PROVIDER` (`"none"`)
y `COMPARABLES_AI_MODEL` (`"deterministic"`).

No se modificó `run_analysis_engines`, `run_trend_analysis_engine`,
`run_news_relevance_engine` ni `investigate`: este motor todavía no se
invoca desde el flujo de investigación de una sola empresa — su
incorporación al `ResearchResult` (individual o comparativo) corresponde
a las tareas siguientes de esta misma sección ("Diseñar la sintaxis del
nuevo comando CLI para comparar dos o más empresas...").

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (import de
  `investmentops.analysis_engines.comparables`; se agregaron
  `COMPARABLES_AI_PROVIDER`/`COMPARABLES_AI_MODEL`,
  `_comparables_analysis_result_to_analysis_result` y
  `run_comparables_engine`, insertadas después de
  `fetch_and_normalize_comparables`; sin cambios en el resto del módulo)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Orquestador y CLI":
- "Diseñar la sintaxis del nuevo comando CLI para comparar dos o más
  empresas directamente." Tarea de diseño/documentación (no de código):
  fijar cómo se invocará el nuevo subcomando de comparación (ej.
  `python -m investmentops compare TICKER1 TICKER2 [...]`), antes de
  implementar su parseo de argumentos (tarea siguiente y separada de la
  misma sección).