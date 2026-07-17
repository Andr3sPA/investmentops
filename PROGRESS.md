# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Generador HTML → *"Implementar el volcado de las mismas
secciones que en Markdown (salud financiera, valoración, fuentes)."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: no existía todavía
`investmentops/reports/html.py` ni ninguna función `render_html`. La
tarea anterior (`HTML_TEMPLATE.md`) era puramente de diseño/documentación
y no incluía código.

## Qué se implementó

**`investmentops/reports/html.py`** (nuevo):

- `render_html(result: ResearchResult) -> str`: construye el documento
  HTML5 completo siguiendo exactamente el esqueleto y la tabla de mapeo
  elemento-a-elemento ya fijados en `investmentops/reports/HTML_TEMPLATE.md`:
  `<!DOCTYPE html>`, `<head>` con `<meta charset="utf-8">`, `<title>` con
  el ticker, un bloque `<style>` embebido mínimo (sin CSS externo, sin
  framework), y el cuerpo con el mismo orden de secciones ya usado por
  `render_markdown` (`investmentops/reports/markdown.py`): encabezado
  (`<h1>`, identidad de la empresa si `name`/`sector`/`market` no están
  vacíos, fecha de ensamblado) → `<h2>Salud financiera</h2>` →
  `<h2>Valoración</h2>`.
- `_find_analysis`/`_render_analysis_body_html`: mismo patrón ya usado en
  `investmentops/reports/markdown.py` (buscar el `AnalysisResult` por
  `analysis_id` y volcar, en orden, hallazgos → métricas de soporte →
  limitaciones → procedencia de la interpretación de IA), pero
  **duplicado** en este módulo en vez de importado desde
  `investmentops.reports.markdown`: cada generador de formato es
  independiente (ver `ARCHITECTURE.md`, "Extensibilidad sin
  reescritura" — agregar un formato nuevo no debe tocar los existentes
  ni acoplarlos entre sí).
- **Escapado de contenido dinámico:** todo el texto insertado en el
  marcado (ticker, identidad de la empresa, fecha, hallazgos —que
  provienen de un modelo de lenguaje—, claves/valores de métricas,
  limitaciones, proveedor/modelo de IA) se pasa por `html.escape` antes
  de insertarse, resolviendo así el punto que `HTML_TEMPLATE.md` dejaba
  explícitamente abierto para esta tarea de implementación.
- Encabezados `<h2>Salud financiera</h2>`/`<h2>Valoración</h2>` siempre
  presentes, estén o no disponibles sus respectivos `AnalysisResult`
  (mismo comportamiento que la plantilla base Markdown: una sección sin
  agente disponible conserva solo su encabezado vacío).
- La sección de "Fallos parciales" queda fuera de alcance de esta tarea
  (documentado explícitamente en el docstring del módulo), mismo
  criterio ya aplicado por `render_markdown` (que tampoco la implementa
  todavía).

**`investmentops/reports/__init__.py`** (modificado): se agrega el
re-export de `render_html` desde `investmentops.reports.html`, junto a
los ya existentes de `investmentops.reports.markdown`.

**`investmentops/tests/test_reports_html.py`** (nuevo): pruebas para
`render_html`, siguiendo el mismo patrón ya usado en
`test_reports_markdown.py` — estructura base del documento HTML5,
encabezados siempre presentes, orden de secciones, volcado de hallazgos/
métricas/limitaciones/procedencia por sección (salud financiera y
valoración), comportamiento cuando un agente no completó su análisis, y
un grupo nuevo de pruebas específico de este generador para confirmar el
escapado de caracteres especiales HTML (`<`, `>`, `&`) tanto en el
ticker como en los hallazgos del modelo de IA.

## Archivos creados o modificados

Creados:
- `investmentops/reports/html.py`
- `investmentops/tests/test_reports_html.py`

Modificados:
- `investmentops/reports/__init__.py` (re-exporta `render_html`)
- `TASKS.md` (tarea "Implementar el volcado de las mismas secciones que
  en Markdown (salud financiera, valoración, fuentes)" marcada como
  completada, Fase 2, "Generador HTML")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/markdown.py`, `investmentops/reports/HTML_TEMPLATE.md`,
ningún otro módulo de código Python existente, ningún otro archivo de
pruebas existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Fase 2 → Generador HTML → *"Implementar el guardado del archivo HTML
generado en una ruta local configurable."*

Con `render_html` ya implementado, la siguiente tarea natural es
`save_html_report` en `investmentops/reports/html.py`, siguiendo
exactamente el mismo patrón ya usado por `save_markdown_report`
(`investmentops/reports/markdown.py`): resolver `[output].output_dir`
desde `config.local.toml` (con el mismo `DEFAULT_OUTPUT_DIR`), crear el
directorio si no existe, escribir `<TICKER>.html` (ticker normalizado a
mayúsculas) y señalar `ReportError` (reutilizable desde
`investmentops.reports.markdown`, o una excepción propia equivalente)
ante ticker vacío o fallos de E/S.
