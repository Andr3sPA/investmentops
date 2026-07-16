# InvestmentOps — Progreso

**Última actualización:** 2026-07-15

## Última tarea completada

Fase 1 → Orquestador mínimo → *"Implementar la invocación secuencial de
los dos agentes de análisis (salud financiera, valoración) sobre el
modelo normalizado."*

Antes de implementarla, se verificó que no estuviera ya satisfecha:
`investmentops/core/orchestrator.py` solo tenía `fetch_raw_data` y
`fetch_and_normalize`; ningún módulo del proyecto encadenaba
`analyze_financial_health` y `analyze_valuation` (ambos ya completos,
Fase 1) sobre un `NormalizedCompanyData`. Con esto continúa la sección
"Orquestador mínimo" de TASKS.md (las dos tareas anteriores, "disparar la
consulta al proveedor" y "pasar datos crudos a normalización", quedaron
completas en conversaciones anteriores).

## Qué se implementó

**`investmentops/core/orchestrator.py`** (modificado) — se agregó:

- **`run_analysis_engines(company_data, *, config=None) ->
  list[AnalysisResult]`** (nueva): recibe un `NormalizedCompanyData`
  (típicamente el resultado de `fetch_and_normalize(ticker, ...)`) e
  invoca, en este orden:
  1. `investmentops.analysis_engines.financial_health.analyze_financial_health(company_data.financial_statement, config=config)`.
  2. `investmentops.analysis_engines.valuation.analyze_valuation(company_data.market_data, company_data.financial_statement, config=config)`.
  - Devuelve `[financial_health_result, valuation_result]`, ambos ya
    `AnalysisResult` completos (con `findings`, `supporting_metrics`,
    `limitations` y `provenance`).
  - No recalcula ninguna métrica: cada agente ya calcula las suyas
    internamente si no se le pasan precalculadas (parámetro `metrics`
    opcional de ambas funciones, no usado aquí).
  - No captura ni traduce las excepciones que puedan levantar los
    agentes (`PromptError`, `AgentProviderSelectionError`,
    `AIProviderError`): si `analyze_financial_health` falla, la
    excepción se propaga y `analyze_valuation` **no** llega a
    invocarse. Este es el comportamiento esperado y documentado de esta
    tarea; manejar el fallo de uno de los dos agentes sin detener el
    resto del flujo es, de forma explícita, la tarea siguiente de esta
    misma sección de TASKS.md.
  - No ensambla el resultado en un `ResearchResult`
    (investmentops.core.research_result): esa estructura además
    requiere la `Company` investigada y una `generated_at`, ninguna de
    las cuales es responsabilidad de esta pieza; el ensamblado es la
    tarea siguiente después del manejo de fallos.
  - `fetch_raw_data`, `NormalizedCompanyData` y `fetch_and_normalize` se
    mantienen sin cambios en su firma ni comportamiento; se reescribió
    íntegramente el archivo para agregar la nueva función y actualizar
    el docstring del módulo, pero el cuerpo de las tres piezas
    existentes es idéntico al de la conversación anterior.

**`tests/test_core_orchestrator.py`** (modificado, reescrito) — se
mantuvieron todas las pruebas ya existentes para `fetch_raw_data` y
`fetch_and_normalize`, y se agregaron pruebas nuevas para
`run_analysis_engines`:

- Que devuelve una lista de exactamente dos `AnalysisResult`, en el
  orden esperado (`"financial_health"` primero, `"valuation"` segundo).
- Que invoca primero al agente de salud financiera y después al de
  valoración (verificado inspeccionando el contenido de cada llamada
  mockeada a `requests.post`, en el orden en que ocurrieron).
- Que los `AnalysisResult` devueltos llevan los `findings` y
  `supporting_metrics` esperados, coherentes con lo que ya prueban
  `test_analysis_engines_financial_health_parse.py` y
  `test_analysis_engines_valuation_parse.py` de forma aislada.
- Que si el primer agente (salud financiera) falla (ej. error 500 del
  proveedor de IA), la excepción se propaga y el segundo agente
  (valoración) nunca llega a invocarse (`mock_post.call_count == 1`).
- Que se propagan sin traducir `AgentProviderSelectionError` (si no se
  puede resolver ningún proveedor de IA) y `PromptError` (si falla la
  carga del prompt de alguno de los dos agentes).

Nota: el proyecto tiene dos carpetas de pruebas (`tests/` e
`investmentops/tests/`), pero `pyproject.toml` solo declara
`testpaths = ["tests"]`; por eso este archivo se actualizó en `tests/`,
la ruta que efectivamente ejecuta `pytest`. `investmentops/tests/
test_core_orchestrator.py` (una versión más antigua, sin las pruebas de
`fetch_and_normalize`) no se tocó: no está en el alcance de esta tarea
decidir si esa carpeta duplicada debe eliminarse o consolidarse, y
hacerlo sería un cambio de alcance mayor al de esta tarea puntual.

## Decisiones tomadas

- **`run_analysis_engines` como una función pequeña que encadena piezas
  ya probadas por separado**, mismo criterio ya aplicado en
  `fetch_and_normalize`. `analyze_financial_health` y `analyze_valuation`
  ya están completas y probadas de forma aislada; esta tarea solo
  necesitaba conectar ambas con `NormalizedCompanyData`, sin duplicar
  ninguna lógica de cálculo de métricas ni de invocación al proveedor de
  IA.
