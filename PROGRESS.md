# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Implementar el parseo de
la respuesta del modelo al resultado estructurado del agente 'value'
(hallazgos, procedencia de IA, dejando explícito que es una lectura
desde un marco particular, no un veredicto)." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/value.py` (extendido): se agregan
`FRAMEWORK_LIMITATION`, `parse_value_response(response,
valuation_metrics, health_metrics) -> AnalysisResult` y
`analyze_value(market_data, statement, valuation_metrics=None,
health_metrics=None, *, config=None) -> AnalysisResult`, siguiendo
exactamente el mismo patrón ya usado por
`parse_financial_health_response`/`parse_valuation_response` (Fase 1):

- `analysis_id`: siempre `"value"`.
- `findings`: `[response.content]`, sin reformatear.
- `supporting_metrics`: `price_to_earnings`/`price_to_sales`
  (`ValuationMetrics`) y `net_margin`/`debt_to_revenue`
  (`FinancialHealthMetrics`), tomados directamente de las métricas ya
  calculadas, nunca del texto del modelo.
- `limitations`: siempre incluye `FRAMEWORK_LIMITATION` primero — la
  limitación explícita que exige la tarea, declarando que la
  interpretación corresponde únicamente al marco de value investing, no
  a una evaluación general ni a un veredicto de inversión — seguida de
  cualquier advertencia de `valuation_metrics.warnings`/
  `health_metrics.warnings`.
- `provenance`: construida desde los metadatos que ya entrega el
  proveedor de IA (`response.provider`/`response.model`/
  `response.generated_at`).

`analyze_value` encadena `calculate_valuation_metrics`/
`calculate_financial_health_metrics` (si no se pasan ya calculadas) →
`invoke_value_agent` (ya implementada) → `parse_value_response`, mismo
patrón que `analyze_financial_health`/`analyze_valuation`.

## Archivos creados o modificados

Modificados:
- `investmentops/analysis_engines/value.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_analysis_engines_value_parse.py`

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Escribir el archivo de prompt del agente de estrategia 'growth'
  (fuera del código Python), indicando su marco de análisis y
  prohibiendo explícitamente cualquier recomendación de compra/venta o
  veredicto."