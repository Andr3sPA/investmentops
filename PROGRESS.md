# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 3, "Orquestador" → "Incluir el resultado de evolución de ingresos y
beneficios en el `ResearchResult` ensamblado, incluyendo el manejo de
fallos parciales (serie histórica no disponible, error de
normalización) sin detener el resto del flujo, siguiendo el mismo
criterio ya usado por `investigate` para los demás agentes" (TASKS.md).

### Qué se implementó

`investigate` en `investmentops/core/orchestrator.py` ahora invoca
también `run_trend_analysis_engine(ticker, config=config,
provider=provider)` (ya implementada en la tarea anterior de esta misma
sección), en un `try/except` **independiente** de los dos ya existentes
para salud financiera y valoración:

- Si el motor de tendencia levanta `DataProviderError` o
  `NormalizationError` (serie histórica no disponible para el ticker,
  datos incompletos que no se pueden normalizar), se captura y se
  traduce a `ResearchFailure(stage="data_provider",
  identifier="trend_analysis", reason=<mensaje>)`, sin detener el resto
  del flujo ni afectar los resultados ya obtenidos de salud financiera o
  valoración.
- Si tiene éxito, su `AnalysisResult` (ya con procedencia centinela
  `ai_provider="none"`/`ai_model="deterministic"`, ver
  `_trend_analysis_result_to_analysis_result`) se agrega a
  `analysis_results`, en el orden `[financial_health, valuation,
  trend_analysis]`.

**Invocación condicional a la capacidad del proveedor.** El parámetro
`provider` de `investigate` está tipado como `DataProvider`, cuyo
contrato solo exige `fetch(ticker)`. `run_trend_analysis_engine`
necesita además `fetch_historical(ticker, period=..., limit=...)` (hoy
solo `FMPFundamentalsProvider` lo implementa). Para no romper el uso ya
establecido de proveedores de prueba mínimos (que en todo el proyecto
solo implementan `fetch`, ver `test_core_orchestrator.py`,
`test_cli_dispatch.py`, `test_core_orchestrator_reports.py`, etc.), el
motor de tendencia solo se intenta cuando:

- `provider is None` (se usará el `FMPFundamentalsProvider` real por
  defecto, que sí soporta series históricas), o
- el `provider` inyectado expone `fetch_historical` (`hasattr` check).

Si el proveedor inyectado no expone esa capacidad, `investigate`
simplemente no incluye ningún análisis de tendencia para esa
investigación, **sin** registrarlo como `ResearchFailure`: es una
limitación de capacidad del proveedor usado, no un fallo en tiempo de
ejecución de una consulta real. Esta decisión de diseño es lo que
permite que **todas** las pruebas ya existentes de `investigate` (Fase
1 y 2, con proveedores mínimos sin `fetch_historical`) sigan pasando sin
ninguna modificación, ya que su comportamiento (`analysis_results` con
2 elementos, `failures` según corresponda) no cambió.

Se agregó `investmentops/tests/test_core_orchestrator_trend_integration.py`,
cubriendo: inclusión del análisis de tendencia cuando el proveedor
soporta series históricas (orden `[financial_health, valuation,
trend_analysis]`, procedencia centinela), omisión silenciosa cuando el
proveedor no las soporta (regresión explícita del comportamiento ya
existente), captura de `DataProviderError` del motor de tendencia como
`ResearchFailure` sin afectar a los demás agentes, y regresión del
fallo de `data_provider` cuando falla la fuente principal (sin llegar
siquiera a intentar el motor de tendencia).

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (docstring del módulo
  actualizado; `investigate` gana el bloque de invocación condicional
  de `run_trend_analysis_engine` con su propio manejo de fallos
  parciales)
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_core_orchestrator_trend_integration.py`

No modificados: `investmentops/analysis_engines/trends.py`,
`investmentops/data_layer/normalization.py`,
`investmentops/data_providers/fundamentals.py`,
`investmentops/core/research_result.py`, `run_analysis_engines`,
`analyze_financial_health`, `analyze_valuation`,
`run_trend_analysis_engine`, `_trend_analysis_result_to_analysis_result`
(ninguna de las piezas ya implementadas en tareas anteriores cambió), ni
`ROADMAP.md`, `GOALS.md`, `ARCHITECTURE.md`. Tampoco se modificó ninguna
de las pruebas ya existentes (`test_core_orchestrator.py`,
`test_cli_dispatch.py`, `test_core_orchestrator_reports.py`,
`test_core_orchestrator_report_formats.py`, `test_cli_format.py`,
`test_main.py`): todas siguen pasando sin cambios, ya que usan
proveedores de prueba mínimos sin `fetch_historical`.

## Próxima tarea recomendada

Fase 3, "Reportes" → "Decidir el formato de presentación de la serie
(tabla simple vs. descripción textual) para esta fase."

Esta es una tarea de diseño/documentación (no de código): fijar cómo se
mostrará la evolución de ingresos y beneficios (el nuevo
`AnalysisResult` con `analysis_id="trend_analysis"`, ya incluido en
`ResearchResult.analysis_results` desde esta tarea) en los reportes
Markdown/HTML, antes de tocar `investmentops/reports/markdown.py` ni
`investmentops/reports/html.py` en las dos tareas siguientes de esa
misma sección.
