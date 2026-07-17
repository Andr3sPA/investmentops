# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Fuente de datos histórica → *"Adjuntar metadatos de procedencia
a cada punto de la serie histórica."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que las dos tareas anteriores de esta misma sección ya
estaban completas: la investigación del proveedor
(`investmentops/data_providers/HISTORICAL_DATA.md`) y la consulta de
series históricas (`FMPFundamentalsProvider.fetch_historical`).

Se revisó si esta tarea ya estaba satisfecha indirectamente por el
`ProviderMetadata` que `fetch_historical` ya adjunta a
`RawProviderData.metadata`. No lo estaba: ese metadato describe la
**consulta completa** (un único `source`/`queried_at`/`reliability` para
toda la respuesta), no cada punto individual de la serie
(`income_statement`/`balance_sheet_statement`, cada uno con varios
periodos). La propia nota de "próxima tarea recomendada" dejada en la
actualización anterior de este archivo ya señalaba explícitamente esta
diferencia, así que la tarea requería trabajo nuevo.

## Qué se implementó

**`investmentops/data_providers/fundamentals.py`** (modificado):

- Nueva función privada `_attach_point_provenance(points, metadata) ->
  list[dict]`: construye una lista nueva (sin mutar los dicts originales
  devueltos por `response.json()`) donde cada punto de la serie recibe
  dos claves adicionales:
  - `"source"`: mismo valor que `metadata.source` (`"fmp"`).
  - `"queried_at"`: mismo valor que `metadata.queried_at`, serializado a
    ISO 8601 (texto), consistente con el formato ya usado para fechas en
    el resto del proyecto (ej. `cached_at` en
    `investmentops/data_layer/cache.py`).
- `FMPFundamentalsProvider.fetch_historical` ahora construye primero el
  `ProviderMetadata` de la consulta (antes se construía al final) y lo
  usa tanto para `RawProviderData.metadata` (sin cambios de
  comportamiento) como para adjuntar, vía `_attach_point_provenance`, la
  procedencia a cada elemento de `payload["income_statement"]` y
  `payload["balance_sheet_statement"]`.
- La validación de "el ticker no existe o no hay datos históricos" sigue
  operando sobre la serie cruda (`raw_series["income_statement"]`, antes
  de adjuntar procedencia), sin cambios de comportamiento.
- `fetch()` (Fase 1) no se tocó: sigue sin adjuntar procedencia por
  punto, ya que no trabaja con series (solo el corte más reciente).

**`investmentops/tests/test_data_providers_fundamentals_historical_provenance.py`**
(nuevo): confirma que cada punto de ambas series lleva `"source"`/
`"queried_at"`, que ambos valores coinciden con el `ProviderMetadata` de
nivel superior, que los campos originales de FMP (`date`, `revenue`,
`netIncome`, `totalDebt`, etc.) se preservan intactos, que los dicts
originales devueltos por `response.json()` no se mutan, y que todos los
puntos de una misma consulta comparten el mismo `queried_at`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_providers_fundamentals_historical_provenance.py` (nuevo)

Modificados:
- `investmentops/data_providers/fundamentals.py` (nueva función
  `_attach_point_provenance`; `fetch_historical` adjunta procedencia por
  punto)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Fuente de datos
  histórica")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/data_layer/normalization.py`,
`investmentops/tests/test_data_providers_fundamentals_historical.py`
(sigue pasando sin cambios, ya que no depende de las claves nuevas),
ningún otro módulo de código Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Con "Fuente de datos histórica" ahora completa en su totalidad, la
siguiente sección pendiente de la Fase 3 es "Normalización":

> "Extender el modelo 'Estados financieros normalizados' para incluir
> series temporales (no solo el dato más reciente)."

Esta tarea deberá decidir la forma concreta del modelo de serie temporal
(ej. una lista de `FinancialStatement` con su propio punto de corte, o
un tipo nuevo), reutilizando las claves de procedencia por punto
(`"source"`, `"queried_at"`) ya adjuntadas en esta tarea al transformar
el payload crudo de `fetch_historical`.
