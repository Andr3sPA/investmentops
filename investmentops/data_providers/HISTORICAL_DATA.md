# Series históricas de ingresos y beneficios — investigación del proveedor (Fase 3)

Cubre la tarea "Investigar si el proveedor actual soporta series
históricas (varios años/trimestres) o si se necesita otro
endpoint/proveedor" (TASKS.md, Fase 3, "Fuente de datos histórica").

Esta tarea es de **investigación/documentación**, no de código: decide si
`FMPFundamentalsProvider` (el proveedor ya elegido en la Fase 1, ver
`investmentops/data_providers/fundamentals.py`) puede seguir siendo la
fuente de datos también para la Fase 3, antes de implementar la consulta
real de series históricas (próxima tarea de esta misma sección).

## Hallazgo: FMP ya devuelve series históricas — no se descubrió recién, ya se estaba usando así

Los dos endpoints que `FMPFundamentalsProvider` ya consulta desde la
Fase 1 —`/income-statement/{ticker}` y
`/balance-sheet-statement/{ticker}`— **no devuelven un único periodo**:
devuelven un **arreglo** con varios periodos históricos (por defecto,
varios años en modo anual), ordenados del más reciente al más antiguo.
Esto ya es visible en el propio código existente del proyecto, aunque
hasta ahora se usaba solo parcialmente:

- `investmentops/data_providers/fundamentals.py` ya tipa el resultado de
  esos endpoints como listas (`payload["income_statement"]`,
  `payload["balance_sheet_statement"]`), no como objetos únicos.
- `investmentops/data_layer/normalization.py`
  (`financial_statement_from_raw`) ya toma explícitamente **el primer
  elemento** de esas listas (`income_statement[0]`,
  `balance_sheet_statement[0]`) como "el corte más reciente disponible",
  con un comentario explícito: *"Toma el corte más reciente disponible:
  el primer elemento... sin series históricas (eso es alcance explícito y
  posterior de la Fase 3)"*.
- Las pruebas ya existentes (`test_data_layer_normalization.py`,
  `test_financial_statement_from_raw_builds_statement_from_latest_period`)
  ya envían **dos periodos** en `income_statement` en sus datos de
  prueba, precisamente para confirmar que la Fase 1 descarta
  deliberadamente todo lo que no sea el primero.

Es decir: el proveedor elegido en la Fase 1 (FMP) **ya traía series
históricas desde el principio**; la Fase 1 simplemente no las
consumía, por diseño explícito y documentado (`financial_statements.py`:
*"definir aquí ya una estructura de serie temporal adelantaría trabajo
de esa fase sin que todavía exista la fuente de datos histórica ni el
motor de análisis de evolución que la consumiría"*).

## Parámetros relevantes de FMP para controlar la serie histórica

Ambos endpoints ya usados (`income-statement`, `balance-sheet-statement`)
aceptan, además de `apikey` (ya enviado por
`FMPFundamentalsProvider._get`), dos parámetros de consulta estándar de
la API de FMP, no usados todavía por el cliente actual:

- **`period`** (`annual` | `quarter`): granularidad de los periodos
  devueltos. El cliente actual no lo envía, por lo que FMP aplica su
  valor por defecto (`annual`).
- **`limit`**: número máximo de periodos a devolver (ej. `limit=5` para
  los últimos 5 años/trimestres). El cliente actual tampoco lo envía,
  por lo que FMP devuelve su cantidad por defecto de periodos históricos
  disponibles (ya varios, ver arriba).

Ninguno de los dos requiere un endpoint nuevo ni un plan de suscripción
distinto: son parámetros de consulta adicionales sobre los mismos dos
endpoints ya integrados y ya pagados/autorizados por la misma
`api_key` configurada en `[data_providers.fundamentals]`
(`config.local.toml`, ver `CONFIGURATION.md`).

## Decisión

**No se necesita otro endpoint ni otro proveedor.** FMP, el proveedor ya
elegido en la Fase 1, soporta series históricas de ingresos y beneficios
de forma nativa a través de los mismos dos endpoints ya integrados
(`income-statement`, `balance-sheet-statement`), simplemente consumiendo
más elementos de las listas que ya devuelven (opcionalmente acotando
cuántos con `limit`, y opcionalmente cambiando `period` a trimestral).

Esto es coherente con el principio de extensibilidad de
`ARCHITECTURE.md` ("Extensibilidad sin reescritura"): la fuente de datos
histórica de la Fase 3 no es un proveedor nuevo que registrar, sino una
extensión de la consulta ya existente al mismo proveedor.

## Qué queda para la próxima tarea (no se implementa aquí)

La tarea siguiente en `TASKS.md` ("Implementar la consulta de series
históricas de ingresos y beneficios para un ticker") deberá decidir e
implementar, como trabajo de código:

- Si `FMPFundamentalsProvider.fetch` (o un método nuevo) debe dejar de
  descartar los periodos adicionales, y cómo exponerlos en
  `RawProviderData.payload` sin romper el uso actual de `payload[...][0]`
  en `investmentops.data_layer.normalization` (Fase 1, todavía vigente y
  fuera de alcance de esta tarea).
- Si conviene enviar `limit`/`period` explícitamente (en vez de depender
  de los valores por defecto de FMP), y con qué valores razonables para
  el MVP.
- Cómo adjuntar metadatos de procedencia a cada punto de la serie (tarea
  separada y siguiente en la misma sección de `TASKS.md`).

## Fuera de alcance de esta tarea

- Cualquier cambio de código en `FMPFundamentalsProvider`,
  `investmentops.data_layer.normalization`, o los modelos de dominio
  (`FinancialStatement`, `MarketData`): tareas separadas y posteriores de
  esta misma sección de la Fase 3.
- El endpoint de cotización histórica (`/historical-price-full/{ticker}`
  u otro equivalente de FMP para `MarketData`/precio en el tiempo): no es
  necesario para esta tarea, ya que la Fase 3 (`ROADMAP.md`) se centra
  explícitamente en **ingresos y beneficios** (`income_statement`), no en
  series de precio de mercado.
- Evaluar proveedores alternativos a FMP: no hay ninguna limitación
  encontrada en esta investigación que lo justifique.
