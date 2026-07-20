# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 3, "Reportes" → "Decidir el formato de presentación de la serie
(tabla simple vs. descripción textual) para esta fase" (TASKS.md).

### Qué se implementó

Tarea de diseño/documentación, sin cambios de código. Se creó
`investmentops/reports/TREND_PRESENTATION.md`, que decide cómo se
mostrará en los reportes Markdown/HTML el `AnalysisResult` con
`analysis_id="trend_analysis"` (ya incluido en `ResearchResult` desde la
tarea anterior de Fase 3, "Orquestador"):

- **Tabla simple** (una fila por periodo, columnas de variación de
  ingresos y beneficios en porcentaje con signo, `"—"` si no calculable)
  para `revenue_growth_by_period`/`net_income_growth_by_period`, en vez
  de la lista plana "clave: valor" ya usada por salud financiera/
  valoración — justificado porque esos dos campos son mapeos con un
  elemento por periodo, no escalares.
- Los `findings` (dos oraciones, incluyendo ya la tendencia agregada en
  su texto) y `limitations`/`provenance` siguen el mismo patrón de texto
  ya implementado para las demás secciones, sin cambios de formato.
- Orden dentro de la sección: hallazgos → tabla (omitida si ambos
  mapeos están vacíos) → limitaciones → procedencia centinela.

Documenta explícitamente qué queda fuera: la implementación real en
`markdown.py`/`html.py` (incluyendo que `_find_analysis` en ambos
generadores deberá reconocer `"trend_analysis"`), gráficos/
visualizaciones, y el registro en `run_analysis_engines`.

## Archivos creados o modificados

Creados:
- `investmentops/reports/TREND_PRESENTATION.md`

Modificados:
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: ningún archivo de código (`.py`). Esta tarea es
puramente de diseño/documentación, sobre la base ya implementada en
`investmentops/analysis_engines/trends.py` y
`investmentops/core/orchestrator.py`.

## Próxima tarea recomendada

Fase 3, "Reportes" → "Añadir la sección 'Evolución de ingresos y
beneficios' a la plantilla Markdown, conforme al formato ya decidido."

Implica modificar `investmentops/reports/markdown.py`: `_find_analysis`
deberá reconocer `analysis_id="trend_analysis"` (además de
`"financial_health"`/`"valuation"`), y `render_markdown` deberá agregar
un nuevo bloque `## Evolución de ingresos y beneficios` que vuelque
hallazgos → tabla de variación periodo a periodo (formato ya fijado en
`TREND_PRESENTATION.md`) → limitaciones → procedencia, reutilizando
`_render_analysis_body` donde sea posible y agregando la lógica de tabla
como una pieza nueva.