# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 2 → Orquestador y CLI → *"Extender el orquestador para invocar los
generadores de reporte tras ensamblar el resultado de investigación."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: `investigate(...)`
(`investmentops/core/orchestrator.py`) devuelve únicamente un
`ResearchResult`, sin ningún efecto secundario de E/S; nada en el
orquestador invocaba todavía `investmentops.reports.render_markdown`/
`render_html`/`save_markdown_report`/`save_html_report` (todos ya
implementados y probados en tareas anteriores de esta misma fase).

## Qué se implementó

**`investmentops/core/orchestrator.py`** (modificado): se agregan dos
funciones nuevas, sin modificar ninguna de las cinco ya existentes
(`fetch_raw_data`, `fetch_and_normalize`, `run_analysis_engines`,
`assemble_research_result`, `investigate`):

- `generate_reports(result, *, output_dir=None, config=None) -> list[Path]`:
  recibe un `ResearchResult` ya ensamblado y genera + guarda ambos
  formatos de reporte, reutilizando **sin modificarlas** las funciones
  ya existentes de `investmentops.reports`
  (`render_markdown`/`save_markdown_report` y
  `render_html`/`save_html_report`). Devuelve las rutas escritas en el
  orden `[markdown_path, html_path]`. Es la pieza reutilizable para
  cualquier caso de uso futuro que ya tenga un `ResearchResult` a mano
  (no solo el flujo de `investigate`, ej. una futura Fase 7 que
  regenere un reporte desde el histórico).
- `investigate_and_generate_reports(ticker, *, config=None, provider=None, output_dir=None) -> tuple[ResearchResult, list[Path]]`:
  función de conveniencia que encadena `investigate(ticker, ...)` →
  `generate_reports(result, ...)`, devolviendo la tupla
  `(ResearchResult, list[Path])`. Es la función pensada para que la use
  la CLI en las dos tareas siguientes de esta misma sección
  ("--format" y el mensaje final en consola).

**Decisión de diseño clave (documentada en el docstring del módulo):**
`investigate(ticker, ...) -> ResearchResult` **no se modificó**. Varias
piezas del sistema ya dependen de que esa función devuelva únicamente un
`ResearchResult` sin efectos secundarios de E/S (`investmentops.cli.dispatch`,
y todas las pruebas de Fase 1 en `test_core_orchestrator.py`,
`test_cli_dispatch.py`, `test_main.py`). Cambiar su contrato para que
también escribiera archivos habría sido una ruptura innecesaria solo
para cumplir esta tarea; en su lugar, se agregaron las dos funciones
nuevas descritas arriba, dejando `investigate` intacto para quien ya lo
usa, y ofreciendo el flujo extendido (investigación + reportes) como una
opción explícita y separada.

**`investmentops/tests/test_core_orchestrator_reports.py`** (nuevo):
pruebas para `generate_reports` e `investigate_and_generate_reports`:
rutas devueltas en el orden correcto (`[markdown_path, html_path]`),
contenido de ambos archivos coincide con lo ya probado para
`render_markdown`/`render_html`, funciona también cuando el
`ResearchResult` solo tiene fallos parciales (sin `analysis_results`,
mismo comportamiento ya usado por los generadores para secciones
vacías), resolución de `output_dir` desde `config.local.toml` cuando no
se indica explícitamente (reutilizando el mismo mecanismo ya probado en
`test_reports_markdown_save.py`/`test_reports_html_save.py`), y que
`investigate_and_generate_reports` sigue funcionando con solo `ticker` +
`provider` (sin `config` ni `output_dir` explícitos).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_core_orchestrator_reports.py`

Modificados:
- `investmentops/core/orchestrator.py` (se agregan `generate_reports` e
  `investigate_and_generate_reports`; docstring del módulo actualizado
  para reflejar la tarea nueva y la decisión de no modificar
  `investigate`)
- `TASKS.md` (tarea "Extender el orquestador para invocar los
  generadores de reporte tras ensamblar el resultado de investigación"
  marcada como completada, Fase 2, "Orquestador y CLI")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/markdown.py`, `investmentops/reports/html.py`,
`investmentops/reports/__init__.py`, `investmentops/cli/__init__.py`,
`investmentops/__main__.py`, ningún otro módulo de código Python
existente, ningún otro archivo de pruebas existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Fase 2 → Orquestador y CLI → *"Añadir al comando CLI la opción de
formato de salida (markdown, html, o ambos)."*

Esa tarea probablemente querrá extender `build_parser`/`dispatch`
(`investmentops/cli/__init__.py`) con un flag `--format` sobre el
subcomando `investigate`, y conectar `dispatch` con
`investigate_and_generate_reports` (ya implementada en esta tarea) en
vez de `investigate` a secas, cuando el usuario pida generación de
reportes. Justo después queda la última tarea de esta sección:
"Implementar el mensaje final en consola indicando dónde quedaron
guardados los reportes generados", que reutilizaría las rutas ya
devueltas por `generate_reports`/`investigate_and_generate_reports`.
