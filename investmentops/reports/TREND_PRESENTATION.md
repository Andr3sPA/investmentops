# Presentación de "Evolución de ingresos y beneficios" en los reportes (Fase 3)

Cubre la tarea "Decidir el formato de presentación de la serie (tabla
simple vs. descripción textual) para esta fase" (TASKS.md, Fase 3,
"Reportes").

Esta tarea es de **diseño/documentación**, no de código: decide cómo se
mostrará, en los reportes Markdown y HTML, el `AnalysisResult` con
`analysis_id="trend_analysis"` que `investigate` ya incluye en
`ResearchResult.analysis_results` desde la tarea anterior (ver
`investmentops/core/orchestrator.py`,
`_trend_analysis_result_to_analysis_result`). No implementa ninguna
plantilla: eso corresponde a las dos tareas siguientes de esta misma
sección ("Añadir la sección... a la plantilla Markdown" / "...HTML").

## Qué hay disponible para mostrar

El `AnalysisResult` de este agente (ver
`investmentops.analysis_engines.trends.assemble_trend_analysis` y su
conversión en `investmentops/core/orchestrator.py`) trae:

- **`findings`**: dos oraciones en lenguaje natural, una para ingresos y
  otra para beneficios (ej. *"Los ingresos muestran una tendencia
  creciente en los periodos analizados."*), generadas por plantilla
  determinista a partir de la tendencia agregada
  (`detect_revenue_trend`/`detect_net_income_trend`).
- **`supporting_metrics`**: un diccionario con cuatro claves:
  - `revenue_trend` / `net_income_trend`: la tendencia agregada de toda
    la serie (`"creciente"` | `"decreciente"` | `"estable"` | `"mixta"`
    | `None`).
  - `revenue_growth_by_period` / `net_income_growth_by_period`: mapeos
    `{period_end (ISO 8601): variación|None}`, un valor por cada salto
    entre periodos consecutivos de la serie (ver `TREND_METRICS.md`).
- **`limitations`**: advertencias (periodo de un solo punto, periodo
  base en cero, tendencia no determinable, huecos irregulares en el
  calendario).
- **`provenance`**: la procedencia centinela (`ai_provider="none"`,
  `ai_model="deterministic"`), ya cubierta automáticamente por el mismo
  bloque de "Generado por: ..." que usan las demás secciones (ver
  `_render_analysis_body` / `_render_analysis_body_html`).

El punto relevante para esta decisión es `*_growth_by_period`: a
diferencia de `supporting_metrics` de salud financiera o valoración (un
puñado de escalares, ej. `net_margin`, `price_to_earnings`), aquí cada
clave apunta a un **mapeo con un elemento por periodo** — hasta 4
elementos con `limit=5` (el valor por defecto de
`fetch_and_normalize_historical`).

## Por qué una lista plana de "clave: valor" no alcanza aquí

Los generadores ya existentes (`_render_analysis_body` en
`investmentops/reports/markdown.py`, `_render_analysis_body_html` en
`investmentops/reports/html.py`) vuelcan `supporting_metrics` como una
lista de un nivel: `- clave: valor` (Markdown) o `<li>clave: valor</li>`
(HTML). Aplicar ese mismo patrón sin cambios a
`revenue_growth_by_period`/`net_income_growth_by_period` produciría una
línea con el diccionario completo serializado como texto (ej.
`- revenue_growth_by_period: {'2025-12-31': 0.1, '2024-12-31': -0.05}`),
que es técnicamente correcto pero difícil de leer para el usuario final
— justo el tipo de dato para el que `GOALS.md` pide "identificar
tendencias" de forma legible, no una estructura cruda.

## Decisión: tabla simple, una fila por periodo

Para la variación periodo a periodo (`revenue_growth_by_period`/
`net_income_growth_by_period`), el reporte usa una **tabla simple**, no
una descripción puramente textual y no el volcado genérico de
`supporting_metrics` ya usado por las demás secciones:

| Periodo | Ingresos (var.) | Beneficios (var.) |
|---|---|---|
| 2025-12-31 | +8.3% | +8.3% |
| 2024-12-31 | +9.1% | +11.1% |
| 2023-12-31 | -5.3% | -10.0% |

- **Una fila por periodo con variación disponible** (el periodo más
  antiguo de la serie, que no tiene un periodo base anterior, no aparece
  en la tabla — mismo criterio ya aplicado por `RevenueGrowthResult`/
  `NetIncomeGrowthResult`, que solo producen un punto por cada *par*
  consecutivo).
- **Orden:** del periodo más reciente al más antiguo, el mismo orden en
  que ya vienen las claves de `revenue_growth_by_period`/
  `net_income_growth_by_period` (que a su vez respeta el orden de
  `FinancialStatementSeries.statements`, ver su propio docstring).
- **Formato del valor:** porcentaje con un decimal (ej. `+8.3%`,
  `-5.3%`), con signo explícito para que crecimiento/caída sean
  evidentes de un vistazo, sin tener que interpretar el signo del
  número crudo. Si la variación de un periodo es `None` (periodo base en
  cero, ver `TREND_METRICS.md`), la celda muestra `"—"` (no calculable);
  la advertencia correspondiente ya aparece en `limitations`, por lo que
  la tabla no necesita repetir el motivo en cada celda.
- **Markdown:** tabla nativa de Markdown (`| ... | ... |`), consistente
  con que el resto del reporte ya es Markdown estándar y no requiere
  ninguna dependencia nueva (mismo criterio que llevó a no introducir un
  motor de templating en `HTML_TEMPLATE.md`).
- **HTML:** `<table>`/`<tr>`/`<td>` equivalente, con el mismo contenido y
  orden que la tabla Markdown, siguiendo el mismo mapeo elemento-a-
  elemento ya usado entre ambos generadores (ver `HTML_TEMPLATE.md`,
  tabla de mapeo).

## Decisión: los hallazgos y la tendencia agregada siguen siendo texto

`findings` (las dos oraciones ya generadas por `_describe_trend`) y la
tendencia agregada (`revenue_trend`/`net_income_trend`) se presentan tal
como ya lo hacen las demás secciones: los `findings` como párrafo(s) de
texto al inicio del bloque de la sección (igual que salud
financiera/valoración), y `revenue_trend`/`net_income_trend` como parte
de esos mismos hallazgos (el texto ya menciona la palabra "creciente"/
"decreciente"/"estable"/"mixta" explícitamente, ver `_describe_trend`) —
no se duplican como una fila adicional de la tabla ni como una entrada
de lista separada, para no repetir la misma información dos veces en
formatos distintos dentro de la misma sección.

Esto es consistente con `REPORT_SECTIONS.md` (hallazgos → métricas de
soporte → limitaciones → procedencia), solo que la "tabla" sustituye a
la lista plana de "métricas de soporte" únicamente para esta sección,
dado el carácter tabular de sus datos.

## Orden dentro de la sección "Evolución de ingresos y beneficios"

Mismo orden en espíritu que `REPORT_SECTIONS.md` ya fija para "Salud
financiera"/"Valoración", adaptado a lo anterior:

1. Hallazgos (`findings`, dos oraciones).
2. Tabla de variación periodo a periodo (`revenue_growth_by_period` +
   `net_income_growth_by_period` combinadas en una sola tabla, una
   columna por métrica, ver arriba). Si ambos mapeos están vacíos (serie
   de un solo periodo o vacía), se omite la tabla por completo — mismo
   criterio ya usado para omitir "Limitaciones" cuando está vacía en las
   demás secciones — y basta con el hallazgo ya generado ("No hay
   suficientes datos para determinar una tendencia de ...").
3. Limitaciones (`limitations`), igual que las demás secciones.
4. Procedencia (`provenance`, ya centinela: "Generado por: none
   (deterministic) el ..."), igual que las demás secciones — sin cambios
   respecto al patrón ya implementado, reutilizado tal cual.

## Fuera de alcance de esta tarea

- La implementación real de la tabla en `investmentops/reports/markdown.py`
  y `investmentops/reports/html.py`: tareas separadas y siguientes en
  esta misma sección de `TASKS.md`.
- Cualquier gráfico o visualización (sparkline, gráfico de barras): fuera
  de alcance del MVP (`ROADMAP.md`, Fase 3, solo promete "tablas o series
  descritas").
- El registro de este motor en `run_analysis_engines` o en la búsqueda de
  análisis por `analysis_id` en los generadores (`_find_analysis`,
  `_find_analysis` en `html.py`): esas funciones ya buscan por
  `analysis_id` exacto, y `_find_analysis` en ambos generadores tendrá
  que aprender a reconocer `"trend_analysis"`, además de
  `"financial_health"`/`"valuation"` — parte de la tarea de
  implementación siguiente, no de esta decisión de formato.