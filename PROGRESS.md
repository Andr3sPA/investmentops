# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 5, "Reportes" → "Adaptar el generador Markdown para soportar un
reporte de comparación (varias empresas) además del reporte
individual." (TASKS.md).

### Qué se implementó

`investmentops/reports/markdown.py` (modificado): se agregaron dos
piezas nuevas y se actualizó el docstring del módulo para documentar la
decisión de formato (no había una tarea de diseño previa y separada
para esta sección, mismo criterio ya usado para "Noticias recientes
relevantes"/"Comparables del sector"):

- `_shift_markdown_headings(markdown_text)`: desplaza un nivel cada
  encabezado Markdown de nivel 1 (`# `) o 2 (`## `) de un texto ya
  renderizado, sumando un `#` adicional a cada uno. Es la única
  transformación necesaria porque `render_markdown` solo produce esas
  dos profundidades de encabezado.
- `render_markdown_comparison(tickers, results)`: construye
  `# Comparación: <tickers>` y, para cada `ResearchResult` de
  `results`, reutiliza `render_markdown(result)` sin modificarlo y
  aplica `_shift_markdown_headings` para anidarlo correctamente bajo el
  documento de comparación (`# Investigación: AAPL` -> `## Investigación:
  AAPL`, `## Salud financiera` -> `### Salud financiera`, etc.).

**Decisión de formato** (documentada en el docstring del módulo):
reutilizar el reporte individual completo de cada empresa, en vez de
una tabla comparativa escalar-por-escalar, porque (1) `compare(...)` no
calcula ningún posicionamiento relativo entre empresas — eso ya existe,
por separado, como el motor de comparables (`run_comparables_engine`),
todavía no conectado a este flujo — y reproducir una tabla aquí
duplicaría, sin datos nuevos, algo que ese motor ya hace mejor; y (2)
ninguna empresa pierde ninguna de sus cinco secciones de análisis.

**Por qué recibe `tickers`/`results` sueltos y no `ComparisonResult`:**
`investmentops.core.orchestrator` (donde vive `ComparisonResult`) ya
importa `investmentops.reports` para `generate_reports`/
`investigate_and_generate_reports`; importar `ComparisonResult` desde
`investmentops.reports.markdown` crearía un ciclo de importación. La
función acepta en su lugar los dos campos sueltos que expone
`ComparisonResult`.

Esta tarea **no** conecta `render_markdown_comparison` con el
orquestador ni con la CLI (ej. un nuevo `--format` para `compare`, o un
`generate_comparison_reports` análogo a `generate_reports`): eso queda
fuera de alcance, mismo criterio ya aplicado a la conexión del motor de
comparables con `investigate()`.

`investmentops/reports/__init__.py` (modificado): re-exporta
`render_markdown_comparison` junto a las piezas ya existentes.

`investmentops/tests/test_reports_markdown_comparison.py` (nuevo):
cubre el título con todos los tickers, el resultado con lista de
`results` vacía (solo el título), el desplazamiento de encabezados
(nivel 1 y nivel 2), la inclusión del contenido completo de cada
empresa, la preservación del orden de las empresas, y que los hallazgos
de una empresa no se filtran a la sección de otra.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_markdown_comparison.py`

Modificados:
- `investmentops/reports/markdown.py`
- `investmentops/reports/__init__.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Reportes":
- "Adaptar el generador HTML para soportar un reporte de comparación
  (varias empresas) además del reporte individual."