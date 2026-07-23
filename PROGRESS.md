# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Escribir el archivo de
prompt del agente de estrategia 'growth' (fuera del código Python),
indicando su marco de análisis y prohibiendo explícitamente cualquier
recomendación de compra/venta o veredicto." (TASKS.md).

### Qué se implementó

`prompts/growth.md` (nuevo): prompt del agente de estrategia "growth",
siguiendo el mismo patrón ya usado por `prompts/value.md`. Sobre el
mapeo de datos ya fijado en `STRATEGY_DATA_MAPPING.md`, instruye al
modelo a:

- Interpretar (nunca recalcular) `revenue_trend`/`net_income_trend`
  (tendencia agregada) y `revenue_growth_by_period`/
  `net_income_growth_by_period` (variación por periodo), ambos ya
  producidos por `assemble_trend_analysis` (Fase 3).
- Relacionar ingresos y beneficios entre sí cuando aporte contexto.
- Declarar explícitamente cuando la tendencia viene como `null` (datos
  insuficientes) o cuando hay advertencias de huecos irregulares en la
  serie, sin inventar ni corregir nada.
- No calcular ninguna cifra nueva (tasas compuestas, proyecciones,
  promedios no entregados).
- No comparar con otras empresas/sector (fuera de alcance).
- No emitir ninguna recomendación de compra/venta ni veredicto de
  inversión, y presentar la lectura como una perspectiva entre varias
  (value, calidad), no como una evaluación general.

Solo el archivo de prompt: no se tocó ningún código Python. La
invocación al proveedor de IA para este agente es la tarea siguiente de
esta misma sección.

## Archivos creados o modificados

Creados:
- `prompts/growth.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Implementar la invocación al proveedor de IA configurado para el
  agente 'growth', enviando los datos normalizados ya existentes junto
  con el prompt."