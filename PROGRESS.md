# InvestmentOps — Progreso

**Última actualización:** 2026-07-15

## Última tarea completada

Fase 1 → Orquestador mínimo → *"Implementar el manejo de fallo del
proveedor de datos o del proveedor de IA sin detener el resto del
flujo, dejándolo explícito en el resultado."*

Con esta tarea **queda completa la sección "Orquestador mínimo"** de
`TASKS.md`. Se verificó antes de implementar que no estuviera ya
satisfecha: `fetch_and_normalize` y `run_analysis_engines` documentan
explícitamente que propagan sus excepciones tal cual (ver sus propios
docstrings y `PROGRESS.md` de la conversación anterior), y
`assemble_research_result` solo acepta `failures` como parámetro pasivo
— nada en el proyecto detectaba fallos parciales todavía.

## Qué se implementó

**`investmentops/core/orchestrator.py`** (modificado) — se agregó una
única función nueva, reutilizando sin cambios `fetch_raw_data`,
`NormalizedCompanyData`, `fetch_and_normalize`, `run_analysis_engines` y
`assemble_research_result`:

- **`investigate(ticker, *, config=None, provider=None) -> ResearchResult`**
  (nueva): función de flujo completo que envuelve las piezas ya
  existentes y decide qué hacer ante cada tipo de fallo, sin detener el
  resto del flujo:

  1. **Consulta + normalización** (`fetch_and_normalize`): si falla con
     `DataProviderError` o `NormalizationError`, se devuelve de
     inmediato un `ResearchResult` con `analysis_results=[]` y un único
     `ResearchFailure(stage="data_provider", identifier=<ticker
     normalizado>, reason=<mensaje del error>)`. Decisión explícita
     (dejada pendiente en la actualización anterior de este archivo):
     **sí** tiene sentido producir un `ResearchResult` en este caso,
     con la etapa de datos marcada como fallida, en vez de no producir
     ningún resultado — conforme a `ARCHITECTURE.md`, "el reporte final
     debe reflejar explícitamente qué información no pudo obtenerse, en
     vez de fallar silenciosamente".
  2. **Agentes de análisis, invocados por separado** (no vía
     `run_analysis_engines`, que se detiene ante el primer fallo): se
     llama a `analyze_financial_health` y, en un `try/except`
     independiente, a `analyze_valuation`. Cada uno captura
     `PromptError`, `AgentProviderSelectionError` y `AIProviderError` de
     forma aislada, traduciéndolos a `ResearchFailure(stage=
     "analysis_engine", identifier=<analysis_id del agente>,
     reason=<mensaje>)`. Un fallo en un agente no impide que el otro se
     ejecute; los resultados exitosos (cero, uno o dos) se recolectan
     en orden.
  3. **Ensamblado final**: se llama a `assemble_research_result(ticker,
     <resultados exitosos>, failures=<fallos capturados>)`, sin
     modificar esa función.

  Otras excepciones (ej. `ConfigError` si no se puede cargar
  `config.local.toml` en absoluto) no se capturan: representan un
  problema de configuración del entorno, no un fallo parcial de una
  fuente o agente concretos, y se documentó así explícitamente en el
  docstring de la función.

  `run_analysis_engines` se mantiene **sin cambios** en su firma ni
  comportamiento ("todo o nada" ante el primer fallo), documentado como
  tal para quien lo necesite explícitamente; `investigate` es la nueva
  pieza que ofrece resiliencia ante fallos parciales.

**`tests/test_core_orchestrator.py`** (modificado, reescrito) — se
mantuvieron íntegramente todas las pruebas ya existentes de
`fetch_raw_data`, `fetch_and_normalize`, `run_analysis_engines` y
`assemble_research_result`, y se agregaron pruebas nuevas para
`investigate`:

- Que devuelve un `ResearchResult` completo (dos `analysis_results`, sin
  `failures`) cuando todo el flujo tiene éxito.
