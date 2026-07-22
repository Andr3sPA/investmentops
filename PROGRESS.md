# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Motor de análisis: posicionamiento relativo" → "Ensamblar el
resultado estructurado del motor (hallazgos, tabla comparativa,
advertencias si faltan datos de algún par)." (TASKS.md).

### Qué se implementó

`assemble_comparables_analysis`/`ComparablesAnalysisResult` en
`investmentops/analysis_engines/comparables.py`, sobre las piezas ya
implementadas (`calculate_relative_positioning`) y sobre el mismo patrón
ya usado por `assemble_trend_analysis`/`TrendAnalysisResult` (Fase 3) y
`assemble_news_relevance_analysis`/`NewsRelevanceResult` (Fase 4):

- `findings`: un hallazgo por métrica (`net_margin`, `debt_to_revenue`,
  `price_to_earnings`, `price_to_sales`), generado por plantilla
  determinista, indicando cuántos pares quedan por encima/por debajo/
  igual y cuántas comparaciones no fueron posibles por falta de datos.
  Si la empresa no tiene pares, un único hallazgo explícito.
- `supporting_metrics`: las cuatro métricas de la empresa investigada y
  la tabla comparativa completa (`comparisons`), un `dict` por par y
  métrica con `peer_ticker`/`company_value`/`peer_value`/`position`.
- `limitations`: siempre incluye `GROWTH_LIMITATION` (limitación
  explícita de crecimiento, ya decidida en `COMPARABLES_METRICS.md`),
  `NO_PEERS_LIMITATION` si `positioning.peers` está vacío, y cualquier
  advertencia de `calculate_entity_metrics` (empresa investigada y cada
  par, identificando el ticker del par afectado en el propio texto).

`ComparablesAnalysisResult` no lleva `provenance`: este motor no invoca
ningún proveedor de IA, mismo criterio ya justificado y reutilizado sin
una nueva decisión de diseño (el problema y su solución ya son idénticos
a los de tendencia/noticias relevantes).

## Archivos creados o modificados

Modificados:
- `investmentops/analysis_engines/comparables.py` (se agregaron
  `AGENT_ID`, `GROWTH_LIMITATION`, `NO_PEERS_LIMITATION`,
  `ComparablesAnalysisResult`, `_describe_metric_positioning`,
  `assemble_comparables_analysis`; sin cambios en el código ya existente
  de `calculate_entity_metrics`/`compare_metric`/
  `calculate_relative_positioning`)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Orquestador y CLI":
- "Registrar el nuevo proveedor de comparables sin modificar los
  proveedores existentes." Implementación de código: siguiendo el mismo
  patrón ya usado por `fetch_raw_news_data`/`fetch_and_normalize_news`
  (Fase 4), añadir al orquestador la pieza que registra el uso de
  `FMPComparablesProvider` (o de `fetch_peer_tickers`/
  `fetch_peer_key_metrics`, ya existentes desde la tarea de "Fuente de
  datos de comparables") sin modificar ningún proveedor ya existente.