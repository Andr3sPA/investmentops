# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Reportes" → "Añadir la misma sección [Lecturas por estrategia
de inversión] a la plantilla HTML." (TASKS.md).

### Qué se implementó

`investmentops/reports/html.py` (modificado): se agregó el bloque
`<h2>Lecturas por estrategia de inversión</h2>` al final de
`_render_result_body_lines` (reutilizada tanto por `render_html` como
por `render_html_comparison`), después de `<h2>Comparables del
sector</h2>`. Presenta las tres estrategias de Fase 6 (`value`,
`growth`, `quality`), cada una en su propia subsección `<h3>` (`<h3>Value
investing</h3>`, `<h3>Growth investing</h3>`, `<h3>Calidad (quality
investing)</h3>`), nunca fusionadas entre sí ni con las demás secciones
— equivalente HTML exacto de la sección ya implementada en
`investmentops/reports/markdown.py` en la tarea anterior.

Igual que en la versión Markdown, esta sección reutiliza sin
modificarla `_render_analysis_body_html` (ya genérica), sin escribir
ningún volcado nuevo, ya que los tres agentes de estrategia ya invocan
un proveedor de IA real y su `AnalysisResult` tiene exactamente la misma
forma que "Salud financiera"/"Valoración" (hallazgos, `supporting_metrics`
planos, limitaciones, `provenance` genuina).

`VALUE_AGENT_ID`/`GROWTH_AGENT_ID`/`QUALITY_AGENT_ID`/`_STRATEGY_SECTIONS`
fijan el orden y las etiquetas legibles de las tres estrategias, mismos
identificadores y mismo orden ya usados en `investmentops/reports/markdown.py`.
Cada subsección conserva solo su encabezado vacío si la estrategia
correspondiente no está en `analysis_results`.

`_shift_html_headings` (usada por `render_html_comparison`) no requirió
ningún cambio: sigue desplazando únicamente `<h1>`/`<h2>`, dejando
intactos los `<h3>` ya existentes (incluidos los nuevos de esta
sección), mismo comportamiento ya usado para "Métricas de soporte"/
"Limitaciones".

No se modificó `investmentops/reports/markdown.py` ni ningún motor/agente
de `investmentops/analysis_engines/` ni `investmentops/core/orchestrator.py`
(ya implementados y conectados en tareas previas de Fase 6).

Se agregó `investmentops/tests/test_reports_html_strategies.py`.

## Archivos creados o modificados

Modificados:
- `investmentops/reports/html.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_reports_html_strategies.py`

## Próxima tarea recomendada

Fase 6, "Reportes":
- "Revisar que ninguna sección fusiona las lecturas en una única
  recomendación o veredicto."