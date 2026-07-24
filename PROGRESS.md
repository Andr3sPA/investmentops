# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Implementar el parseo de
la respuesta del modelo al resultado estructurado del agente 'growth'
(hallazgos, procedencia de IA, dejando explícito que es una lectura
desde un marco particular, no un veredicto)." (TASKS.md).

### Qué se implementó

`parse_growth_response`/`analyze_growth`/`FRAMEWORK_LIMITATION` en
`investmentops/analysis_engines/growth.py` (agregados al módulo ya
existente). Mismo patrón ya usado por `parse_value_response`/
`analyze_value` (Fase 6, estrategia "value"):

- `parse_growth_response(response, trend_result)` traduce el
  `AIProviderResponse` crudo (más el `TrendAnalysisResult` ya calculado)
  a un `AnalysisResult`: `analysis_id="growth"`, `findings=[response.content]`,
  `supporting_metrics` con las cuatro claves ya calculadas por
  `assemble_trend_analysis` (`revenue_trend`, `net_income_trend`,
  `revenue_growth_by_period`, `net_income_growth_by_period`), `limitations`
  con `FRAMEWORK_LIMITATION` (siempre primero) seguida de cualquier
  advertencia ya producida por `assemble_trend_analysis`
  (`trend_result.limitations`), y `provenance` construida desde los
  metadatos del proveedor de IA.
- `FRAMEWORK_LIMITATION` declara explícitamente que la lectura
  corresponde solo al marco de growth investing, no a una evaluación
  general ni a un veredicto — mismo criterio ya usado por
  `value.FRAMEWORK_LIMITATION`.
- `analyze_growth(series, trend_result=None, *, config=None)` encadena
  `assemble_trend_analysis` (si no se pasa ya calculado) →
  `invoke_growth_agent` → `parse_growth_response`, análoga a
  `analyze_value`.

No se modificó `invoke_growth_agent`, `trends.py`, `value.py` ni ningún
otro motor existente.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_analysis_engines_growth_parse.py`

Modificados:
- `investmentops/analysis_engines/growth.py` (se agregó `parse_growth_response`,
  `analyze_growth`, `FRAMEWORK_LIMITATION`, y las importaciones/docstring
  correspondientes)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Escribir el archivo de prompt del agente de estrategia 'calidad'
  (fuera del código Python), indicando su marco de análisis y
  prohibiendo explícitamente cualquier recomendación de compra/venta o
  veredicto."