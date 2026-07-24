# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Implementar el parseo de
la respuesta del modelo al resultado estructurado del agente 'calidad'
(hallazgos, procedencia de IA, dejando explícito que es una lectura
desde un marco particular, no un veredicto)." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/quality.py` (modificado): se agregaron
`FRAMEWORK_LIMITATION`, `parse_quality_response(response, health_metrics)`
y `analyze_quality(statement, health_metrics=None, *, config=None)`.
Sigue exactamente el mismo patrón ya usado por `parse_value_response`/
`analyze_value` (`investmentops.analysis_engines.value`) y
`parse_growth_response`/`analyze_growth`
(`investmentops.analysis_engines.growth`):

- `parse_quality_response` empaqueta `response.content` como único
  hallazgo, adjunta las `FinancialHealthMetrics` ya calculadas
  (`net_margin`, `debt_to_revenue`) como `supporting_metrics` sin
  recalcularlas ni derivarlas del texto del modelo, declara siempre
  `FRAMEWORK_LIMITATION` (primero en la lista de limitaciones) seguida
  de cualquier advertencia de `health_metrics.warnings`, y construye la
  `AnalysisProvenance` a partir de los metadatos del proveedor de IA.
- `FRAMEWORK_LIMITATION` deja explícito que esta interpretación
  corresponde exclusivamente al marco de quality investing: no es un
  veredicto, no es una evaluación general de la empresa, no equivale a
  otras lecturas por estrategia (value, growth) ni al diagnóstico
  general de salud financiera ya presentado en otra sección del
  reporte (Fase 1).
- `analyze_quality` encadena `calculate_financial_health_metrics` (si no
  se pasa ya calculada) → `invoke_quality_agent` (ya existente) →
  `parse_quality_response`, sin traducir las excepciones que pueda
  levantar (`PromptError`, `AgentProviderSelectionError`,
  `AIProviderError`): esa integración corresponde a la tarea de
  "Orquestador" de esta misma fase, todavía pendiente.

Se agregó `investmentops/tests/test_analysis_engines_quality_parse.py`,
siguiendo el mismo patrón de pruebas ya usado en
`test_analysis_engines_value_parse.py`/`test_analysis_engines_growth_parse.py`.

## Archivos creados o modificados

Modificados:
- `investmentops/analysis_engines/quality.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_analysis_engines_quality_parse.py`

## Próxima tarea recomendada

Fase 6, "Orquestador":
- "Registrar los nuevos motores de estrategia sin modificar los motores
  existentes."