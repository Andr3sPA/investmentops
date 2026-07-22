# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Orquestador y CLI" → "Registrar el nuevo proveedor de
comparables sin modificar los proveedores existentes." (TASKS.md).

### Qué se implementó

`fetch_raw_comparables_data`/`fetch_and_normalize_comparables` en
`investmentops/core/orchestrator.py`, siguiendo exactamente el mismo
patrón de dos capas ya usado por `fetch_raw_news_data`/
`fetch_and_normalize_news` (Fase 4) y `fetch_raw_historical_data`/
`fetch_and_normalize_historical` (Fase 3):

- `fetch_raw_comparables_data(ticker, ...)`: dispara la consulta a
  `FMPComparablesProvider.fetch(ticker)`. Por defecto construye un
  `FMPComparablesProvider`, acepta un `provider` inyectado para pruebas.
- `fetch_and_normalize_comparables(ticker, ...)`: encadena ese resultado
  con `investmentops.data_layer.normalization.comparables_from_raw`,
  obteniendo las cifras normalizadas de cada empresa par reutilizando
  —sin modificarlas— `fetch_peer_tickers`/`fetch_peer_key_metrics`, ya
  implementadas en la tarea "Fuente de datos de comparables" de esta
  misma fase. Devuelve un `Comparables` completo, listo para que el
  motor de posicionamiento relativo (`calculate_relative_positioning`)
  lo consuma.

Ninguna de las dos funciones captura `DataProviderError`/
`NormalizationError`: las propaga tal cual, mismo criterio ya aplicado
por el resto de funciones `fetch_raw_*`/`fetch_and_normalize_*`. No se
modificó `FMPComparablesProvider`, `fetch_peer_tickers`,
`fetch_peer_key_metrics` ni ninguna otra función ya existente.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (import de `Comparables` y
  `comparables_from_raw`; se agregaron `fetch_raw_comparables_data` y
  `fetch_and_normalize_comparables`, insertadas después de
  `fetch_peer_key_metrics`; sin cambios en el resto del módulo)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Orquestador y CLI":
- "Registrar el nuevo motor de posicionamiento relativo sin modificar
  los motores existentes." Implementación de código: siguiendo el mismo
  patrón ya usado por `run_trend_analysis_engine`/
  `_trend_analysis_result_to_analysis_result` (Fase 3) y
  `run_news_relevance_engine`/`_news_relevance_result_to_analysis_result`
  (Fase 4), añadir `run_comparables_engine`/
  `_comparables_analysis_result_to_analysis_result` en
  `investmentops/core/orchestrator.py`, encadenando
  `fetch_and_normalize` (empresa investigada) + 
  `fetch_and_normalize_comparables` (ya implementada) →
  `calculate_relative_positioning` → `assemble_comparables_analysis` →
  conversión a `AnalysisResult` con procedencia centinela
  (`ai_provider="none"`, `ai_model="deterministic"`), sin modificar
  ningún motor existente.