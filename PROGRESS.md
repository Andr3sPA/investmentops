# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Reportes" → "Revisar que ninguna sección fusiona las lecturas
en una única recomendación o veredicto." (TASKS.md).

### Qué se implementó

`investmentops/reports/VERDICT_REVIEW.md` (nuevo): documento de
auditoría, no código. Revisa tres frentes para confirmar el
cumplimiento del principio rector de `GOALS.md` ("El sistema informa,
no decide") y del requisito específico de Fase 6 ("opiniones
contrastables entre sí, no como una única verdad"):

1. Los seis prompts que producen texto de análisis
   (`financial_health.md`, `valuation.md`, `value.md`, `growth.md`,
   `quality.md`, `report.md`): todos prohíben explícitamente cualquier
   recomendación de compra/venta o veredicto; los tres de estrategia
   además se autolimitan a su propio marco de interpretación, sin
   presentarse como la única perspectiva válida.
2. Los generadores `investmentops/reports/markdown.py`/`html.py`: cada
   una de las ocho secciones del reporte (incluidas las tres
   subsecciones de "Lecturas por estrategia de inversión") se renderiza
   de forma independiente, sin ningún paso de síntesis, puntuación
   agregada, ni frase de cierre que combine varias lecturas.
   `_render_analysis_body`/`_render_analysis_body_html` (reutilizada
   por salud financiera/valoración y por las tres estrategias) procesa
   un único `AnalysisResult` por invocación, sin posibilidad estructural
   de mezclar dos análisis.
3. Las pruebas ya existentes
   (`test_render_does_not_merge_strategies_into_a_single_reading`, en
   Markdown y HTML) que ya verifican explícitamente esta propiedad.

**Conclusión de la auditoría:** no se encontró ningún punto del sistema
que fusione las distintas lecturas en un veredicto único. No se
requirió ningún cambio de código de producción para esta tarea.

No se modificó ningún módulo de `investmentops/analysis_engines/`,
`investmentops/reports/markdown.py`, `investmentops/reports/html.py` ni
`investmentops/core/orchestrator.py`.

## Archivos creados o modificados

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/reports/VERDICT_REVIEW.md`

## Próxima tarea recomendada

Fase 6, "Verificación" (tareas manuales, no automatizables por
Claude Web):
- "Probar el flujo completo con una empresa real y revisar que las
  distintas lecturas de estrategia aparecen una junto a otra, sin
  mezclarse."
- "Revisar manualmente que el lenguaje usado en las lecturas es
  descriptivo/interpretativo y no prescriptivo ('compra'/'vende')."

Si se prefiere continuar con trabajo automatizable, la Fase 6 queda
completamente cerrada (todas las tareas de código y documentación
marcadas), por lo que la siguiente fase a abordar sería la Fase 7 —
"Registro personal de investigaciones", comenzando por "Definir qué
campos del histórico ya guardado... se expondrán al usuario".