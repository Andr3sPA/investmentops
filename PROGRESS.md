# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Generador HTML → *"Implementar el guardado del archivo HTML
generado en una ruta local configurable."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: `investmentops/reports/html.py`
solo tenía `render_html` (volcado de secciones, tarea anterior); no existía
ninguna función de guardado en disco (`save_html_report` o equivalente).

## Qué se implementó

**`investmentops/reports/html.py`** (modificado):

- `save_html_report(ticker, content, *, output_dir=None, config=None) -> Path`:
  guarda el texto HTML ya renderizado por `render_html` en
  `<output_dir>/<TICKER>.html`, siguiendo **exactamente** el mismo patrón
  ya usado por `investmentops.reports.markdown.save_markdown_report`:
  1. Resuelve el directorio de salida (`_resolve_output_dir`, nueva
     función local) en este orden de prioridad: `output_dir` explícito →
     `[output].output_dir` en la configuración cargada → `DEFAULT_OUTPUT_DIR`
     (reutilizado por import desde `investmentops.reports.markdown`, no
     redefinido — misma carpeta de salida que usa el generador Markdown,
     ya que ambos formatos comparten `[output].output_dir` en
     `config.local.toml`).
  2. Crea el directorio con `Path.mkdir(parents=True, exist_ok=True)` si
     no existe.
  3. Escribe `<TICKER>.html` (ticker normalizado a mayúsculas) en UTF-8,
     sobrescribiendo cualquier reporte previo del mismo ticker.
- **Reutiliza `ReportError`** (importada desde
  `investmentops.reports.markdown`, no duplicada como una excepción
  nueva): a diferencia del *renderizado* (`render_html`, que
  deliberadamente no importa nada de `investmentops.reports.markdown`
  para mantener cada formato independiente en su contenido/marcado), el
  *guardado en disco* es infraestructura de E/S idéntica entre formatos
  (crear directorio, resolver ruta, escribir archivo, traducir fallos),
  por lo que compartir la excepción y la constante `DEFAULT_OUTPUT_DIR`
  no viola "Extensibilidad sin reescritura" (`ARCHITECTURE.md`): no hay
  ninguna lógica de presentación acoplada entre los dos generadores, solo
  una pieza de infraestructura común ya extraída y estable. Esta decisión
  queda documentada explícitamente en el docstring del módulo para que no
  se reconsidere sin motivo en una tarea futura.
- Docstring del módulo actualizado para reflejar ambas tareas ya
  completadas de "Generador HTML" (volcado de secciones + guardado en
  disco) y explicar el porqué de la reutilización de `ReportError`/
  `DEFAULT_OUTPUT_DIR` frente a la independencia deliberada del
  renderizado.

**`investmentops/reports/__init__.py`** (modificado): se agrega el
re-export de `save_html_report` desde `investmentops.reports.html`, junto
a los ya existentes (`render_html`, `render_markdown`,
`save_markdown_report`, `ReportError`).

**`investmentops/tests/test_reports_html_save.py`** (nuevo): pruebas para
`save_html_report`, siguiendo el mismo patrón ya usado en
`test_reports_markdown_save.py` — escritura con contenido dado,
normalización del ticker a mayúsculas en el nombre de archivo, creación
del directorio si falta, sobrescritura de un reporte previo del mismo
ticker, rechazo de ticker vacío, lectura de `output_dir` desde
`config.local.toml` cuando no se indica explícitamente, uso de
`DEFAULT_OUTPUT_DIR` cuando la configuración no define `output_dir`, y
dos pruebas nuevas específicas de esta tarea: que Markdown y HTML
comparten el mismo `[output].output_dir` (mismo ticker → misma carpeta,
`<TICKER>.md` y `<TICKER>.html`) y que el `ReportError` levantado por
`save_html_report` es el mismo tipo ya usado por `save_markdown_report`
(no una excepción propia y separada).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_html_save.py`

Modificados:
- `investmentops/reports/html.py` (se agrega `save_html_report` y
  `_resolve_output_dir`; docstring del módulo actualizado)
- `investmentops/reports/__init__.py` (re-exporta `save_html_report`)
- `TASKS.md` (tarea "Implementar el guardado del archivo HTML generado en
  una ruta local configurable" marcada como completada, Fase 2,
  "Generador HTML")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/markdown.py`, `investmentops/reports/HTML_TEMPLATE.md`,
`investmentops/reports/REPORT_MODEL.md`, `investmentops/reports/REPORT_SECTIONS.md`,
`investmentops/tests/test_reports_html.py`, ningún otro módulo de código
Python existente, ningún otro archivo de pruebas existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Fase 2 → Modelo de reporte → *"(Opcional) Escribir el archivo de prompt
del agente de reporte y definir su alcance: solo redacción a partir de
los resultados ya existentes, sin nuevos hallazgos ni veredictos."*

Es la única tarea restante marcada como pendiente antes de la sección
"Generador Markdown"/"Generador HTML" (ambas ya completas) y de
"Orquestador y CLI" (Fase 2). Al ser explícitamente **opcional** en
`TASKS.md`, si se prefiere avanzar directamente a valor de punta a punta,
la siguiente tarea no opcional es Fase 2 → "Orquestador y CLI" →
*"Extender el orquestador para invocar los generadores de reporte tras
ensamblar el resultado de investigación."* Esa tarea probablemente
querrá reutilizar tanto `render_markdown`/`save_markdown_report` como
`render_html`/`save_html_report` (ya ambos completos), decidiendo cómo
`investigate(...)` (o una nueva función que lo envuelva) dispara la
generación de reportes sin romper su contrato actual (que hoy solo
devuelve un `ResearchResult`, sin generar archivos).
