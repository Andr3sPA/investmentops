# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 6, "Diseño de estrategias" → "Para cada estrategia, definir de
forma breve qué datos del modelo de dominio utiliza y qué pregunta
responde." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/STRATEGY_DATA_MAPPING.md` (nuevo): tarea
de decisión/documentación, sin código. Sobre las tres estrategias ya
confirmadas en `STRATEGIES.md` (value, growth, calidad), fija para cada
una:

- **Value:** responde ¿está cara o barata en relación con sus propios
  fundamentales?, reutilizando `ValuationMetrics` (P/E, P/S) ya
  calculadas por `calculate_valuation_metrics` (Fase 1), con
  `FinancialHealthMetrics` como contexto adicional y los modelos
  `FinancialStatement`/`MarketData` normalizados como base.
- **Growth:** responde ¿cómo ha evolucionado el crecimiento y qué tan
  consistente es?, reutilizando íntegramente el resultado ya ensamblado
  por `assemble_trend_analysis` (Fase 3): tendencia agregada y variación
  periodo a periodo.
- **Calidad:** responde ¿qué tan sólida es la salud financiera
  subyacente?, reutilizando `FinancialHealthMetrics` (`net_margin`,
  `debt_to_revenue`) ya calculadas por `calculate_financial_health_metrics`
  (Fase 1), con `FinancialStatement` como base.

Se documenta explícitamente el principio común (ningún cálculo
determinístico nuevo: solo se reinterpretan, con marcos distintos,
métricas ya existentes) y se justifica por qué "calidad" no duplica al
agente de salud financiera de Fase 1 pese a compartir los mismos datos
de entrada: la diferencia vive en el prompt (marco de interpretación),
no en los datos ni en su cálculo.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/STRATEGY_DATA_MAPPING.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Escribir el archivo de prompt del agente de estrategia 'value' (fuera
  del código Python), indicando su marco de análisis y prohibiendo
  explícitamente cualquier recomendación de compra/venta o veredicto."