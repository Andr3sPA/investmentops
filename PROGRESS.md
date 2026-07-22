# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Motor de análisis: posicionamiento relativo" → "Implementar el
cálculo de la posición relativa de la empresa frente a sus pares en cada
métrica." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/comparables.py` (nuevo), sobre la
decisión ya tomada en `COMPARABLES_METRICS.md`:

- `calculate_entity_metrics(ticker, financial_statement, market_data)`:
  calcula las cuatro métricas ya decididas (`net_margin`,
  `debt_to_revenue`, `price_to_earnings`, `price_to_sales`) para una
  empresa (investigada o par), reutilizando sin duplicarlas
  `calculate_financial_health_metrics`/`calculate_valuation_metrics`
  (Fase 1), y agrega las advertencias de ambos cálculos.
- `compare_metric(company_value, peer_value)`: compara el valor de una
  métrica de la empresa investigada contra un par
  (`"por_encima"`/`"por_debajo"`/`"igual"`), devolviendo `None` sin
  inventar una posición si alguno de los dos valores no fue calculable.
- `calculate_relative_positioning(company_ticker, company_financial_statement,
  company_market_data, comparables)`: calcula las métricas de la empresa
  investigada y de cada `PeerComparable` de un `Comparables` ya
  normalizado, y produce, por cada una de las cuatro métricas, una
  comparación contra cada par, en el mismo orden en que ya vienen los
  pares (sin reordenar). Maneja sin error el caso de una empresa sin
  pares (`Comparables.peers == []`).

Ninguna de las funciones invoca ningún proveedor de IA: es un cálculo
puramente determinístico, consistente con el principio ya aplicado por
los motores de tendencia y noticias relevantes.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/comparables.py`
- `investmentops/tests/test_analysis_engines_comparables.py`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Motor de análisis: posicionamiento relativo":
- "Ensamblar el resultado estructurado del motor (hallazgos, tabla
  comparativa, advertencias si faltan datos de algún par)." Implementación
  de código: encadenar `calculate_relative_positioning` (ya implementada)
  en un resultado estructurado (hallazgos en lenguaje natural generados
  por plantilla determinista, tabla comparativa a partir de
  `RelativePositioning.comparisons`, y advertencias — incluyendo la
  limitación explícita de "crecimiento" ya documentada en
  `COMPARABLES_METRICS.md` y cualquier advertencia por métrica no
  calculable de algún par), siguiendo el mismo patrón ya usado por
  `assemble_trend_analysis`/`TrendAnalysisResult` (Fase 3) y
  `assemble_news_relevance_analysis`/`NewsRelevanceResult` (Fase 4): este
  motor tampoco invoca IA, por lo que no usará `AnalysisResult`/
  `AnalysisProvenance` directamente.