# investmentops/analysis_engines/STRATEGY_DATA_MAPPING.md
# Lecturas por estrategia de inversión — datos y pregunta por estrategia (Fase 6)

Cubre la tarea "Para cada estrategia, definir de forma breve qué datos
del modelo de dominio utiliza y qué pregunta responde" (TASKS.md, Fase
6, "Diseño de estrategias"), sobre las tres estrategias ya confirmadas
en `investmentops/analysis_engines/STRATEGIES.md` (value, growth,
calidad).

Esta tarea es de **diseño/documentación**, no de código: fija, para cada
estrategia, qué modelos de dominio y qué métricas ya existentes
consumirá (sin ningún cálculo determinístico nuevo, conforme a
`ROADMAP.md`: *"interpretan datos ya existentes, sin nuevas fuentes"*) y
qué pregunta de investigación responde, antes de escribir su prompt
(tareas siguientes de esta misma sección, "Motores de análisis por
estrategia").

## Principio común: ningún cálculo nuevo, solo reinterpretación

Ninguna de las tres estrategias introduce una métrica, un modelo de
dominio o una fuente de datos nueva. Todas reutilizan, tal cual, lo ya
calculado de forma determinística por los motores existentes
(`calculate_financial_health_metrics`, `calculate_valuation_metrics`,
`assemble_trend_analysis`): lo que cambia entre estrategias es
exclusivamente el **marco de interpretación** que aplicará el modelo de
lenguaje sobre esos mismos números (su prompt), no los datos ni su
cálculo. Esto es coherente con el patrón ya usado por salud
financiera/valoración (Fase 1): el cálculo vive en código, la
interpretación vive en el modelo de lenguaje guiado por un prompt.

## Value (`value`)

- **Pregunta que responde:** ¿Está la empresa "cara" o "barata" en
  relación con sus propios fundamentales, desde el marco de análisis de
  valor?
- **Datos que utiliza:**
  - `ValuationMetrics` (`price_to_earnings`, `price_to_sales`), ya
    calculadas por `calculate_valuation_metrics`
    (`investmentops.analysis_engines.valuation`, Fase 1).
  - `FinancialHealthMetrics` (`net_margin`, `debt_to_revenue`), ya
    calculadas por `calculate_financial_health_metrics`
    (`investmentops.analysis_engines.financial_health`, Fase 1), como
    contexto adicional: un múltiplo bajo junto a fundamentales sólidos
    se lee de forma distinta que un múltiplo bajo junto a fundamentales
    débiles.
  - `FinancialStatement`/`MarketData` normalizados (para que el prompt
    tenga las cifras base, no solo los ratios ya derivados), mismo
    criterio ya usado en `invoke_valuation_agent`.
- **Qué NO utiliza:** la serie histórica (`FinancialStatementSeries`,
  `TrendAnalysisResult`) ni los datos de comparables (`Comparables`): el
  marco de valor de este MVP se centra en la relación precio/fundamento
  de la propia empresa en su corte más reciente, no en su evolución en
  el tiempo ni en su comparación con pares (esas dos lecturas ya existen
  por separado como sus propios motores, Fases 3 y 5).

## Growth (`growth`)

- **Pregunta que responde:** ¿Cómo ha evolucionado el crecimiento de
  ingresos y beneficios en el tiempo, y qué tan consistente es esa
  tendencia?
- **Datos que utiliza:**
  - El resultado ya ensamblado por `assemble_trend_analysis`
    (`investmentops.analysis_engines.trends`, Fase 3):
    `revenue_trend`/`net_income_trend` (tendencia agregada:
    creciente/decreciente/estable/mixta) y
    `revenue_growth_by_period`/`net_income_growth_by_period` (variación
    periodo a periodo), ya calculados de forma determinística.
- **Qué NO utiliza:** múltiplos de valoración (`ValuationMetrics`) ni
  ratios de salud financiera de corte único (`FinancialHealthMetrics`):
  el marco de growth de este MVP se centra exclusivamente en la
  trayectoria en el tiempo, no en si la empresa está cara/barata hoy
  (value) ni en su solidez financiera puntual (calidad) — esas
  distinciones son justamente lo que hace a las tres lecturas
  contrastables entre sí, conforme a `GOALS.md`.

## Calidad (`quality`)

- **Pregunta que responde:** ¿Qué tan sólida es la salud financiera
  subyacente de la empresa (rentabilidad, nivel de endeudamiento),
  independientemente de su valoración actual o de su ritmo de
  crecimiento?
- **Datos que utiliza:**
  - `FinancialHealthMetrics` (`net_margin`, `debt_to_revenue`), ya
    calculadas por `calculate_financial_health_metrics`
    (`investmentops.analysis_engines.financial_health`, Fase 1) — las
    mismas dos métricas ya usadas por el agente de salud financiera de
    Fase 1, pero interpretadas aquí bajo un marco distinto (calidad del
    negocio como estilo de inversión, no un diagnóstico financiero
    genérico).
  - `FinancialStatement` normalizado, como contexto base (mismo criterio
    ya usado por `invoke_financial_health_agent`).
- **Qué NO utiliza:** múltiplos de valoración ni la serie histórica: el
  marco de calidad de este MVP evalúa solidez financiera puntual, no
  precio (value) ni evolución en el tiempo (growth).

## Por qué "calidad" y "salud financiera" (Fase 1) no son redundantes

Ambas comparten los mismos datos de entrada (`FinancialHealthMetrics`),
pero no son la misma lectura: el agente de salud financiera (Fase 1)
responde una pregunta general y neutral ("¿esta empresa está
financieramente sana?", `GOALS.md`, pregunta 1), mientras que el agente
de calidad (Fase 6) enmarca esos mismos números explícitamente dentro
del estilo de inversión "quality investing" (qué tan atractivo es el
negocio como candidato de calidad para un inversionista que prioriza esa
característica sobre precio o crecimiento). La diferencia vive
enteramente en el prompt de cada agente (marco de interpretación), no en
los datos ni en su cálculo — mismo principio ya fijado en la sección
"Principio común" de este documento.

## Resumen

| Estrategia | Pregunta                                                                 | Datos/métricas reutilizados                                                                 |
|------------|---------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| Value      | ¿Está cara o barata en relación con sus propios fundamentales?            | `ValuationMetrics` (P/E, P/S) + `FinancialHealthMetrics` (contexto) + `FinancialStatement`/`MarketData` |
| Growth     | ¿Cómo ha evolucionado su crecimiento y qué tan consistente es?            | Resultado de `assemble_trend_analysis` (tendencia agregada + variación por periodo)             |
| Calidad    | ¿Qué tan sólida es su salud financiera subyacente?                        | `FinancialHealthMetrics` (net_margin, debt_to_revenue) + `FinancialStatement`                   |

## Fuera de alcance de esta tarea

- El contenido de los prompts de cada estrategia (tareas separadas y
  posteriores, "Motores de análisis por estrategia").
- La invocación al proveedor de IA y el parseo de la respuesta de cada
  estrategia (tareas separadas y posteriores de la misma sección).
- Cualquier cálculo determinístico nuevo: como ya señala el "Principio
  común" de este documento, ninguna estrategia lo requiere.