- Que captura un fallo de `DataProviderError` (`_FailingProvider`) sin
  propagar la excepción, devolviendo `analysis_results=[]` y un
  `ResearchFailure(stage="data_provider", ...)` con el `ticker`
  normalizado como `identifier`.
- Que captura un fallo de `NormalizationError` (payload incompleto) de
  la misma forma.
- Que, si el agente de salud financiera falla (mock de `requests.post`
  con status 500 en la primera llamada), el agente de valoración
  **igual se invoca** (segunda llamada a `requests.post`) y su
  resultado exitoso queda en `analysis_results`, mientras el fallo del
  primero queda registrado en `failures` con
  `identifier="financial_health"`.
- El caso simétrico: valoración falla, salud financiera se mantiene en
  `analysis_results`.
- Que ambos agentes pueden fallar a la vez, produciendo dos
  `ResearchFailure` (uno por `analysis_id`) y `analysis_results=[]`.
- Que `AgentProviderSelectionError` (configuración incompleta para
  ambos agentes) se captura igual que `AIProviderError`, sin propagarse.
- Que `PromptError` (mockeando `load_prompt` para que falle en el
  agente de salud financiera) se captura igual, dejando que valoración
  se ejecute con éxito.
- Que el `ResearchResult` devuelto por `investigate` es inmutable
  (mismo comportamiento ya heredado de `ResearchResult`).

Nota: igual que en conversaciones anteriores, el archivo se actualizó
en `tests/` (la carpeta declarada en `testpaths` de `pyproject.toml`),
no en `investmentops/tests/` (carpeta duplicada más antigua, fuera de
`testpaths`; ver "Problemas encontrados").

## Decisiones tomadas

- **Un fallo en `fetch_and_normalize` produce un `ResearchResult` con
  `analysis_results=[]` y un único `ResearchFailure`, en vez de no
  producir ningún resultado.** Era la pregunta explícitamente dejada
  abierta en la actualización anterior de este archivo. Se prefirió
  esta opción porque mantiene un tipo de retorno consistente
  (`ResearchResult` siempre, nunca `None` ni una excepción) para quien
  invoque `investigate` (la futura CLI, ver TASKS.md, sección "CLI"),
  y porque es la lectura más directa de "dejarlo explícito en el
  resultado" del texto de la propia tarea.
- **Invocar cada agente por separado dentro de `investigate`, en vez de
  modificar `run_analysis_engines` para que capture sus propios
  fallos.** Ambas alternativas quedaron explícitamente abiertas en la
  actualización anterior. Se prefirió no modificar
  `run_analysis_engines`: varias pruebas ya existentes dependen
  deliberadamente de su comportamiento "todo o nada" (ej.
  `test_run_analysis_engines_does_not_invoke_valuation_if_financial_health_fails`),
  y ese comportamiento sigue siendo válido para quien lo necesite
  explícitamente. Introducir `investigate` como una función nueva evita
  romper ese contrato y dimensiona el cambio a exactamente lo que pide
  la tarea.
- **`identifier` de cada `ResearchFailure` de tipo `analysis_engine` es
  el `analysis_id` del agente** (`"financial_health"` o `"valuation"`,
  reutilizando las constantes `AGENT_ID` ya existentes en cada módulo de
  agente, importadas con alias para evitar colisión de nombres), no un
  texto libre inventado en este módulo — consistente con
  `ResearchFailure.identifier`, documentado en
  `investmentops/core/research_result.py` como "el `analysis_id` del
  agente de análisis que no pudo completarse".
- **No se agregó manejo especial para el caso en que ambos agentes
  fallan.** Se comporta igual que un fallo individual, repetido por
  cada agente: dos `ResearchFailure`, `analysis_results=[]`. No hace
  falta un caso especial porque cada `try/except` es independiente.

## Validación realizada

