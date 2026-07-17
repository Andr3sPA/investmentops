# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Fuente de datos histórica → *"Investigar si el proveedor actual
soporta series históricas (varios años/trimestres) o si se necesita otro
endpoint/proveedor."*

## Verificación previa (sin duplicar trabajo)

Se confirmó primero que la Fase 2 ya estaba completa: la única tarea
pendiente que quedaba en esa fase era opcional ("Escribir el archivo de
prompt del agente de reporte..."), explícitamente marcada como tal en
`TASKS.md`, y la sección "Verificación" de la Fase 2 es manual (no de
implementación). La siguiente tarea real, ya anticipada como "Próxima
tarea recomendada" en la actualización anterior de este archivo, es la
primera de la Fase 3.

Se confirmó que esta tarea **no** estaba satisfecha: no existía ningún
documento que investigara ni registrara si FMP soporta series
históricas. El código existente ya *insinuaba* la respuesta (el payload
crudo de `FMPFundamentalsProvider` y la normalización en
`investmentops/data_layer/normalization.py` ya tratan
`income_statement`/`balance_sheet_statement` como **listas**, tomando
solo el primer elemento como "el más reciente"), pero esa observación
nunca se había investigado ni dejado documentada como decisión explícita
de esta tarea concreta de `TASKS.md`.

## Qué se implementó

Esta es una tarea de **investigación/documentación** (no de código),
igual criterio que otras tareas de decisión ya completadas en fases
anteriores (ej. "Elegir el proveedor de datos financieros fundamentales"
en Fase 1, `FINANCIAL_HEALTH_METRICS.md`/`VALUATION_METRICS.md` en Fase
1, `CACHE.md`/`HTML_TEMPLATE.md`/`REPORT_MODEL.md`/`REPORT_SECTIONS.md`
en Fases 1-2).

**`investmentops/data_providers/HISTORICAL_DATA.md`** (nuevo):

- Documenta el hallazgo central: los dos endpoints de FMP ya integrados
  desde la Fase 1 (`income-statement`, `balance-sheet-statement`) **ya
  devuelven series históricas de forma nativa** (un arreglo con varios
  periodos, no un único periodo). Esto ya era visible en el código
  existente —`FMPFundamentalsProvider` los tipa como listas,
  `financial_statement_from_raw` toma explícitamente `[0]` como "el
  corte más reciente", con un comentario que ya remitía a esta tarea de
  Fase 3— pero nunca se había investigado ni dejado como decisión
  explícita.
- Documenta los dos parámetros de consulta relevantes de FMP, no usados
  todavía por el cliente actual: `period` (`annual`/`quarter`) y `limit`
  (cantidad de periodos a devolver).
- **Decisión: no se necesita otro endpoint ni otro proveedor.** La
  fuente de datos histórica de la Fase 3 es una extensión de la consulta
  ya existente al mismo proveedor (FMP), no un proveedor nuevo que
  registrar — consistente con "Extensibilidad sin reescritura"
  (`ARCHITECTURE.md`).
- Deja explícitamente fuera de alcance (para la tarea siguiente,
  "Implementar la consulta de series históricas...") las decisiones de
  implementación: si `FMPFundamentalsProvider.fetch` debe dejar de
  descartar los periodos adicionales y cómo, si conviene enviar
  `limit`/`period` explícitamente, y la propagación de metadatos de
  procedencia por punto de la serie (tarea separada y siguiente).
- Aclara que el endpoint de cotización histórica de FMP queda fuera de
  esta tarea, ya que `ROADMAP.md` (Fase 3) se centra explícitamente en
  ingresos y beneficios (`income_statement`), no en series de precio.

**Ningún archivo de código Python se modificó.** No se tocó
`FMPFundamentalsProvider`, `investmentops.data_layer.normalization`, ni
ningún modelo de dominio: esta tarea es puramente de investigación,
conforme a su alcance en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/HISTORICAL_DATA.md` (nuevo)

Modificados:
- `TASKS.md` (tarea marcada como completada, Fase 3, "Fuente de datos
  histórica")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, ningún módulo de código
Python existente, ningún archivo de pruebas existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

La siguiente tarea pendiente en la misma sección de la Fase 3 ("Fuente
de datos histórica") es:

> "Implementar la consulta de series históricas de ingresos y beneficios
> para un ticker."

Esta sí es una tarea de código: deberá decidir cómo `FMPFundamentalsProvider`
(o una extensión suya) expone varios periodos de `income_statement`/
`balance_sheet_statement` en `RawProviderData.payload`, sin romper el
comportamiento actual de Fase 1 (`payload[...][0]` en
`investmentops.data_layer.normalization`, que debe seguir funcionando
igual mientras esa capa no se extienda en una tarea posterior de esta
misma sección de la Fase 3, "Normalización").
