# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 3, "Reportes" → "Añadir la misma sección [Evolución de ingresos y
beneficios] a la plantilla HTML, conforme al formato ya decidido."
(TASKS.md).

### Qué se implementó

Modificado `investmentops/reports/html.py`:

- `TREND_ANALYSIS_AGENT_ID = "trend_analysis"`: nuevo identificador,
  mismo criterio ya usado por `FINANCIAL_HEALTH_AGENT_ID`/
  `VALUATION_AGENT_ID` en este módulo (no se importa desde
  `investmentops.analysis_engines.trends`, consistente con la
  independencia entre generadores ya documentada).
- `_find_analysis` (ya genérica) se reutiliza sin cambios para localizar
  `analysis_id="trend_analysis"`.
- `_format_growth_percentage_html`: equivalente HTML de
  `_format_growth_percentage` (Markdown), misma lógica de formateo con
  signo y `"—"` para `None`.
- `_render_trend_analysis_body_html` (nueva, separada de
  `_render_analysis_body_html` por la misma razón que en Markdown):
  vuelca hallazgos → tabla `<table>` (combinando
  `revenue_growth_by_period`/`net_income_growth_by_period`, omitida si
  ambos mapeos están vacíos) → limitaciones → procedencia. No repite
  `revenue_trend`/`net_income_trend` como lista `<ul>`.
- `render_html`: agrega `<h2>Evolución de ingresos y beneficios</h2>`
  después de `<h2>Valoración</h2>`, mismo comportamiento de encabezado
  vacío cuando el motor no completó su análisis.

### Ajuste a una prueba ya existente

`test_reports_html.py`,
`test_render_keeps_empty_valuation_section_when_agent_absent` asumía que
"Valoración" era la última sección del reporte (tomaba todo el texto
restante hasta `</body>`). Se acotó entre `"<h2>Valoración</h2>"` y
`"<h2>Evolución de ingresos y beneficios</h2>"`, mismo ajuste ya aplicado
a `test_reports_markdown.py` en la tarea anterior.

### Pruebas nuevas

`investmentops/tests/test_reports_html_trend.py` (nuevo): mismo conjunto
de casos ya cubierto en `test_reports_markdown_trend.py`, adaptado al
marcado HTML (encabezado vacío, ubicación después de "Valoración",
hallazgos, tabla `<table>` con filas/porcentajes con signo, celda `"—"`,
omisión completa de la tabla, no duplicación de tendencia agregada como
lista, limitaciones, procedencia centinela).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_html_trend.py`

Modificados:
- `investmentops/reports/html.py`
- `investmentops/tests/test_reports_html.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `investmentops/reports/markdown.py`, ningún motor de
análisis ni el orquestador.

## Próxima tarea recomendada

Fase 4 — "Analizar noticias recientes" → "Fuente de datos de noticias" →
"Elegir el proveedor de noticias a usar para el MVP" (primera tarea
pendiente de la siguiente fase, ya que la Fase 3 queda completa con esta
tarea).