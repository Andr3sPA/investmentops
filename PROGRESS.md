# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Fuente de datos histórica → *"Implementar la consulta de series
históricas de ingresos y beneficios para un ticker."*

## Verificación previa (sin duplicar trabajo)

Se confirmó primero que la tarea anterior de esta misma sección
("Investigar si el proveedor actual soporta series históricas...") ya
estaba completa (`investmentops/data_providers/HISTORICAL_DATA.md`).

Se revisó si esta tarea ya estaba satisfecha de forma indirecta: el
cliente `FMPFundamentalsProvider.fetch()` ya consulta los endpoints
`income-statement`/`balance-sheet-statement`, que técnicamente ya
devuelven varios periodos en su respuesta cruda. Sin embargo, `fetch()`:

- No permite controlar `period` (`annual`/`quarter`) ni `limit`
  (cantidad de periodos), dependiendo por completo de los valores por
  defecto de FMP.
- Su contrato (`RawProviderData` reutilizado también por Fase 1) no deja
  claro para quien lo invoque que el payload trae series completas, ya
  que la propia normalización de Fase 1 (`financial_statement_from_raw`)
  descarta deliberadamente todo salvo el primer elemento.

Por lo tanto, esta tarea **no** estaba satisfecha: faltaba un punto de
entrada explícito, propio de la Fase 3, que consulte series históricas
de forma intencional y configurable, sin tocar el comportamiento ya
establecido de `fetch()` (usado por Fase 1/2 y sus pruebas existentes).

## Qué se implementó

**`investmentops/data_providers/fundamentals.py`** (modificado):

- Nuevo método `FMPFundamentalsProvider.fetch_historical(ticker, *,
  period="annual", limit=5) -> RawProviderData`:
  - Consulta únicamente `income-statement` y `balance-sheet-statement`
    (no `quote`), conforme a lo ya documentado en `HISTORICAL_DATA.md`:
    la Fase 3 se centra en ingresos y beneficios, no en series de precio
    de mercado.
  - Envía `period` y `limit` como parámetros de consulta explícitos,
    junto a `apikey`, en vez de depender de los valores por defecto de
    FMP.
  - Devuelve el `payload` con **todos** los periodos que entrega FMP
    (hasta `limit`), sin descartar ninguno — a diferencia de la
    normalización de Fase 1, que sigue tomando solo `[0]` y no se tocó.
  - Valida `ticker` (no vacío), `period` (`"annual"`/`"quarter"`) y
    `limit` (≥ 1), señalando `DataProviderError` en caso contrario, y
    traduce fallos de red/autenticación/formato con el mismo criterio ya
    usado por `fetch()`.
- Se extendió el método privado `_get` para aceptar un parámetro
  opcional `extra_params` (usado por `fetch_historical` para enviar
  `period`/`limit`). `fetch()` sigue invocando `_get` sin `extra_params`,
  por lo que su comportamiento **no cambió**: sigue enviando únicamente
  `{"apikey": ...}`, confirmado con una prueba de regresión explícita.

**`investmentops/tests/test_data_providers_fundamentals_historical.py`**
(nuevo): cubre el comportamiento básico de `fetch_historical` (series
completas, normalización de ticker), el envío de `period`/`limit` (por
defecto y explícitos), la exclusión del endpoint `quote`, la validación
de argumentos (ticker vacío, `period` inválido, `limit` < 1), el manejo
de errores (ticker inexistente, fallo de red, 401, 500, JSON inválido), y
una prueba de regresión que confirma que `fetch()` sigue enviando
únicamente `apikey`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_providers_fundamentals_historical.py` (nuevo)

Modificados:
- `investmentops/data_providers/fundamentals.py` (nuevo método
  `fetch_historical`, `_get` extendido con `extra_params` opcional)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Fuente de datos
  histórica")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/data_layer/normalization.py` (la transformación al modelo
de series temporales es tarea separada de la sección "Normalización"),
ningún otro módulo de código Python existente, ninguna prueba existente
(`test_data_providers_fundamentals.py` sigue pasando sin cambios).

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

La siguiente tarea pendiente en la misma sección de la Fase 3 ("Fuente
de datos histórica") es:

> "Adjuntar metadatos de procedencia a cada punto de la serie
> histórica."

A diferencia de `ProviderMetadata` en Fase 1 (un único metadato para
toda la consulta), esta tarea deberá decidir cómo asociar procedencia
(fuente, fecha) a **cada periodo individual** de la serie devuelta por
`fetch_historical`, antes de que la sección "Normalización" transforme
esa serie al modelo de dominio temporal.
