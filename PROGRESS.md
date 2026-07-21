# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 4, "Reportes" → "Añadir la sección 'Noticias recientes relevantes'
a la plantilla Markdown" (TASKS.md).

### Qué se implementó

`render_markdown` (`investmentops/reports/markdown.py`) ahora agrega el
bloque `## Noticias recientes relevantes` después de `## Evolución de
ingresos y beneficios`, buscando el `AnalysisResult` con
`analysis_id == "news_relevance"` (`NEWS_RELEVANCE_AGENT_ID`) vía
`_find_analysis` (ya genérica, sin cambios).

`TASKS.md` no desglosaba una tarea de diseño separada para el formato de
esta sección (a diferencia de la de tendencia, que sí tuvo su propia
tarea de diseño con `TREND_PRESENTATION.md`); la decisión de formato se
documentó inline en el docstring de `markdown.py`. Como
`supporting_metrics["relevant_news"]` es una lista de dicts con varios
campos de texto libre por noticia (título, resumen, fuente, fecha, URL)
—no escalares como salud financiera/valoración, ni un mapeo por periodo
como tendencia—, se descartó tanto la lista plana "clave: valor" ya
usada por las primeras dos secciones como la tabla ya usada por
tendencia, y se eligió una **lista Markdown**, un ítem por noticia
relevante:
<título> (<fuente>, <fecha ISO 8601>): <resumen> (Leer más)
`_render_news_relevance_body` (nueva) construye esa sección: hallazgos →
lista de noticias (omitida por completo si `relevant_news` está vacía,
igual criterio que la tabla de tendencia cuando ambos mapeos están
vacíos) → limitaciones → procedencia centinela (`ai_provider="none"`,
`ai_model="deterministic"`, ya usada por este motor desde su integración
al orquestador).

Como esta sección se agregó *después* de "Evolución de ingresos y
beneficios", se ajustaron en `test_reports_markdown_trend.py` las
pruebas que asumían que esa sección era la última del documento
(`test_render_keeps_empty_trend_section_when_agent_absent`,
`test_render_places_trend_findings_under_its_own_section`,
`test_render_trend_section_ignores_other_analysis_results`,
`test_render_omits_trend_limitations_subsection_when_empty`,
`test_render_omits_trend_provenance_when_agent_absent`), acotándolas
ahora entre ambos encabezados — mismo tipo de ajuste ya aplicado en su
momento a las pruebas de "Valoración" cuando se agregó la sección de
tendencia (Fase 3).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_markdown_news.py`

Modificados:
- `investmentops/reports/markdown.py` (`NEWS_RELEVANCE_AGENT_ID`,
  `_render_news_relevance_body`, `render_markdown` extendido; docstring
  del módulo actualizado)
- `investmentops/tests/test_reports_markdown_trend.py` (pruebas
  acotadas al nuevo límite de sección, ver arriba)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Reportes" → "Añadir la misma sección [Noticias recientes
relevantes] a la plantilla HTML."