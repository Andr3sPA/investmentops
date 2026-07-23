# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Escribir el archivo de
prompt del agente de estrategia 'value' (fuera del código Python),
indicando su marco de análisis y prohibiendo explícitamente cualquier
recomendación de compra/venta o veredicto." (TASKS.md).

### Qué se implementó

`prompts/value.md` (nuevo): prompt del agente de estrategia value
investing, siguiendo el mismo patrón ya usado por
`prompts/financial_health.md`/`prompts/valuation.md`. Sobre el mapeo de
datos ya fijado en `STRATEGY_DATA_MAPPING.md` (Fase 6, "Diseño de
estrategias"):

- Instruye a interpretar `price_to_earnings`/`price_to_sales` (ya
  calculados de forma determinística, nunca recalculados por el
  modelo), usando `net_margin`/`debt_to_revenue` como contexto de
  calidad del negocio detrás del precio.
- Enmarca explícitamente la lectura como una perspectiva de value
  investing entre varias posibles (no una evaluación general de la
  empresa), consistente con `GOALS.md` ("opiniones contrastables entre
  sí, no como una única verdad").
- Declara honestamente las ausencias de datos (P/E no calculable,
  comparables no disponibles en esta fase) sin inventar cifras ni
  aproximaciones.
- Prohíbe explícitamente cualquier recomendación de compra/venta o
  veredicto de inversión, mismo criterio ya aplicado en los prompts de
  salud financiera y valoración.

Solo el prompt (archivo de texto, fuera del código Python); la
invocación al proveedor de IA y el parseo de su respuesta son las dos
tareas siguientes y separadas de la misma sección.

## Archivos creados o modificados

Creados:
- `prompts/value.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Implementar la invocación al proveedor de IA configurado para el
  agente 'value', enviando los datos normalizados ya existentes (sin
  nuevas fuentes ni cálculos adicionales) junto con el prompt."