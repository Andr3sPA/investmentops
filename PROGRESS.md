# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Reportes" → "Añadir la sección 'Lecturas por estrategia de
inversión' a la plantilla Markdown, presentando cada estrategia por
separado." (TASKS.md).

### Qué se implementó

`investmentops/reports/markdown.py` (modificado): se agregó el bloque
`## Lecturas por estrategia de inversión` al final de `render_markdown`,
después de `## Comparables del sector`. Presenta las tres estrategias de
Fase 6 (`value`, `growth`, `quality`), cada una en su propia subsección
de nivel 3 (`### Value investing`, `### Growth investing`, `### Calidad
(quality investing)`), nunca fusionadas entre sí ni con las demás
secciones — conforme al principio de `GOALS.md` de presentar las
lecturas como opiniones contrastables, no como una única verdad.

A diferencia de los motores de tendencia/noticias relevantes/comparables
(que usan procedencia centinela y volcados de `supporting_metrics`
especiales — tabla, lista, estructura anidada), los tres agentes de
estrategia ya invocan un proveedor de IA real y devuelven un
`AnalysisResult` con exactamente la misma forma que "Salud
financiera"/"Valoración" (hallazgos, `supporting_metrics` planos,
limitaciones, `provenance` genuina). Por eso esta sección reutiliza sin
modificarla `_render_analysis_body` (ya genérica), sin escribir ningún
volcado nuevo.

`_STRATEGY_SECTIONS` fija el orden y las etiquetas legibles de las tres
estrategias (`value` → "Value investing", `growth` → "Growth investing",
`quality` → "Calidad (quality investing)"), mismo orden en que se listan
en `STRATEGIES.md`/se invocan en `investigate`. Cada subsección conserva
solo su encabezado vacío si la estrategia correspondiente no está en
`analysis_results` (ej. se investigó con un proveedor de prueba
inyectado, que no las incluye).

No se modificó `investmentops/reports/html.py` (tarea separada y
siguiente de la misma sección), ni ningún motor/agente de
`investmentops/analysis_engines/` ni `investmentops/core/orchestrator.py`
(ya implementados y conectados en tareas previas de Fase 6).

Se agregó `investmentops/tests/test_reports_markdown_strategies.py`.

## Archivos creados o modificados

Modificados:
- `investmentops/reports/markdown.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_reports_markdown_strategies.py`

## Próxima tarea recomendada

Fase 6, "Reportes":
- "Añadir la misma sección [Lecturas por estrategia de inversión] a la
  plantilla HTML."