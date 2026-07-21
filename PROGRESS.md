# InvestmentOps — Progreso

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 4, "Orquestador" → "Registrar el nuevo proveedor de noticias sin
modificar los proveedores existentes" (TASKS.md).

### Qué se implementó

`fetch_raw_news_data`/`fetch_and_normalize_news` en
`investmentops/core/orchestrator.py`, siguiendo exactamente el mismo
patrón de dos capas ya usado por `fetch_raw_data`/`fetch_and_normalize`
(Fase 1) y `fetch_raw_historical_data`/`fetch_and_normalize_historical`
(Fase 3):

- **`fetch_raw_news_data(ticker, ...)`**: dispara la consulta al
  proveedor de noticias (`investmentops.data_providers.news.FMPNewsProvider.fetch`).
  Por defecto construye un `FMPNewsProvider`, pero acepta un `provider`
  inyectado (pensado sobre todo para pruebas).
- **`fetch_and_normalize_news(ticker, ...)`**: encadena
  `fetch_raw_news_data(ticker, ...)` con
  `investmentops.data_layer.normalization.news_from_raw`, devolviendo
  una `list[News]` (lista vacía si la empresa no tiene noticias
  recientes, mismo criterio ya aplicado en `investmentops.data_providers.news`:
  eso no es un error).

Ninguna de las dos captura `DataProviderError` ni `NormalizationError`:
las propagan tal cual, mismo criterio que las funciones equivalentes de
Fase 1 y Fase 3. No se modificó `FMPFundamentalsProvider` ni ninguna
función ya existente del orquestador (`fetch_raw_data`,
`fetch_and_normalize`, `fetch_raw_historical_data`,
`fetch_and_normalize_historical`, `run_trend_analysis_engine`,
`investigate`, etc.): es un cambio puramente aditivo.

Registrar el motor de análisis de noticias relevantes en el flujo del
orquestador e incluir su resultado en `ResearchResult` quedan como
tareas separadas y siguientes de esta misma sección.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_core_orchestrator_news.py`

Modificados:
- `investmentops/core/orchestrator.py` (agregado `fetch_raw_news_data`,
  `fetch_and_normalize_news`, imports de `News`, `news_from_raw` y
  `FMPNewsProvider`; ninguna función existente cambió su comportamiento)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Orquestador" → "Registrar el nuevo motor de análisis sin
modificar los motores existentes."