- **Devuelve una `list[AnalysisResult]`, no un tipo nuevo.** A
  diferencia de `fetch_and_normalize` (que sí introdujo
  `NormalizedCompanyData` porque agrupaba dos tipos distintos con
  nombres propios), aquí ambos elementos ya son del mismo tipo
  (`AnalysisResult`) y se distinguen por su propio `analysis_id`; una
  lista simple es suficiente y evita introducir una estructura
  intermedia que la siguiente tarea (ensamblado en `ResearchResult`)
  probablemente no necesite tal cual.
- **Orden fijo: salud financiera primero, valoración después.** Es el
  mismo orden en que TASKS.md y ARCHITECTURE.md los mencionan
  consistentemente ("salud financiera, valoración"); no hay ninguna
  dependencia de datos entre ambos agentes (los dos consumen el mismo
  `NormalizedCompanyData` de forma independiente), por lo que el orden
  es una decisión de presentación/consistencia, no una restricción
  técnica.
- **No se capturan fallos parciales en esta tarea.** Si el primer
  agente falla, el segundo no se invoca y la excepción se propaga tal
  cual. Esto es deliberado y está documentado en el docstring de la
  función: la tarea siguiente de esta misma sección de TASKS.md
  ("Implementar el manejo de fallo... sin detener el resto del flujo")
  es exactamente la que debe envolver esta invocación para que un fallo
  de un agente no impida obtener el resultado del otro.
- **No se ensambla el `ResearchResult` en esta tarea.** Esa estructura
  requiere además la `Company` investigada (identidad básica, no parte
  de `NormalizedCompanyData`) y una marca de tiempo de ensamblado; mezclar
  eso aquí habría ampliado el alcance más allá de "invocar secuencialmente
  los dos agentes", que es literalmente el texto de la tarea en TASKS.md.

## Validación realizada

Revisión manual del código y las pruebas nuevas contra el patrón ya
usado en `test_analysis_engines_financial_health_invoke.py` y
`test_analysis_engines_valuation_invoke.py` (mismo mockeo de
`requests.post` hacia `investmentops.ai_providers.anthropic_provider`,
usando `side_effect` con una respuesta por cada llamada esperada en
orden). No se ejecutó la suite completa en este entorno (Claude Web, sin
acceso al repositorio real ni red en el sandbox); se dejan los archivos
para que el usuario los integre y corra `pytest` localmente.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (se agregó `run_analysis_engines`;
  `fetch_raw_data`, `NormalizedCompanyData` y `fetch_and_normalize` no
  cambiaron de comportamiento)
- `tests/test_core_orchestrator.py` (se agregaron pruebas para
  `run_analysis_engines`; las pruebas de `fetch_raw_data` y
  `fetch_and_normalize` ya existentes se mantuvieron)
- `TASKS.md` (tercera tarea de "Orquestador mínimo" marcada como
  completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/core/__init__.py`
(sigue re-exportando solo `ResearchFailure`/`ResearchResult`; mismo
criterio ya dejado anotado en la actualización anterior — `__init__.py`
re-exporta estructuras de datos, no funciones de orquestación),
`investmentops/tests/test_core_orchestrator.py` (versión duplicada más
antigua, fuera del `testpaths` declarado en `pyproject.toml`; no se tocó,
ver "Qué se implementó" arriba), ningún otro módulo de código Python
existente.

## Problemas encontrados

Se detectó que el repositorio tiene dos carpetas de pruebas paralelas
(`tests/` e `investmentops/tests/`) con contenido parcialmente duplicado
(por ejemplo, dos versiones de `test_core_orchestrator.py`), pero solo
`tests/` está declarada en `testpaths` de `pyproject.toml` y por lo tanto
es la que realmente ejecuta `pytest`. No se resolvió esta duplicación en
esta tarea por ser un cambio de alcance distinto (afectaría muchos
archivos de prueba ya existentes, no solo el de esta tarea) y por la
regla de "no rediseñar la arquitectura salvo que exista un problema
crítico" — esto es una inconsistencia de organización de pruebas, no un
problema arquitectónico crítico. Queda anotado aquí para que el usuario
decida si vale la pena consolidar ambas carpetas en una tarea aparte.

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Orquestador mínimo" (TASKS.md) es:

4. *"Implementar el ensamblado de ambos resultados en un 'Resultado de
   investigación' único."*

Nota para la próxima conversación:
- `run_analysis_engines(company_data, ...)` ya devuelve
  `[financial_health_result, valuation_result]`, los dos
  `AnalysisResult` que `ResearchResult.analysis_results` necesita (ver
  `investmentops/core/research_result.py`).
- Para ensamblar un `ResearchResult` completo también hace falta una
  `Company` (identidad básica: ticker, nombre, sector, mercado — ver
  `investmentops.data_layer.Company`), que hoy **no** forma parte de
  `NormalizedCompanyData` ni de ningún payload crudo ya normalizado
  (`FinancialStatement`/`MarketData` no incluyen nombre/sector/mercado).
  Esa tarea probablemente deba decidir de dónde sale esa `Company` (por
  ejemplo, un `Company` mínimo construido solo con el `ticker` recibido,
  ya que ni FMP ni el modelo de dominio actual exponen nombre/sector/
  mercado todavía) antes de poder construir el `ResearchResult`.
- La tarea también necesitará una `generated_at` (fecha/hora de
  ensamblado del resultado de investigación, distinta de
  `AnalysisProvenance.generated_at` de cada análisis individual).
- Como todavía no existe manejo de fallos parciales (tarea siguiente a
  esa), esta tarea de ensamblado probablemente asuma que
  `run_analysis_engines` tuvo éxito completo y construya un
  `ResearchResult` con `failures=[]`; el llenado real de `failures` es,
  de forma explícita, la última tarea pendiente de esta sección.