Revisión manual del código y las pruebas nuevas contra el patrón ya
usado en las pruebas existentes de `run_analysis_engines` (mocks de
`requests.post` con `side_effect` para simular llamadas sucesivas,
alguna exitosa y alguna fallida) y de `assemble_research_result` (mismas
aserciones de inmutabilidad). No se ejecutó la suite completa en este
entorno (Claude Web, sin acceso al repositorio real ni red en el
sandbox); se dejan los archivos para que el usuario los integre y corra
`pytest` localmente.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (se agregó `investigate`;
  `fetch_raw_data`, `NormalizedCompanyData`, `fetch_and_normalize`,
  `run_analysis_engines` y `assemble_research_result` no cambiaron de
  comportamiento, solo se reescribió el docstring del módulo para
  reflejar el estado completo de las 5 tareas de "Orquestador mínimo")
- `tests/test_core_orchestrator.py` (se agregaron pruebas para
  `investigate`; las pruebas ya existentes se mantuvieron)
- `TASKS.md` (quinta y última tarea de "Orquestador mínimo" marcada
  como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/core/__init__.py`
(sigue re-exportando solo `ResearchFailure`/`ResearchResult`; mismo
criterio ya dejado anotado en actualizaciones anteriores),
`investmentops/core/research_result.py`, `investmentops/analysis_engines/`,
`investmentops/ai_providers/`, `investmentops/data_layer/`,
`investmentops/data_providers/` (ningún contrato ni implementación de
capas inferiores cambió), `investmentops/tests/test_core_orchestrator.py`
(versión duplicada más antigua, fuera del `testpaths` declarado en
`pyproject.toml`; no se tocó), ningún otro módulo de código Python
existente.

## Problemas encontrados

Se mantiene el mismo hallazgo ya anotado en actualizaciones anteriores:
el repositorio tiene dos carpetas de pruebas paralelas (`tests/` e
`investmentops/tests/`) con contenido parcialmente duplicado, pero solo
`tests/` está declarada en `testpaths` de `pyproject.toml`. No se
resolvió esta duplicación en esta tarea por el mismo motivo ya
documentado (cambio de alcance distinto, no es un problema
arquitectónico crítico).

## Próxima tarea recomendada

Con "Orquestador mínimo" completo, la siguiente sección sin empezar de
`TASKS.md` es **"CLI"** (Fase 1), cuya primera tarea es:

1. *"Definir la sintaxis del comando de investigación (ej. investigar
   una empresa por ticker)."*

Nota para la próxima conversación:
- Es una tarea de **diseño/documentación** (igual patrón que
  `FINANCIAL_HEALTH_METRICS.md`, `VALUATION_METRICS.md` o `CACHE.md`):
  no se espera código todavía, solo decidir la sintaxis del comando
  (nombre del comando, cómo se pasa el ticker, si hay flags opcionales
  para esta fase) antes de implementar el parseo real en la tarea
  siguiente ("Implementar el parseo del argumento ticker").
- `investigate(ticker, ...)` (`investmentops/core/orchestrator.py`,
  esta conversación) ya es la función de entrada natural que la CLI
  invocará: recibe un ticker y devuelve un `ResearchResult` completo,
  sin dejar escapar fallos parciales de la fuente de datos ni de los
  agentes de análisis. La sintaxis del comando debería considerar cómo
  exponer `config`/`provider` (típicamente `config=None` para que la
  CLI cargue `config.local.toml` por defecto, sin necesidad de un
  parámetro de línea de comandos para esto en el MVP).
- Al definir la sintaxis, considerar que `ARCHITECTURE.md` (componente
  1, "CLI") exige que la CLI "no contiene lógica financiera ni de
  formateo de reportes; delega todo" — la sintaxis debe limitarse a
  qué argumentos recibe el comando, no a cómo se presenta la salida
  (esa es la tarea posterior "Implementar la impresión en consola del
  resultado").
