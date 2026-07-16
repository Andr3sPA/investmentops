# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 1 → CLI → *"Conectar el comando con el orquestador."*

## Verificación previa (sin duplicar trabajo)

Antes de implementar, se confirmó que esta tarea **no** estaba satisfecha
todavía: `investmentops/cli/__init__.py` solo exponía `build_parser` y
`parse_args` (parseo y validación del ticker), sin ningún punto de
conexión con `investmentops.core.orchestrator.investigate`, y
`investmentops/__main__.py` solo probaba la carga de
`config.local.toml`. El resto de piezas necesarias para esta tarea
(`investigate(ticker, config=None, provider=None)`, ya con manejo de
fallos parciales) ya existían completas desde la sección "Orquestador
mínimo" (ver entradas anteriores de este archivo). Por lo tanto, esta
tarea sí requería código nuevo.

## Qué se implementó

**`investmentops/cli/__init__.py`** (modificado) — se agregó:

- `dispatch(args, *, config=None, provider=None) -> ResearchResult`:
  recibe el `argparse.Namespace` ya producido por `parse_args` y, para
  el subcomando `"investigate"`, invoca
  `investmentops.core.orchestrator.investigate(args.ticker, config=config,
  provider=provider)`, devolviendo el `ResearchResult` obtenido sin
  transformarlo. `config`/`provider` son parámetros opcionales,
  pensados sobre todo para pruebas (para no depender de un
  `config.local.toml` real en disco ni de una llamada de red real); en
  uso normal ambos se dejan en `None` y `investigate` resuelve la
  configuración real y el proveedor por defecto (FMP) por sí mismo. Si
  `args.command` no es un comando reconocido, levanta `ValueError` como
  salvaguarda defensiva (no debería ocurrir en la práctica, ya que
  `argparse` ya exige un subcomando válido).
- Deliberadamente, `dispatch` **no imprime nada en consola** y **no
  traduce ningún error**: `investigate(...)` ya captura
  `DataProviderError`, `NormalizationError`, `PromptError`,
  `AgentProviderSelectionError` y `AIProviderError` como
  `ResearchFailure` dentro del propio `ResearchResult` (ver
  `investmentops/core/orchestrator.py`); lo único que puede seguir
  escapando (ej. `ConfigError` si falta `config.local.toml` por
  completo) se propaga tal cual desde `dispatch`, sin envolver. Decidir
  qué se imprime y qué mensaje legible mostrar ante ese tipo de fallo
  son las dos tareas siguientes de la misma sección, intencionalmente
  separadas.
- `build_parser`, `parse_args` y `_validate_ticker` no cambiaron de
  comportamiento; solo se actualizó el docstring del módulo para
  reflejar el alcance de la nueva pieza (`dispatch`).

**`investmentops/tests/test_cli_dispatch.py`** (nuevo) — cubre:
- `dispatch` con el subcomando `investigate` devuelve un `ResearchResult`
  con ambos análisis completados (usando un `DataProvider` de prueba y
  mockeando `requests.post` de Anthropic, mismo patrón ya usado en
  `test_core_orchestrator.py`).
- El ticker parseado (`args.ticker`) se pasa tal cual al proveedor
  inyectado, sin normalizar a mayúsculas (esa normalización sigue
  ocurriendo más abajo en el pipeline, no en `dispatch`).
- Un fallo del proveedor de datos (`DataProviderError`) se traduce a un
  `ResearchFailure` dentro del `ResearchResult` devuelto, sin que
  `dispatch` levante ninguna excepción.
- `dispatch` levanta `ValueError` ante un comando no reconocido
  (salvaguarda defensiva).

## Decisiones tomadas

- **`dispatch` vive en `investmentops/cli/__init__.py`, no en
  `investmentops/__main__.py`.** `investmentops/__main__.py` sigue sin
  tocarse: hoy solo prueba la carga de configuración como humo del
  entorno, y conectar ese punto de entrada real al flujo completo
  (parsear → `dispatch` → imprimir) corresponde de forma más natural a
  cuando también exista la impresión en consola (tarea siguiente), para
  no dejar un `__main__.py` a medias que llama al orquestador pero no
  muestra nada útil todavía.
- **Firma simétrica a `investigate(...)`.** `dispatch` expone los mismos
  parámetros opcionales `config`/`provider` que ya tiene `investigate`,
  en vez de ocultarlos, para que las pruebas (y cualquier futuro llamador
  que lo necesite) puedan inyectar un proveedor/configuración de prueba
  sin depender de I/O real, mismo criterio ya aplicado en todo el resto
  del proyecto (`fetch_raw_data`, `fetch_and_normalize`, etc.).
- **Sin impresión ni manejo de errores en esta tarea.** Aunque hubiera
  sido tentador imprimir el `ResearchResult` directamente desde
  `dispatch` para "ver algo" de inmediato, `TASKS.md` separa
  explícitamente esa responsabilidad en la tarea siguiente
  ("Implementar la impresión en consola del resultado"). Mezclarlas
  hubiera hecho esta tarea más grande de lo necesario y hubiera
  duplicado trabajo de diseño (formato de impresión) que corresponde a
  otra tarea.
- **`ValueError` para comando desconocido, no una excepción propia
  nueva.** No existe hoy ningún caso de uso real en el que `args.command`
  llegue a `dispatch` con un valor fuera de `{"investigate"}` (`argparse`
  ya lo impide), por lo que introducir una jerarquía de excepciones
  específica para este caso sería sobre-diseño; `ValueError` es
  suficientemente claro como salvaguarda defensiva.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_cli_dispatch.py` (nuevo)

Modificados:
- `investmentops/cli/__init__.py` (se agregó `dispatch`; se actualizó el
  docstring del módulo)
- `TASKS.md` (tarea "Conectar el comando con el orquestador" marcada
  como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/cli/CLI.md`,
`investmentops/core/orchestrator.py`, `investmentops/__main__.py`,
ningún otro módulo de código Python existente.

## Problemas encontrados

Ninguno. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`); el archivo de pruebas nuevo de esta tarea se
colocó en `investmentops/tests/`, consistente con el resto de módulos de
código de la Fase 1.

## Próxima tarea recomendada

La siguiente tarea sin marcar en `TASKS.md`, sección "CLI", es:

5. *"Implementar la impresión en consola del resultado (texto simple,
   sin formato de reporte todavía)."*

Nota para la próxima conversación:
- Ya existe `dispatch(args, ...)` en `investmentops/cli/__init__.py`,
  que devuelve un `ResearchResult` completo (con `company`,
  `analysis_results` y `failures`). Esta tarea debe decidir e
  implementar cómo se imprime ese objeto en consola como texto simple
  (sin plantillas de reporte, eso es la Fase 2): probablemente una
  función nueva (ej. `format_research_result` o similar) que recorra
  `analysis_results` (mostrando `analysis_id`, `findings`,
  `supporting_metrics`, `limitations`) y, si aplica, mencione
  `failures` de forma explícita.
- Sigue sin conectarse `investmentops/__main__.py` al flujo real
  (parsear → `dispatch` → imprimir): esta tarea es un buen momento para
  hacerlo, ya que la impresión es la pieza que faltaba para que
  `__main__.py` tenga algo útil que mostrar.
- La tarea de mensajes de error legibles ante fallos del flujo (ej.
  `ConfigError` si falta `config.local.toml`) sigue siendo la tarea
  siguiente a esta, intencionalmente separada.
