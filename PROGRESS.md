# InvestmentOps — Progreso

**Última actualización:** 2026-07-15

## Última tarea completada

Fase 1 → Orquestador mínimo → *"Implementar el paso de datos crudos a la
capa de normalización."*

Antes de implementarla, se verificó que no estuviera ya satisfecha:
`investmentops/core/orchestrator.py` solo tenía `fetch_raw_data`, que
devuelve `RawProviderData` sin normalizar; nada en el proyecto encadenaba
ese resultado con `investmentops.data_layer.normalization`. Con esto
continúa la sección "Orquestador mínimo" de TASKS.md (la tarea anterior,
"disparar la consulta al proveedor de Fase 1", quedó completa en la
conversación anterior).

## Qué se implementó

**`investmentops/core/orchestrator.py`** (modificado) — se agregó:

- **`NormalizedCompanyData`** (dataclass inmutable, nueva): agrupa
  `financial_statement: FinancialStatement` y `market_data: MarketData`,
  los dos modelos normalizados que hoy consumen los agentes de análisis
  ya implementados (`analyze_financial_health`, `analyze_valuation`).
- **`fetch_and_normalize(ticker, *, config=None, provider=None) ->
  NormalizedCompanyData`** (nueva): encadena, en orden:
  1. `fetch_raw_data(ticker, config=config, provider=provider)` (ya
     existente, sin cambios en su comportamiento).
  2. `investmentops.data_layer.normalization.financial_statement_from_raw(raw)`.
  3. `investmentops.data_layer.normalization.market_data_from_raw(raw)`.
  - No traduce `DataProviderError` ni `NormalizationError`: ambas se
    propagan tal cual, mismo criterio ya usado por `fetch_raw_data`. El
    manejo de fallos "sin detener el resto del flujo" sigue siendo una
    tarea explícita y posterior de esta misma sección de TASKS.md.
  - No consulta ni escribe la caché de datos normalizados
    (`investmentops.data_layer.cache`): igual que se documentó para
    `fetch_raw_data`, decidir cuándo evitar la llamada al proveedor por
    tener ya un dato normalizado reciente en caché es una decisión que
    corresponde a una tarea posterior que también involucre esta pieza,
    no algo que deba resolverse aquí de forma implícita.
  - `fetch_raw_data` se mantiene sin cambios en su firma ni
    comportamiento; se reescribió íntegramente el archivo para agregar
    la nueva función y actualizar el docstring del módulo, pero el
    cuerpo de `fetch_raw_data` es idéntico al de la conversación
    anterior.

**`investmentops/tests/test_core_orchestrator.py`** (modificado,
reescrito) — se mantuvieron las pruebas ya existentes para
`fetch_raw_data` (uso de proveedor inyectado, propagación de
`DataProviderError`, construcción por defecto de `FMPFundamentalsProvider`
vía mocks de `requests.get`) y se agregaron pruebas nuevas para
`fetch_and_normalize`:

- Que devuelve un `NormalizedCompanyData` con `FinancialStatement` y
  `MarketData` bien construidos a partir de un payload crudo completo.
- Que los campos de `FinancialStatement` (`revenue`, `net_income`,
  `debt`, `source`, `period_end`) y `MarketData` (`price`, `market_cap`,
  `multiples`, `source`, `as_of`) coinciden con lo esperado según el
  payload de prueba.
- Que el ticker recibido se propaga correctamente al proveedor
  inyectado.
- Que propaga `DataProviderError` sin traducirla cuando el proveedor
  inyectado falla (mismo criterio que `fetch_raw_data`).
- Que propaga `NormalizationError` sin traducirla cuando el payload
  crudo (aunque la consulta al proveedor tuvo éxito) no trae los campos
  imprescindibles para `FinancialStatement` (falta `balance_sheet_statement`)
  o para `MarketData` (falta `quote`).
- Que, sin `provider` explícito, construye y usa `FMPFundamentalsProvider`
  por defecto (mockeando `requests.get`, nunca una llamada de red real),
  confirmando que ambos modelos normalizados quedan con
  `source == "fmp"`.

## Decisiones tomadas

