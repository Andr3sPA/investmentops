# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 4, "Reportes" → "Añadir la misma sección [Noticias recientes
relevantes] a la plantilla HTML" (TASKS.md).

### Qué se implementó

`render_html` (`investmentops/reports/html.py`) ahora agrega el bloque
`<h2>Noticias recientes relevantes</h2>` después de `<h2>Evolución de
ingresos y beneficios</h2>`, buscando el `AnalysisResult` con
`analysis_id == "news_relevance"` (`NEWS_RELEVANCE_AGENT_ID`, nuevo en
este módulo) vía `_find_analysis` (ya genérica, sin cambios).

Siguiendo el mismo criterio ya usado para la sección de tendencia
(`_render_trend_analysis_body_html`, que reemplaza la lista plana
`<ul><li>clave: valor</li></ul>` por una tabla), esta nueva función
`_render_news_relevance_body_html` reemplaza esa misma lista plana por
una lista `<ul>` de noticias, ya que `supporting_metrics["relevant_news"]`
es una lista de dicts con varios campos de texto libre por noticia
(título, resumen, fuente, fecha, URL), no un mapeo por periodo (como
tendencia) ni escalares sueltos (como salud financiera/valoración). Cada
noticia relevante se vuelca como:

```html
<li><strong>título</strong> (fuente, fecha ISO 8601): resumen
    (<a href="url">Leer más</a>)</li>
```

equivalente elemento a elemento a la línea Markdown ya implementada en
`investmentops.reports.markdown._render_news_relevance_body`. Todo el
contenido dinámico (título, fuente, fecha, resumen, url) se escapa con
`html.escape`, mismo criterio ya aplicado en el resto de este generador
(los hallazgos y limitaciones ya vienen de texto libre y no deben
interpretarse como marcado HTML).

`_render_news_relevance_body_html` construye la sección completa:
hallazgos → lista de noticias (omitida por completo si `relevant_news`
está vacía) → limitaciones → procedencia centinela (`ai_provider="none"`,
`ai_model="deterministic"`, ya usada por este motor desde su integración
al orquestador en la Fase 4).

Con esta tarea, ambos generadores (Markdown y HTML) quedan alineados:
las cuatro secciones de análisis (salud financiera, valoración,
evolución de ingresos y beneficios, noticias recientes relevantes) ya
se vuelcan en ambos formatos, en el mismo orden.

## Archivos creados o modificados

Modificados:
- `investmentops/reports/html.py` (`NEWS_RELEVANCE_AGENT_ID`,
  `_render_news_relevance_body_html`, `render_html` extendido; docstring
  del módulo actualizado)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Verificación":
- Probar el flujo con una empresa que tenga noticias recientes y revisar
  que aparecen en el reporte con su fuente y fecha.
- Probar el flujo con una empresa sin noticias recientes y revisar que
  el reporte lo indica explícitamente en vez de omitirlo en silencio.

(Estas son tareas de verificación manual, no de código; la siguiente
tarea de implementación real sería el inicio de la Fase 5, "Comparar con
empresas similares".)