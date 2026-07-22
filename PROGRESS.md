# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Normalización" → "Implementar el guardado de comparables
normalizados en la caché local tras cada consulta" (TASKS.md).

### Qué se implementó

`save_comparables` en `investmentops/data_layer/cache.py`, siguiendo
exactamente el mismo patrón ya usado por `save_financial_statement_series`
(Fase 3) y `save_news` (Fase 4): agrega una nueva sección `"comparables"`
al mismo archivo `<TICKER>.json` ya usado por las cuatro secciones
existentes (`financial_statement`, `market_data`,
`financial_statement_series`, `news`), sin sobrescribirlas.

La sección serializa `{"peers": [...], "cached_at": ...}`, donde cada
elemento de `"peers"` serializa explícitamente un `PeerComparable`
(`ticker`, `financial_statement` con los mismos campos ya usados por la
sección `"financial_statement"`, `market_data` con los mismos campos ya
usados por la sección `"market_data"`). No se reutiliza `_save_section`
(que usa `dataclasses.asdict` sobre un único dataclass plano), por la
misma razón ya documentada para `save_financial_statement_series`/
`save_news`: `Comparables` es una lista de dataclasses anidados con
campos `date`. Sí se reutilizan `_resolve_cache_dir`, `_ticker_file` y
`_read_existing`, sin duplicar esa infraestructura.

Una lista de pares vacía (empresa sin comparables según el proveedor) es
un valor válido y se guarda igual que cualquier otro, mismo criterio ya
aplicado por `save_news` con `items=[]`.

No se implementó `load_comparables`: es la tarea siguiente y separada en
la misma sección de `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_layer_cache_comparables.py`

Modificados:
- `investmentops/data_layer/cache.py` (nueva función `save_comparables`,
  nueva constante `_COMPARABLES_SECTION`, nuevos imports: `Comparables`,
  `PeerComparable`)
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Normalización":
- "Implementar la lectura de comparables normalizados desde caché para
  evitar una nueva llamada al proveedor si el dato ya existe y es
  reciente." Seguiría el mismo patrón ya usado por
  `load_financial_statement_series`/`load_news`: `load_comparables`
  reconstruye `Comparables`/`PeerComparable` a partir de la sección
  `"comparables"` ya escrita por `save_comparables`, devolviendo `None`
  si no hay nada cacheado o si venció, y `CacheError` ante una sección
  corrupta/incompleta.