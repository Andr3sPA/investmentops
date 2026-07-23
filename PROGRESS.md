# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 6, "Diseño de estrategias" → "Listar las estrategias/escuelas de
inversión a cubrir en el MVP (ej. value, growth, calidad)." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/STRATEGIES.md` (nuevo): tarea de
decisión/documentación, sin código. Confirma las **tres** estrategias ya
anticipadas en el desglose original de `TASKS.md` para "Motores de
análisis por estrategia" — **value**, **growth** y **calidad** — sin
agregar ni quitar ninguna.

Justificación documentada: las tres son implementables reutilizando
exclusivamente modelos de dominio y métricas ya normalizados/calculados
en fases anteriores (`FinancialStatement`, `MarketData`,
`FinancialStatementSeries`, `calculate_financial_health_metrics`,
`calculate_valuation_metrics`, `assemble_trend_analysis`), sin ninguna
fuente de datos nueva, conforme a `ROADMAP.md` ("consumiendo el mismo
modelo de dominio ya existente"); y cubren ángulos claramente distintos
entre sí (¿está cara o barata? / ¿cómo evoluciona en el tiempo? / ¿qué
tan sólida es, independientemente del precio o crecimiento?), conforme
al principio de `GOALS.md` de presentar "opiniones contrastables entre
sí, no como una única verdad".

El documento deja explícitamente fuera de alcance (para la tarea
siguiente, ya pendiente en la misma sección) qué datos concretos del
modelo de dominio usa cada estrategia y qué pregunta responde, así como
el contenido de los prompts y cualquier cálculo determinístico nuevo
(`ROADMAP.md` ya aclara que estos motores no necesitan nuevas fuentes de
datos).

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/STRATEGIES.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Diseño de estrategias":
- "Para cada estrategia, definir de forma breve qué datos del modelo de
  dominio utiliza y qué pregunta responde." — sobre las tres estrategias
  ya confirmadas en `investmentops/analysis_engines/STRATEGIES.md`
  (value, growth, calidad).