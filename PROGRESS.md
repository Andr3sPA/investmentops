# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Fuente de datos de comparables" → "Adjuntar metadatos de
procedencia a los datos de comparables" (TASKS.md).

### Qué se implementó

`_attach_comparables_provenance` en
`investmentops/data_providers/comparables.py` (nuevo), aplicada dentro
de `FMPComparablesProvider.fetch` justo antes de construir el
`RawProviderData` devuelto.

Mismo patrón ya usado por `_attach_point_provenance`
(`investmentops/data_providers/fundamentals.py`, serie histórica) y
`_attach_news_provenance` (`investmentops/data_providers/news.py`,
noticias): cada elemento del payload crudo (típicamente un único
elemento con `"peersList"`, ver `COMPARABLES_PROVIDER.md`) recibe dos
claves nuevas, `"source"` y `"queried_at"`, con el mismo valor que el
`ProviderMetadata` de nivel superior (`RawProviderData.metadata`), sin
mutar los dicts originales devueltos por `response.json()` (se
construyen copias nuevas vía `{**item, ...}`).

`fetch()` conserva su comportamiento existente: valida ticker vacío,
traduce errores de red/autenticación/servidor/JSON inválido a
`DataProviderError`, y trata una lista vacía como respuesta válida (sin
pares encontrados). Lo único que cambia es que `payload` ahora lleva
`"source"`/`"queried_at"` por elemento antes de devolverse.
`investmentops.core.orchestrator.fetch_peer_tickers` no requirió ningún
cambio: sigue leyendo `payload[0].get("peersList")` sin verse afectado
por las claves nuevas.

Se actualizó `test_data_providers_comparables.py`
(`test_fetch_returns_raw_provider_data_with_list_payload`, que antes
comparaba `result.payload` por igualdad exacta contra el payload de
ejemplo) para reflejar que el payload devuelto ahora incluye
`"source"`/`"queried_at"` por elemento, verificando en su lugar los
campos originales uno por uno — mismo criterio ya aplicado por las
pruebas equivalentes de `fundamentals`/`news` tras sus propias tareas de
procedencia por punto.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_providers_comparables_provenance.py`

Modificados:
- `investmentops/data_providers/comparables.py` (`_attach_comparables_provenance`
  nueva; `fetch()` la aplica al payload antes de devolverlo)
- `investmentops/tests/test_data_providers_comparables.py`
  (`test_fetch_returns_raw_provider_data_with_list_payload` actualizada)
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Normalización":
- "Definir el modelo de dominio 'Comparables' (conjunto de empresas
  pares y sus métricas equivalentes)." Tarea de diseño/documentación,
  siguiendo el mismo patrón ya usado para "Noticias"
  (`investmentops/data_layer/news.py`) y `FinancialStatementSeries`: a
  partir de lo que ya expone `PeerMetrics`
  (`investmentops/core/orchestrator.py`: `ticker`, `financial_statement`,
  `market_data`), decidir si el modelo de dominio "Comparables" es un
  contenedor `{ticker, peers: Sequence[PeerMetrics|...]}` o requiere una
  estructura distinta, antes de implementar su transformación.