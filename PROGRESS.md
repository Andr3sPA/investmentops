# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Escribir el archivo de
prompt del agente de estrategia 'calidad' (fuera del código Python),
indicando su marco de análisis y prohibiendo explícitamente cualquier
recomendación de compra/venta o veredicto." (TASKS.md).

### Qué se implementó

`prompts/quality.md` (nuevo). Sigue el mismo patrón ya usado por
`prompts/value.md`/`prompts/growth.md` (Fase 6): instruye al modelo a
interpretar, sin recalcular, `net_margin`/`debt_to_revenue` (ya
calculadas por `calculate_financial_health_metrics`, Fase 1) junto con
`FinancialStatement` normalizado como contexto, sobre el mapeo de datos
ya fijado en `STRATEGY_DATA_MAPPING.md` (¿qué tan sólida es la salud
financiera subyacente?). Enmarca explícitamente la lectura como una
perspectiva de "quality investing", distinta del diagnóstico general ya
producido por el agente de salud financiera de Fase 1 (misma
distinción ya documentada en `STRATEGY_DATA_MAPPING.md`, "Por qué
'calidad' y 'salud financiera' no son redundantes"): la diferencia vive
en el marco de interpretación del prompt, no en los datos ni su
cálculo. Declara explícitamente la limitación de liquidez ya conocida
desde Fase 1 (el modelo de dominio no expone activos/pasivos
corrientes) y prohíbe cualquier recomendación de compra/venta o
veredicto de inversión.

Solo se agregó el archivo de prompt; no se tocó ningún módulo Python.
La invocación al proveedor de IA para este agente y el parseo de su
respuesta son las dos tareas siguientes y separadas de esta misma
sección.

## Archivos creados o modificados

Creados:
- `prompts/quality.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Implementar la invocación al proveedor de IA configurado para el
  agente 'calidad', enviando los datos normalizados ya existentes
  junto con el prompt."