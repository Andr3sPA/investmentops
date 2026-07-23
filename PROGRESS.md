# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 5, "Reportes" → "Adaptar el generador HTML para soportar un
reporte de comparación (varias empresas) además del reporte
individual." (TASKS.md).

### Qué se implementó

`investmentops/reports/html.py` (modificado): equivalente HTML de
`render_markdown_comparison` (ya implementada en la tarea anterior de
esta misma sección para Markdown).

- `_render_result_body_lines(result)`: se extrajo del cuerpo de
  `render_html` la construcción del título, identidad, fecha y las
  cinco secciones de análisis para un único `ResearchResult`, como
  pieza reutilizable. `render_html` sigue produciendo exactamente el
  mismo documento que antes (esta extracción no cambia su
  comportamiento ni su salida, solo permite reutilizar la lógica sin
  duplicarla).
- `_shift_html_headings(html_fragment)`: desplaza un nivel cada
  `<h1>`/`<h2>` de un fragmento HTML ya renderizado (`<h1>`→`<h2>`,
  `<h2>`→`<h3>`), equivalente HTML de `_shift_markdown_headings`. Los
  `<h3>` ya presentes (ej. "Métricas de soporte") no se tocan.
- `render_html_comparison(tickers, results)`: construye
  `<h1>Comparación: <tickers></h1>` y, para cada `ResearchResult` de
  `results`, reutiliza `_render_result_body_lines` y aplica
  `_shift_html_headings` para anidarlo correctamente bajo el documento
  de comparación, envolviendo todo en un documento HTML5 completo
  (mismo `<style>` embebido y estructura de cabecera ya usados por
  `render_html`).

Misma decisión de formato ya documentada para la versión Markdown
(reutilizar el reporte individual completo de cada empresa, en vez de
una tabla comparativa escalar-por-escalar): el motor de comparables
(`run_comparables_engine`) sigue sin estar conectado a `investigate()`,
y ninguna empresa pierde ninguna de sus cinco secciones.

Recibe `tickers`/`results` sueltos, no un `ComparisonResult`, por el
mismo motivo ya documentado en `render_markdown_comparison`: evitar un
ciclo de importación con `investmentops.core.orchestrator` (que ya
importa `investmentops.reports` para `generate_reports`).

Esta tarea **no** conecta `render_html_comparison` con el orquestador
ni con la CLI: mismo alcance ya documentado para la tarea equivalente
de Markdown.

`investmentops/reports/__init__.py` (modificado): re-exporta
`render_html_comparison` junto a las piezas ya existentes.

`investmentops/tests/test_reports_html_comparison.py` (nuevo): cubre
el título con todos los tickers, el resultado con lista de `results`
vacía (solo el título), el desplazamiento de encabezados (nivel 1 y
nivel 2), la inclusión del contenido completo de cada empresa, la
preservación del orden de las empresas, que los hallazgos de una
empresa no se filtran a la sección de otra, y el escapado del ticker en
título/encabezado.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_html_comparison.py`

Modificados:
- `investmentops/reports/html.py`
- `investmentops/reports/__init__.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Verificación":
- Probar el comando de investigación individual y confirmar que ahora
  incluye la sección de comparables.
- Probar el nuevo comando de comparación con dos empresas reales del
  mismo sector.

(Ambas son tareas de verificación manual, no de implementación; si se
prefiere seguir con implementación, la Fase 5 ya no tiene tareas `[ ]`
pendientes — la siguiente fase con trabajo pendiente es la Fase 6,
"Lecturas por estrategia de inversión".)