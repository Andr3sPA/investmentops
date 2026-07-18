# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Normalización → *"Extender la caché local para persistir series
históricas sin romper los datos ya guardados de Fase 1."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo anterior:
`investmentops/data_layer/cache.py` solo tenía
`save_financial_statement`/`load_financial_statement` y
`save_market_data`/`load_market_data` (corte único, Fase 1). No existía
ninguna función que persistiera un `FinancialStatementSeries` (la serie
histórica ya construida en la tarea anterior mediante
`financial_statement_series_from_raw`). Era trabajo nuevo.

## Qué se implementó

**`investmentops/data_layer/cache.py`** (modificado): se agregaron
`save_financial_statement_series(ticker, series, *, cache_path=None,
config=None) -> Path` y `load_financial_statement_series(ticker, *,
cache_path=None, config=None, max_age=DEFAULT_MAX_AGE) ->
FinancialStatementSeries | None`.

- Reutilizan, sin duplicar, la infraestructura ya existente:
  `_resolve_cache_dir`, `_ticker_file`, `_read_existing` (para guardar) y
  `_load_section` (para leer y chequear frescura vía `cached_at`, mismo
  umbral `DEFAULT_MAX_AGE` de 24 horas ya usado por las demás secciones).
- **Nueva sección** `"financial_statement_series"` dentro del mismo
  archivo `<TICKER>.json` ya usado por `"financial_statement"` y
  `"market_data"` (Fase 1), tal como ya anticipaba
  `investmentops/data_layer/CACHE.md`: *"podrá representarse como una
  lista dentro de la misma clave... sin romper este formato de archivo
  por ticker"*.
- **No se reutilizó `_save_section`/su serialización genérica
  (`dataclasses.asdict` + `_serialize`)** para el cuerpo de la sección:
  esa función serializa un único dataclass plano; una serie es una lista
  de `FinancialStatement` anidados con un campo `date` cada uno, que
  `asdict` no convierte a texto por sí solo. En su lugar,
  `save_financial_statement_series` construye explícitamente la lista de
  estados serializados (mismo patrón manual ya usado en
  `financial_statement_series_from_raw` para construir el modelo desde
  datos crudos), preservando el orden recibido (más reciente primero).
- Guardar la serie **no sobrescribe** `financial_statement`/`market_data`
  ya cacheados para el mismo ticker, y viceversa (fusión de secciones,
  mismo comportamiento ya probado para las secciones existentes).
- Mismo manejo de fallos ya usado por el resto del módulo: `CacheError`
  ante ticker vacío, fallos de E/S, `cached_at` ausente/no interpretable,
  o un elemento de `"statements"` con campos faltantes o una fecha
  inválida (identificando la sección, no solo "algo salió mal").

**`investmentops/tests/test_data_layer_cache_series.py`** (nuevo):
confirma guardado (estructura de la sección, serialización de cada
punto, orden preservado, normalización de ticker, fusión con
`financial_statement`/`market_data` en ambos órdenes de escritura,
sobrescritura solo de la sección de la serie, creación de directorio,
ticker vacío, ruta desde configuración) y lectura (ausencia de ticker/
sección, lectura fresca, insensibilidad a mayúsculas, orden preservado,
vencimiento por `max_age` por defecto y personalizado, `cached_at`
ausente/ inválido, estados con campos faltantes o fecha inválida, ticker
vacío, ruta desde configuración, y un roundtrip conjunto con
`financial_statement`/`market_data` en el mismo archivo).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_layer_cache_series.py` (nuevo)

Modificados:
- `investmentops/data_layer/cache.py` (se agregaron
  `save_financial_statement_series`/`load_financial_statement_series`;
  se actualizó el docstring del módulo para documentarlas y se agregó la
  constante `_FINANCIAL_STATEMENT_SERIES_SECTION`)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Normalización")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/data_layer/financial_statements.py`,
`investmentops/data_layer/financial_statement_series.py`,
`investmentops/data_layer/market_data.py`,
`investmentops/data_layer/normalization.py`,
`investmentops/data_providers/fundamentals.py`,
`save_financial_statement`/`load_financial_statement`/
`save_market_data`/`load_market_data` (el comportamiento de corte único
de Fase 1 no cambió), ningún otro módulo de código Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Con la caché de series históricas ya implementada, la Fase 3 completó
por completo sus secciones "Fuente de datos histórica" y "Normalización".
La siguiente sección pendiente es **"Motor de análisis: evolución de
ingresos y beneficios"**, cuya primera tarea es:

> "Definir qué se considera 'tendencia' (ej. crecimiento interanual,
> aceleración/desaceleración) a nivel básico."

Esta es una tarea de diseño/documentación (no de código), análoga a
`FINANCIAL_HEALTH_METRICS.md`/`VALUATION_METRICS.md`: deberá decidir, a
partir de los campos ya disponibles en `FinancialStatementSeries`
(`revenue`, `net_income` por periodo), qué constituye "tendencia" para el
MVP (por ejemplo, variación porcentual periodo a periodo y una
clasificación simple creciente/decreciente/estable), dejando explícito
qué queda fuera (ej. proyecciones, suavizado estadístico) antes de
implementar el cálculo determinístico en la tarea siguiente.
