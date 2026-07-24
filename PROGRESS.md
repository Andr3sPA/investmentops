# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Orquestador" → "Registrar los nuevos motores de estrategia sin
modificar los motores existentes." (TASKS.md).

### Qué se implementó

`investmentops/core/orchestrator.py` (modificado): se agregaron tres
funciones nuevas, `run_value_engine`, `run_growth_engine` y
`run_quality_engine`, siguiendo el mismo patrón ya usado por
`run_trend_analysis_engine`/`run_news_relevance_engine`/
`run_comparables_engine` (Fases 3-5): cada una encadena la obtención y
normalización de datos ya existente con el agente de estrategia
correspondiente (Fase 6).

Diferencia clave respecto a los motores anteriores: `analyze_value`/
`analyze_growth`/`analyze_quality` ya invocan un proveedor de IA real y
devuelven un `AnalysisResult` con `AnalysisProvenance` genuina (no
determinística/centinela), por lo que ninguno de los tres wrappers
necesita una función `_*_to_analysis_result` adicional — simplemente
propagan el resultado ya completo de `analyze_*`.

- `run_value_engine(ticker, ...)`: `fetch_and_normalize` →
  `analyze_value(market_data, financial_statement, ...)`.
- `run_growth_engine(ticker, ..., period="annual", limit=5)`:
  `fetch_and_normalize_historical` → `analyze_growth(series, ...)`.
- `run_quality_engine(ticker, ...)`: `fetch_and_normalize` →
  `analyze_quality(financial_statement, ...)`.

Ninguna de las tres captura excepciones de las funciones que invoca
(`DataProviderError`, `NormalizationError`, `PromptError`,
`AgentProviderSelectionError`, `AIProviderError`): las propagan tal
cual, mismo criterio ya aplicado por los demás `run_*_engine`. Ninguna
se invoca todavía desde `investigate`/`assemble_research_result`: esa
incorporación al `ResearchResult`, con manejo de fallos parciales, es
la tarea siguiente y separada de esta misma sección ("Incluir los
resultados de cada estrategia en el 'Resultado de investigación' como
entradas independientes y contrastables"). No se modificó
`run_analysis_engines`, `run_trend_analysis_engine`,
`run_news_relevance_engine` ni `run_comparables_engine`.

Se agregó `investmentops/tests/test_core_orchestrator_strategies.py`.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_core_orchestrator_strategies.py`

## Próxima tarea recomendada

Fase 6, "Orquestador":
- "Incluir los resultados de cada estrategia en el 'Resultado de
  investigación' como entradas independientes y contrastables."