- **`fetch_and_normalize` como una función pequeña que encadena piezas ya
  probadas por separado**, en vez de reimplementar la lógica de
  normalización aquí. `financial_statement_from_raw`/`market_data_from_raw`
  ya están completas, probadas (`test_data_layer_normalization.py`) y
  señalan `NormalizationError` de forma explícita ante datos
  incompletos; esta tarea solo necesitaba conectar esas piezas con
  `fetch_raw_data`, sin duplicar ninguna validación ni transformación ya
  existente.
- **`NormalizedCompanyData` en vez de devolver una tupla.** Un dataclass
  con nombres de campo explícitos (`financial_statement`, `market_data`)
  es más legible para quien consuma esta función en una tarea posterior
  (la siguiente, "invocación secuencial de los dos agentes de análisis",
  que necesitará ambos valores con nombre, no posicionales) y sigue el
  mismo patrón de tipos inmutables ya usado en todo el proyecto
  (`FinancialStatement`, `MarketData`, `AnalysisResult`, etc.).
- **No se integra con la caché en esta tarea**, por la misma
  justificación ya usada para `fetch_raw_data`: la caché opera sobre
  modelos ya normalizados, y decidir cuándo leerla/escribirla en este
  flujo mezclaría una decisión de una tarea distinta y posterior con el
  alcance estrictamente delimitado de "pasar datos crudos a la capa de
  normalización".
- **No se traducen las excepciones a un tipo común.** `DataProviderError`
  y `NormalizationError` siguen siendo tipos distintos que se propagan
  tal cual; unificarlas (o capturarlas para producir un
  `ResearchFailure`) es explícitamente la última tarea pendiente de esta
  sección ("manejo de fallo... sin detener el resto del flujo"), no algo
  a adelantar aquí.

## Validación realizada

Revisión manual del código y las pruebas nuevas contra el patrón ya
usado en `test_data_layer_normalization.py` (mismos payloads de ejemplo
reutilizados como base) y en `test_core_orchestrator.py` de la
conversación anterior (mismo patrón de `_DummyProvider`/`_FailingProvider`
e inyección de `provider`). No se ejecutó la suite completa en este
entorno (Claude Web, sin acceso al repositorio real); se dejan los
archivos para que el usuario los integre y corra `pytest` localmente.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (se agregó `NormalizedCompanyData`
  y `fetch_and_normalize`; `fetch_raw_data` no cambió de comportamiento)
- `investmentops/tests/test_core_orchestrator.py` (se agregaron pruebas
  para `fetch_and_normalize`; las pruebas de `fetch_raw_data` ya
  existentes se mantuvieron)
- `TASKS.md` (segunda tarea de "Orquestador mínimo" marcada como
  completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/core/__init__.py`
(sigue re-exportando solo `ResearchFailure`/`ResearchResult`; no se
re-exportó `fetch_raw_data` ni `fetch_and_normalize` — mismo criterio ya
dejado anotado en la actualización anterior: `__init__.py` re-exporta
estructuras de datos, no funciones de orquestación; se puede revisar
cuando el orquestador tenga más piezas ensambladas), ningún otro módulo
de código Python existente.

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Orquestador mínimo" (TASKS.md) es:

3. *"Implementar la invocación secuencial de los dos agentes de análisis
   (salud financiera, valoración) sobre el modelo normalizado."*

Nota para la próxima conversación:
- `fetch_and_normalize(ticker, ...)` ya devuelve un `NormalizedCompanyData`
  con `financial_statement` y `market_data` listos para pasarse
  directamente a `analyze_financial_health(statement, config=...)` y
  `analyze_valuation(market_data, statement, config=...)` (ambos ya
  completos, ver `investmentops/analysis_engines/financial_health.py` y
  `.../valuation.py`).
- Esta tarea probablemente deba limitarse a una función que reciba un
  `NormalizedCompanyData` (o un ticker, llamando internamente a
  `fetch_and_normalize`) y devuelva los dos `AnalysisResult` obtenidos de
  invocar ambos agentes en secuencia, sin ensamblarlos todavía en un
  `ResearchResult` (esa es la tarea siguiente) ni manejar fallos de
  ninguno de los dos agentes sin detener el flujo (la tarea después de
  esa).
- Ojo con las pruebas: invocar ambos agentes reales implica mockear
  `requests.post` (llamada a Anthropic) igual que ya hacen
  `test_analysis_engines_financial_health_invoke.py` y
  `test_analysis_engines_valuation_invoke.py`, no solo `requests.get`
  (llamada a FMP).
