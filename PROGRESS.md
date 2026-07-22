# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Normalización" → "Definir el modelo de dominio 'Comparables'
(conjunto de empresas pares y sus métricas equivalentes)" (TASKS.md).

### Qué se implementó

`Comparables`/`PeerComparable` en `investmentops/data_layer/comparables.py`
(nuevo). Tarea de definición de estructura, siguiendo el mismo patrón ya
usado por `FinancialStatementSeries` (Fase 3) y `News` (Fase 4): un
archivo `.py` con el/los `dataclass(frozen=True)` correspondientes y un
docstring extenso documentando la decisión, en vez de solo un `.md` de
diseño.

Decisión de diseño: en vez de introducir campos nuevos, `Comparables`
reutiliza `FinancialStatement`/`MarketData` (ya normalizados desde la
Fase 1) como las cifras de cada empresa par, agrupadas en un tipo
intermedio `PeerComparable` (`ticker`, `financial_statement`,
`market_data`). `Comparables` es el contenedor simple `{ticker, peers:
Sequence[PeerComparable]}`, donde `ticker` identifica a la empresa
investigada y `peers` preserva el orden en que el proveedor de
comparables entregó los pares (sin reordenar ni filtrar, mismo criterio
ya fijado en `investmentops/data_providers/COMPARABLES_PROVIDER.md`).
Una lista de pares vacía es un caso válido (empresa sin comparables según
el proveedor).

Se documentó explícitamente la relación con
`investmentops.core.orchestrator.PeerMetrics` (ya existente desde la
tarea anterior de esta misma fase, "Implementar la consulta de métricas
clave... para cada empresa par"): tiene la misma forma que
`PeerComparable`, pero vive en una capa distinta (composición *on-the-fly*
del orquestador, no modelo de dominio de `data_layer`). Esta tarea no
modificó `investmentops/core/orchestrator.py` ni `PeerMetrics`: decidir
si `fetch_peer_key_metrics` pasa a construir/devolver este nuevo modelo
de dominio es una decisión de la tarea siguiente ("Implementar la
transformación de los datos crudos de comparables al modelo
normalizado"), no de esta.

No se propaga `queried_at` por par (metadato de la consulta, no del
dato), mismo criterio ya aplicado por `FinancialStatementSeries`/`News`.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/comparables.py`
- `investmentops/tests/test_data_layer_comparables.py`

Modificados:
- `investmentops/data_layer/__init__.py` (re-exporta `Comparables`,
  `PeerComparable`)
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Normalización":
- "Implementar la transformación de los datos crudos de comparables al
  modelo normalizado." Traduciría el `RawProviderData` que entrega
  `FMPComparablesProvider.fetch` (o, alternativamente, la composición ya
  existente vía `fetch_peer_tickers`/`fetch_and_normalize` en el
  orquestador) al nuevo `Comparables`/`PeerComparable` ya definido en
  esta tarea, decidiendo en concreto dónde vive esa función
  (`investmentops.data_layer.normalization`, siguiendo el patrón ya
  usado por `financial_statement_series_from_raw`/`news_from_raw`) y si
  reutiliza o reemplaza la composición ya existente en
  `investmentops.core.orchestrator.fetch_peer_key_metrics`.