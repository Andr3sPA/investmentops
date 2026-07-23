# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 5, "Reportes" → "Añadir la sección 'Comparables del sector' a la
plantilla Markdown." (TASKS.md).

### Qué se implementó

`investmentops/reports/markdown.py` (modificado): se agregó
`COMPARABLES_AGENT_ID = "comparables"` (mismo criterio de identificador
ya usado para los demás motores, sin importar desde
`investmentops.analysis_engines.comparables` para no acoplar este
generador a la implementación concreta del motor) y tres piezas nuevas:

- `_format_comparable_value`/`_format_comparable_position`: formatean
  valores/posiciones `None` como `"—"`, mismo símbolo ya usado por
  `_format_growth_percentage` para variaciones no calculables de la
  sección de tendencia.
- `_render_comparables_body`: construye la sección "Comparables del
  sector" — hallazgos → métricas propias de la empresa (lista plana
  `- clave: valor`, sin la clave `ticker`, mismo formato ya usado por
  salud financiera/valoración) → tabla comparativa Markdown (una fila
  por combinación métrica/par, tomada de
  `supporting_metrics["comparisons"]`; omitida si ninguna métrica tiene
  comparaciones, es decir, la empresa no tiene pares) → limitaciones →
  procedencia centinela (mismo patrón ya usado por tendencia/noticias
  relevantes).

`render_markdown` ahora agrega el bloque `## Comparables del sector`
después de `## Noticias recientes relevantes`, convirtiéndose en la
nueva última sección del reporte. No se decidió el formato en un
documento `.md` separado (a diferencia de la tendencia, que tuvo
`TREND_PRESENTATION.md`): siguiendo el mismo criterio ya usado para
"Noticias recientes relevantes" (que tampoco tuvo una tarea de diseño
separada en `TASKS.md`), la decisión se documentó inline en el docstring
del módulo.

Esta tarea **no conecta** el motor de posicionamiento relativo
(`run_comparables_engine`) con `investigate()`: hoy ningún
`ResearchResult` real producido por el flujo normal incluye un
`AnalysisResult` con `analysis_id="comparables"` (esa conexión no está
desglosada como tarea explícita en `TASKS.md` para esta sección). La
sección simplemente queda lista para volcar el contenido cuando ese
análisis esté presente, igual que ya ocurrió con salud
financiera/valoración/tendencia/noticias antes de que sus respectivos
motores se conectaran al orquestador.

`investmentops/tests/test_reports_markdown_news.py` (modificado): se
ajustaron `test_render_is_the_last_section_of_the_document` (renombrada
a `test_render_precedes_comparables_section`, ya que "Noticias recientes
relevantes" dejó de ser la última sección) y
`test_render_keeps_empty_news_relevance_section_when_agent_absent`
(acotada ahora por `## Comparables del sector` en vez de tomar todo lo
que sigue hasta el final del documento), junto con las pruebas de
limitaciones/procedencia que también asumían ser la sección final.

`investmentops/tests/test_reports_markdown_comparables.py` (nuevo):
cubre encabezado y ubicación de la sección (después de "Noticias
recientes relevantes", nueva última sección), hallazgos, métricas de la
empresa (presentes/ausentes, sin la clave `ticker`), tabla comparativa
(filas por métrica/par, valores/posiciones no calculables como `"—"`,
tabla omitida sin pares), limitaciones y procedencia centinela.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_markdown_comparables.py`

Modificados:
- `investmentops/reports/markdown.py`
- `investmentops/tests/test_reports_markdown_news.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Reportes":
- "Añadir la misma sección [Comparables del sector] a la plantilla HTML."