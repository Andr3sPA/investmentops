# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Motor de análisis: posicionamiento relativo" → "Definir qué
métricas clave se comparan lado a lado (ej. valoración, márgenes,
crecimiento)." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/COMPARABLES_METRICS.md` (nuevo),
siguiendo el mismo patrón ya usado por `FINANCIAL_HEALTH_METRICS.md`/
`VALUATION_METRICS.md`/`TREND_METRICS.md`/`NEWS_RELEVANCE.md`: una tarea
de diseño/documentación, sin código.

Decisión: el motor de posicionamiento relativo comparará cuatro métricas
ya definidas y calculadas en Fase 1, reutilizadas sin duplicar código:

- `net_margin` y `debt_to_revenue`, vía `calculate_financial_health_metrics`
  (`investmentops/analysis_engines/financial_health.py`).
- `price_to_earnings` y `price_to_sales`, vía `calculate_valuation_metrics`
  (`investmentops/analysis_engines/valuation.py`).

Ambas funciones ya existentes se aplicarán tanto a la empresa investigada
como a cada `PeerComparable` (que expone los mismos `FinancialStatement`/
`MarketData` ya normalizados que la propia empresa), sin necesidad de
ninguna función de cálculo nueva.

"Crecimiento" (mencionado como ejemplo en `TASKS.md`) se descarta
explícitamente para el MVP: requeriría una serie histórica por empresa
par, que `Comparables`/`PeerComparable` no expone (solo un único corte
por diseño, ver `investmentops/data_layer/comparables.py`), y no existe
hoy ninguna fuente de datos que obtenga series históricas para empresas
pares (`fetch_historical` solo se invoca para la empresa investigada).
Se documenta como limitación explícita a declarar por el futuro motor,
en vez de aproximarla con datos que no le corresponden — mismo criterio
ya aplicado repetidamente en el proyecto (liquidez en Fase 1, P/B y
EV/EBITDA en Fase 1, entre otros).

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/COMPARABLES_METRICS.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Motor de análisis: posicionamiento relativo":
- "Implementar el cálculo de la posición relativa de la empresa frente a
  sus pares en cada métrica." Implementación de código: calcular, para
  la empresa investigada y para cada par, las cuatro métricas ya
  decididas en `COMPARABLES_METRICS.md` (reutilizando
  `calculate_financial_health_metrics`/`calculate_valuation_metrics` sin
  duplicarlas), y determinar la posición relativa de la empresa
  investigada frente a cada par en cada métrica (ej. por encima/por
  debajo, o el valor numérico de cada uno lado a lado).