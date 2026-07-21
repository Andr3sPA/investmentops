# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Fuente de datos de comparables" → "Implementar la consulta de
métricas clave (las ya normalizadas en fases previas) para cada empresa
par" (TASKS.md).

### Qué se implementó

`PeerMetrics`, `fetch_peer_tickers` y `fetch_peer_key_metrics` en
`investmentops/core/orchestrator.py` (nuevos).

- `fetch_peer_tickers(ticker, ...)`: consulta
  `FMPComparablesProvider.fetch(ticker)` y extrae los tickers pares de
  `payload[0]["peersList"]` (forma ya conocida y documentada del
  payload crudo de FMP, ver `COMPARABLES_PROVIDER.md`). Una lista vacía
  o sin `"peersList"` no es un error, mismo criterio ya aplicado por el
  propio `FMPComparablesProvider.fetch`.
- `fetch_peer_key_metrics(ticker, ...)`: para cada ticker par devuelto
  por `fetch_peer_tickers`, reutiliza **sin duplicarla**
  `fetch_and_normalize` (ya existente desde la Fase 1) para obtener su
  `FinancialStatement`/`MarketData` ya normalizados, empaquetados en un
  `PeerMetrics` nuevo (`ticker`, `financial_statement`, `market_data`).

Ambas funciones viven en `investmentops/core/orchestrator.py` (no en
`investmentops/data_providers/comparables.py`) para respetar la regla
de dependencia de `ARCHITECTURE.md`: combinar `FMPComparablesProvider`
con `FMPFundamentalsProvider` + `financial_statement_from_raw`/
`market_data_from_raw` requeriría que un módulo de `data_providers`
importe de `data_layer`, invirtiendo la dependencia ya establecida
(`data_layer` depende de `data_providers`, nunca al revés) — mismo
criterio arquitectónico ya aplicado a `fetch_and_normalize_historical`/
`fetch_and_normalize_news` en fases anteriores.

Ninguna de las dos funciones captura `DataProviderError`/
`NormalizationError`: las propaga tal cual (comportamiento "todo o
nada" si falla la consulta de comparables o la de cualquier empresa
par), mismo criterio ya usado por el resto de funciones `fetch_*`/
`fetch_and_normalize_*` del orquestador. No se modificó
`FMPComparablesProvider`, `FMPFundamentalsProvider`, ningún modelo de
dominio ni ninguna función ya existente: cambio puramente aditivo.

Quedan explícitamente fuera de esta tarea (ver TASKS.md, tareas
siguientes de la misma sección): adjuntar metadatos de procedencia a
los datos de comparables, y el modelo de dominio "Comparables" (sección
"Normalización").

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_core_orchestrator_comparables.py`

Modificados:
- `investmentops/core/orchestrator.py` (import de `FMPComparablesProvider`,
  nuevo dataclass `PeerMetrics`, nuevas funciones `fetch_peer_tickers` y
  `fetch_peer_key_metrics`)
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Fuente de datos de comparables":
- "Adjuntar metadatos de procedencia a los datos de comparables."
  Mismo patrón ya usado por `_attach_point_provenance`
  (`investmentops/data_providers/fundamentals.py`) y
  `_attach_news_provenance` (`investmentops/data_providers/news.py`):
  adjuntar `"source"`/`"queried_at"` a cada elemento del payload crudo
  de `FMPComparablesProvider.fetch`.