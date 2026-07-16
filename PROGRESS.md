# InvestmentOps — Progreso

**Última actualización:** 2026-07-15

## Última tarea completada

Fase 1 → Orquestador mínimo → *"Implementar el ensamblado de ambos
resultados en un 'Resultado de investigación' único."*

Antes de implementarla, se verificó que no estuviera ya satisfecha:
`ResearchResult`/`ResearchFailure` (`investmentops/core/research_result.py`)
ya existían desde la sección "Contratos e interfaces", y `run_analysis_engines`
ya producía los dos `AnalysisResult` esperados, pero ningún módulo del
proyecto los combinaba efectivamente en un `ResearchResult`. Con esto
continúa la sección "Orquestador mínimo" de TASKS.md (queda pendiente
únicamente la última tarea de esa sección: manejo de fallos parciales).

## Qué se implementó

**`investmentops/core/orchestrator.py`** (modificado) — se agregó:

- **`assemble_research_result(ticker, analysis_results, *, failures=(),
  generated_at=None) -> ResearchResult`** (nueva): recibe el `ticker`
  investigado y la lista de `AnalysisResult` ya producida (típicamente
  el resultado de `run_analysis_engines(...)`), y construye un
  `ResearchResult` completo:
  - **`company`**: una `Company` (investmentops.data_layer.Company)
    **mínima**, con solo el `ticker` recibido (normalizado a
    mayúsculas, mismo criterio que `FMPFundamentalsProvider.fetch` y la
    caché local), dejando `name`, `sector` y `market` como cadenas
    vacías (`""`). Se documentó extensamente en el docstring del módulo
    por qué: ni el payload crudo de FMP ni ningún modelo normalizado de
    la Fase 1 (`FinancialStatement`, `MarketData`) exponen esos campos;
    inventarlos violaría el principio de no inventar datos
    (`ARCHITECTURE.md`, "Manejo de errores y limitaciones"), y hacerlos
    opcionales en `Company` habría sido un cambio de contrato no
    justificado por esta tarea.
  - **`analysis_results`**: los `AnalysisResult` recibidos, tal cual
    (sin recalcular ni reinterpretar nada).
  - **`failures`**: parámetro opcional, por defecto una lista vacía.
    Esta tarea no implementa la detección de fallos parciales (eso es,
    de forma explícita, la última tarea pendiente de "Orquestador
    mínimo"); el parámetro solo deja el ensamblado listo para
    recibirlos.
  - **`generated_at`**: parámetro opcional; si no se indica, se usa
    `datetime.now(timezone.utc)` en el momento de la llamada.
  - `fetch_raw_data`, `NormalizedCompanyData`, `fetch_and_normalize` y
    `run_analysis_engines` se mantienen sin cambios en su firma ni
    comportamiento; se reescribió íntegramente el archivo para agregar
    la nueva función y su documentación, pero el cuerpo de las cuatro
    piezas existentes es idéntico al de la conversación anterior.

**`tests/test_core_orchestrator.py`** (modificado, reescrito) — se
mantuvieron todas las pruebas ya existentes de `fetch_raw_data`,
`fetch_and_normalize` y `run_analysis_engines`, y se agregaron pruebas
nuevas para `assemble_research_result`:

- Que devuelve una instancia de `ResearchResult`.
- Que la `Company` construida solo lleva el `ticker` (normalizado a
  mayúsculas), con `name`/`sector`/`market` vacíos.
- Que `analysis_results` se incluye tal cual se recibió (sin
  transformación).
- Que `failures` es `[]` por defecto, y que acepta una lista explícita
  de `ResearchFailure`.
- Que `generated_at` por defecto cae dentro de una ventana razonable
  alrededor de "ahora" (UTC), y que acepta un valor explícito.
- Que el `ResearchResult` devuelto es inmutable (hereda el
  comportamiento de `investmentops.core.research_result`, ya probado
  por separado en `test_core_research_result.py`).
- Una prueba de punta a punta que encadena `run_analysis_engines(...)`
  (con `requests.post` mockeado) directamente hacia
  `assemble_research_result(...)`, confirmando que la lista de
  `AnalysisResult` se puede pasar sin transformación intermedia.

Nota: igual que en la conversación anterior, el archivo se actualizó en
`tests/` (la carpeta declarada en `testpaths` de `pyproject.toml`), no en
`investmentops/tests/` (carpeta duplicada más antigua, fuera de
`testpaths`; ver "Problemas encontrados" más abajo, ya anotado
previamente).

## Decisiones tomadas

- **`Company` mínima, solo con `ticker`, en vez de rediseñar el modelo
  de dominio o inventar datos.** Es la decisión explícitamente anotada
  como pendiente en la actualización anterior de este archivo ("Próxima
  tarea recomendada"). Se prefirió sobre las alternativas consideradas:
  inventar nombre/sector/mercado (violaría "no inventar datos"), o
  hacer esos campos opcionales en `Company` (cambiaría un contrato ya
  usado y probado en otras partes del sistema, un rediseño no
  justificado por esta tarea puntual). Completar esos campos con datos
  reales queda documentado como fuera de alcance, a resolver en una
  tarea futura si se agrega una fuente que los provea (ej. un endpoint
  de perfil de empresa).
- **`failures` como parámetro opcional con valor por defecto vacío**, no
  como algo que esta función calcule. El texto de la tarea es
  "ensamblar ambos resultados en un... único", no "detectar y manejar
  fallos parciales" (esa es, literalmente, la tarea siguiente en
  TASKS.md). Dejar el parámetro ya presente evita que la tarea de manejo
  de fallos tenga que cambiar la firma de `assemble_research_result`.
- **`generated_at` opcional, con `datetime.now(timezone.utc)` como
  valor por defecto.** Mismo patrón ya usado en otras partes del
  proyecto para fechas de "ahora" (ej. `AnthropicAIProvider.complete`,
  que usa `datetime.now(timezone.utc)` para `AIProviderResponse.
  generated_at`); se deja como parámetro explícito para que las pruebas
  (y una tarea futura que necesite fijar la fecha, ej. para comparar con
  un histórico) no dependan del reloj real.
- **No se agregó una función que encadene `fetch_and_normalize` →
  `run_analysis_engines` → `assemble_research_result` de punta a
  punta.** El texto de esta tarea es específicamente "el ensamblado",
  no "el flujo completo"; además, la tarea siguiente (manejo de fallos
  parciales) probablemente necesite envolver justo esa cadena para
  capturar excepciones de cualquiera de los pasos y traducirlas a
  `ResearchFailure` — introducir esa función ahora se habría adelantado
  a esa tarea y probablemente habría requerido deshacerla o modificarla
  en la siguiente conversación.

## Validación realizada

Revisión manual del código y las pruebas nuevas contra el patrón ya
usado en `test_core_research_result.py` (mismas aserciones de
inmutabilidad y de agregación de `ResearchFailure`/`AnalysisResult`) y
en `test_data_layer_domain.py` (mismo patrón de verificación de campos
de `Company`). No se ejecutó la suite completa en este entorno (Claude
Web, sin acceso al repositorio real ni red en el sandbox); se dejan los
archivos para que el usuario los integre y corra `pytest` localmente.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (se agregó `assemble_research_result`;
  `fetch_raw_data`, `NormalizedCompanyData`, `fetch_and_normalize` y
  `run_analysis_engines` no cambiaron de comportamiento)
- `tests/test_core_orchestrator.py` (se agregaron pruebas para
  `assemble_research_result`; las pruebas ya existentes se mantuvieron)
- `TASKS.md` (cuarta tarea de "Orquestador mínimo" marcada como
  completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/core/__init__.py`
(sigue re-exportando solo `ResearchFailure`/`ResearchResult`; mismo
criterio ya dejado anotado en actualizaciones anteriores — `__init__.py`
re-exporta estructuras de datos, no funciones de orquestación),
`investmentops/data_layer/domain.py` (el modelo `Company` no cambió; se
reutiliza tal cual, con campos vacíos donde no hay datos disponibles),
`investmentops/tests/test_core_orchestrator.py` (versión duplicada más
antigua, fuera del `testpaths` declarado en `pyproject.toml`; no se
tocó), ningún otro módulo de código Python existente.

## Problemas encontrados

Se mantiene el mismo hallazgo ya anotado en la actualización anterior:
el repositorio tiene dos carpetas de pruebas paralelas (`tests/` e
`investmentops/tests/`) con contenido parcialmente duplicado, pero solo
`tests/` está declarada en `testpaths` de `pyproject.toml`. No se
resolvió esta duplicación en esta tarea por el mismo motivo ya
documentado (cambio de alcance distinto, no es un problema
arquitectónico crítico).

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Orquestador mínimo" (TASKS.md), y la
última de esa sección, es:

5. *"Implementar el manejo de fallo del proveedor de datos o del
   proveedor de IA sin detener el resto del flujo, dejándolo explícito
   en el resultado."*

Nota para la próxima conversación:
- Ya existen todas las piezas que esa tarea necesita envolver:
  `fetch_and_normalize` (puede levantar `DataProviderError` o
  `NormalizationError`), `run_analysis_engines` (puede levantar
  `PromptError`, `AgentProviderSelectionError` o `AIProviderError` desde
  cualquiera de los dos agentes) y `assemble_research_result` (ya acepta
  `failures` como parámetro, listo para recibir los `ResearchFailure`
  que esta tarea detecte).
- Esa tarea probablemente deba introducir la función de flujo completo
  que se decidió *no* introducir en esta conversación (ver "Decisiones
  tomadas"): algo como `investigate(ticker, ...) -> ResearchResult` que
  encadene `fetch_and_normalize` → (agente por agente, capturando fallos
  individuales) → `assemble_research_result`, ya que capturar fallos
  parciales de agentes individuales requiere invocar
  `analyze_financial_health`/`analyze_valuation` por separado (no via
  `run_analysis_engines`, que hoy detiene el flujo ante el primer
  fallo) o modificar `run_analysis_engines` para que capture sus propios
  fallos — esa decisión de diseño (modificar `run_analysis_engines` vs.
  introducir una función nueva que no lo use) queda para esa tarea.
- Considerar también si un fallo en `fetch_and_normalize` (antes de
  poder invocar cualquier agente) debe representarse como un
  `ResearchFailure` con `stage="data_provider"` y un `ResearchResult`
  con `analysis_results=[]`, o si en ese caso no tiene sentido producir
  un `ResearchResult` en absoluto — ambas lecturas son coherentes con
  `ARCHITECTURE.md` ("Manejo de errores y limitaciones"), y la tarea
  deberá decidir explícitamente cuál sigue.
