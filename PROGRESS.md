# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Normalización → *"Implementar la transformación de la respuesta
cruda histórica al modelo de series temporales."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo anterior:
`investmentops/data_layer/normalization.py` solo tenía
`financial_statement_from_raw`/`market_data_from_raw` (Fase 1), que toman
el **primer** elemento de las listas del payload — el corte más reciente,
no una serie. No existía ninguna función que tradujera el
`RawProviderData` devuelto por
`FMPFundamentalsProvider.fetch_historical` (varios periodos, con
procedencia por punto ya adjuntada en la tarea anterior) al
`FinancialStatementSeries` ya definido (tarea previa, ver actualización
anterior de este archivo). Era trabajo nuevo.

## Qué se implementó

**`investmentops/data_layer/normalization.py`** (modificado): se agregó
`financial_statement_series_from_raw(raw: RawProviderData) ->
FinancialStatementSeries`.

- Toma `raw.payload["income_statement"]` (uno o varios periodos, tal como
  entrega `fetch_historical`) y construye un `FinancialStatement` por
  cada elemento.
- **Decisión clave:** empareja cada periodo de `income_statement` con su
  `balance_sheet_statement` correspondiente **por fecha** (`"date"`), no
  por posición/índice. No hay garantía de que FMP devuelva ambos
  endpoints alineados por índice (distinta cantidad de periodos
  disponibles, orden distinto, etc.), así que emparejar por índice sería
  frágil y podría combinar en silencio datos de periodos distintos.
- El `source` de cada punto de la serie se toma del propio elemento
  (`income_entry["source"]`, ya adjuntado por
  `_attach_point_provenance` en la tarea anterior de esta misma
  sección), con `raw.metadata.source` como respaldo si un punto no lo
  trae. Esto es más preciso que usar siempre `raw.metadata.source`: dado
  que la procedencia ya vive por punto desde la tarea anterior, esta
  transformación la respeta en vez de ignorarla.
- Igual criterio de manejo de errores ya usado por
  `financial_statement_from_raw`: si a un periodo le faltan campos
  imprescindibles (incluyendo no encontrar su balance correspondiente
  por fecha) o su fecha no es interpretable, se levanta
  `NormalizationError` (reutilizada, no duplicada), identificando
  explícitamente **qué periodo** falló (por su fecha cruda), en vez de
  omitir ese punto en silencio o interpolar un valor.
- No reordena ni valida huecos/continuidad entre periodos: eso ya quedó
  documentado como fuera de alcance en `FinancialStatementSeries` (tarea
  anterior), y esta transformación respeta esa decisión.

**`investmentops/tests/test_data_layer_normalization_series.py`**
(nuevo): confirma que la serie se construye con un `FinancialStatement`
por periodo, que el orden de `income_statement` se preserva tal cual, que
el emparejamiento con `balance_sheet_statement` es por fecha (con un caso
explícito donde ambas listas no coinciden en orden), que cada punto
conserva sus propios valores y su propio `source` (con fallback al
`metadata.source` si el punto no lo trae), y los casos de error ya
esperados (`income_statement` vacío, periodo sin balance correspondiente
identificado por fecha, fecha ausente/inválida).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_layer_normalization_series.py` (nuevo)

Modificados:
- `investmentops/data_layer/normalization.py` (se agregó
  `financial_statement_series_from_raw`; se actualizó el docstring del
  módulo para documentarla)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Normalización")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/data_layer/financial_statements.py`,
`investmentops/data_layer/financial_statement_series.py`,
`investmentops/data_layer/market_data.py`,
`investmentops/data_providers/fundamentals.py`,
`financial_statement_from_raw`/`market_data_from_raw` (el comportamiento
de corte único de Fase 1 no cambió), ningún otro módulo de código Python
existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Con la transformación a `FinancialStatementSeries` ya implementada, la
siguiente tarea pendiente de la misma sección ("Normalización", Fase 3)
es:

> "Extender la caché local para persistir series históricas sin romper
> los datos ya guardados de Fase 1."

Esta tarea deberá decidir cómo representar una serie en
`<TICKER>.json` (ver `investmentops/data_layer/CACHE.md`, que ya
anticipa esta extensión: *"Extenderla a series es tarea explícita de la
Fase 3... podrá representarse como una lista dentro de la misma clave
(ej. `"financial_statement": [...]`) sin romper este formato de archivo
por ticker"*) e implementar el guardado/lectura correspondiente en
`investmentops/data_layer/cache.py`, sin alterar el formato ya usado por
`save_financial_statement`/`load_financial_statement` (corte único, Fase
1), que deben seguir funcionando exactamente igual.
