# investmentops/reports/html.py
"""Generador de reportes en HTML.

Cubre, hasta ahora, seis tareas de TASKS.md, Fase 2 ("Generador HTML"),
Fase 3 ("Reportes"), Fase 4 ("Reportes") y Fase 5 ("Reportes"):

- "Implementar el volcado de las mismas secciones que en Markdown (salud
  financiera, valoración, fuentes)." (ya completada, ver PROGRESS.md).
- "Implementar el guardado del archivo HTML generado en una ruta local
  configurable." (ya completada, ver PROGRESS.md).
- "Añadir la misma sección [Evolución de ingresos y beneficios] a la
  plantilla HTML, conforme al formato ya decidido." (ya completada, ver
  PROGRESS.md).
- "Añadir la misma sección [Noticias recientes relevantes] a la
  plantilla HTML." (ya completada, ver PROGRESS.md).
- "Añadir la misma sección [Comparables del sector] a la plantilla
  HTML." (ya completada, ver PROGRESS.md).
- "Adaptar el generador HTML para soportar un reporte de comparación
  (varias empresas) además del reporte individual." (esta tarea).

Sobre la base de diseño ya fijada en `investmentops/reports/HTML_TEMPLATE.md`:
HTML5 mínimo, sin CSS elaborado, sin JavaScript, sin motor de templating
externo, con las mismas secciones y el mismo orden ya usados por el
generador Markdown (`investmentops/reports/markdown.py`), consumiendo
directamente `ResearchResult` sin ningún tipo intermedio nuevo (ver
`investmentops/reports/REPORT_MODEL.md` y `REPORT_SECTIONS.md`).

Este módulo no importa nada de `investmentops.reports.markdown` para la
parte de **renderizado** (`render_html`/`render_html_comparison`):
aunque el contenido y el orden de las secciones son los mismos, cada
generador de formato es independiente (ver ARCHITECTURE.md,
"Extensibilidad sin reescritura" — "Agregar un nuevo formato de salida
implica añadir un generador nuevo, no tocar los existentes"), por lo que
las constantes de identificador de agente (`FINANCIAL_HEALTH_AGENT_ID`,
`VALUATION_AGENT_ID`, `TREND_ANALYSIS_AGENT_ID`,
`NEWS_RELEVANCE_AGENT_ID`, `COMPARABLES_AGENT_ID`) y el helper de
búsqueda (`_find_analysis`) se duplican aquí en vez de importarse, mismo
criterio ya documentado en versiones anteriores de este módulo.

## Sección "Evolución de ingresos y beneficios"

Cubre la tarea "Añadir la misma sección a la plantilla HTML, conforme al
formato ya decidido" (TASKS.md, Fase 3, "Reportes"), equivalente HTML de
la sección ya implementada en
`investmentops.reports.markdown.render_markdown`/
`_render_trend_analysis_body`, sobre el formato fijado en
`investmentops/reports/TREND_PRESENTATION.md`.

`TREND_ANALYSIS_AGENT_ID` (``"trend_analysis"``, el mismo identificador
usado en `investmentops.analysis_engines.trends.AGENT_ID` y propagado por
`investmentops.core.orchestrator._trend_analysis_result_to_analysis_result`)
se reutiliza junto con `_find_analysis` (ya genérica) para localizar el
`AnalysisResult` correspondiente dentro de `ResearchResult.analysis_results`.
Sigue siendo un `AnalysisResult` normal, con una `AnalysisProvenance`
centinela (`ai_provider="none"`, `ai_model="deterministic"`, ver
`investmentops/core/TREND_INTEGRATION.md`), por lo que no requiere ningún
tipo ni contrato nuevo.

A diferencia de "Salud financiera"/"Valoración" (que vuelcan
`supporting_metrics` como una lista `<ul><li>clave: valor</li></ul>`),
esta sección reemplaza esa lista por una tabla `<table>` para las dos
claves que son mapeos por periodo
(`revenue_growth_by_period`/`net_income_growth_by_period`), mismo
contenido y orden que la tabla Markdown ya implementada
(`_render_trend_analysis_body` en `investmentops/reports/markdown.py`).

## Sección "Noticias recientes relevantes"

Cubre la tarea "Añadir la misma sección a la plantilla HTML" (TASKS.md,
Fase 4, "Reportes"), equivalente HTML de la sección ya implementada en
`investmentops.reports.markdown.render_markdown`/
`_render_news_relevance_body`, sobre el formato decidido inline en el
docstring de `markdown.py` ("Sección 'Noticias recientes relevantes'").

`NEWS_RELEVANCE_AGENT_ID` (``"news_relevance"``, el mismo identificador
usado en `investmentops.analysis_engines.news_relevance.AGENT_ID` y
propagado tal cual por
`investmentops.core.orchestrator._news_relevance_result_to_analysis_result`
al convertir su resultado a `AnalysisResult`) se reutiliza junto con
`_find_analysis` (ya genérica) para localizar el `AnalysisResult`
correspondiente. Es un `AnalysisResult` normal, con una
`AnalysisProvenance` centinela (`ai_provider="none"`,
`ai_model="deterministic"`, mismo criterio ya justificado en
`TREND_INTEGRATION.md` y reutilizado sin una nueva decisión de diseño
para este motor).

Igual que en la versión Markdown, `supporting_metrics["relevant_news"]`
es una lista de dicts (`title`, `summary`, `source`, `published_at`,
`url`), no un mapeo por periodo (a diferencia de la tabla de tendencia)
ni un puñado de escalares (a diferencia de salud financiera/valoración).
Esta sección usa una **lista HTML** (`<ul><li>`), un ítem por noticia
relevante, equivalente elemento a elemento a la lista Markdown ya
implementada.

## Sección "Comparables del sector"

Cubre la tarea "Añadir la misma sección [Comparables del sector] a la
plantilla HTML" (TASKS.md, Fase 5, "Reportes"), equivalente HTML de la
sección ya implementada en `investmentops.reports.markdown.render_markdown`/
`_render_comparables_body`, sobre el formato decidido inline en el
docstring de `markdown.py` ("Sección 'Comparables del sector'").

`COMPARABLES_AGENT_ID` (``"comparables"``, el mismo identificador usado
en `investmentops.analysis_engines.comparables.AGENT_ID` y propagado tal
cual por
`investmentops.core.orchestrator._comparables_analysis_result_to_analysis_result`
al convertir su resultado a `AnalysisResult`) se reutiliza junto con
`_find_analysis` (ya genérica) para localizar el `AnalysisResult`
correspondiente. Es un `AnalysisResult` normal, con una
`AnalysisProvenance` centinela (`ai_provider="none"`,
`ai_model="deterministic"`), mismo criterio ya usado por los motores de
tendencia y noticias relevantes: este motor tampoco invoca ningún
proveedor de IA.

`supporting_metrics` de este motor tiene la forma `{"company": {...},
"comparisons": {...}}` (ver
`investmentops.analysis_engines.comparables.assemble_comparables_analysis`),
distinta de las demás secciones. Esta sección la vuelca en dos partes,
equivalente elemento a elemento a `_render_comparables_body`
(`investmentops/reports/markdown.py`):

1. **Métricas de la empresa** (`supporting_metrics["company"]`, sin la
   clave `"ticker"`): volcadas como lista `<ul><li>clave: valor</li></ul>`,
   mismo formato ya usado por "Salud financiera"/"Valoración".
2. **Tabla comparativa** (`supporting_metrics["comparisons"]`): una
   `<table>` con una fila por combinación (métrica, par), columnas
   `Métrica | Par | Valor empresa | Valor par | Posición`. Valores y
   posiciones `None` se muestran como `"—"` (`_format_comparable_value_html`/
   `_format_comparable_position_html`), mismo símbolo ya usado por la
   tabla de tendencia. La tabla se omite por completo si ninguna métrica
   tiene comparaciones (la empresa no tiene pares).

Orden dentro de la sección, igual que en la versión Markdown: hallazgos
→ métricas de la empresa (omitida si no hay ninguna) → tabla comparativa
(omitida si no hay pares) → limitaciones → procedencia.

Esta tarea no conecta el motor de posicionamiento relativo
(`run_comparables_engine`) con `investigate()`: mismo alcance ya
documentado para la tarea equivalente de Markdown.

## Reporte de comparación (varias empresas, esta tarea)

Cubre la tarea "Adaptar el generador HTML para soportar un reporte de
comparación (varias empresas) además del reporte individual" (TASKS.md,
Fase 5, "Reportes"). Equivalente HTML de
`investmentops.reports.markdown.render_markdown_comparison`, sobre la
misma decisión de formato ya documentada en ese módulo (reutilizada
aquí sin una nueva decisión de diseño: no hay ninguna tarea de diseño
separada para este reporte en `TASKS.md`, y la razón para no producir
una tabla comparativa escalar-por-escalar —el motor de comparables
todavía no está conectado a `investigate()`, y ninguna empresa debe
perder ninguna de sus cinco secciones— aplica igual en HTML que en
Markdown).

### Por qué se extrae `_render_result_body_lines`

`render_html` construía, hasta esta tarea, el cuerpo de un único
`ResearchResult` (título, identidad, fecha, y las cinco secciones)
directamente dentro de su propio cuerpo de función, antes de envolverlo
en el documento HTML5 completo (`<!DOCTYPE html>` ... `</html>`). Para
anidar varios reportes completos bajo un único documento de comparación
sin duplicar esa lógica de volcado, esa construcción se extrajo a
`_render_result_body_lines(result) -> list[str]`, reutilizada tanto por
`render_html` (que la envuelve en su propio documento) como por
`render_html_comparison` (que la envuelve, ya con los encabezados
desplazados, dentro de un único documento de comparación). Este cambio
es puramente una extracción de función: `render_html` no cambia su
comportamiento ni su salida.

### Desplazamiento de encabezados (`_shift_html_headings`)

Equivalente HTML de
`investmentops.reports.markdown._shift_markdown_headings`: transforma
cada `<h1>`/`</h1>` en `<h2>`/`</h2>`, y cada `<h2>`/`</h2>` en
`<h3>`/`</h3>` (el orden de las dos sustituciones importa: primero
`<h2>`→`<h3>`, luego `<h1>`→`<h2>`, para no desplazar dos veces el mismo
encabezado). Los `<h3>` ya presentes en el fragmento (ej. "Métricas de
soporte", "Limitaciones") no se tocan — mismo criterio que la versión
Markdown, que solo desplaza los dos niveles que produce el reporte
individual (`#`/`##`), dejando intacto cualquier nivel más profundo.

### Por qué recibe `tickers`/`results` sueltos y no un `ComparisonResult`

Mismo motivo ya documentado en `investmentops.reports.markdown.render_markdown_comparison`:
`investmentops.core.orchestrator` ya importa `investmentops.reports`
(`render_markdown`, `render_html`, `save_markdown_report`,
`save_html_report`) para `generate_reports`/
`investigate_and_generate_reports`; importar `ComparisonResult` desde
este módulo crearía un ciclo de importación. Esta función acepta los dos
campos sueltos que expone `ComparisonResult` (`tickers`, `results`).

Fuera de alcance de esta tarea:
- Conectar `render_html_comparison`/`save_html_report` con el
  orquestador o con la CLI (ej. un nuevo `--format` para `compare`, o un
  `generate_comparison_reports`): no forma parte de esta tarea, mismo
  alcance ya documentado para la tarea equivalente de Markdown.
- Cualquier tabla comparativa escalar-por-escalar entre las empresas
  comparadas: ya existe, por separado, como el motor de comparables
  (Fase 5), no conectado a este flujo.

## Guardado del archivo HTML generado (`save_html_report`)

A diferencia del renderizado, el **guardado en disco** sí reutiliza
piezas ya existentes de `investmentops.reports.markdown`
(`ReportError`, `DEFAULT_OUTPUT_DIR`): guardar un archivo en una ruta
local configurable es una operación de infraestructura (crear
directorio, resolver ruta de salida, escribir archivo, traducir fallos
de E/S) idéntica para cualquier formato de reporte, no una decisión de
presentación específica del formato — a diferencia de `render_html` vs
`render_markdown`, que sí difieren en contenido/marcado. Reimplementar
esa infraestructura aquí duplicaría lógica sin ningún beneficio de
independencia real entre formatos: extensibilidad no exige rehacer código
idéntico.

`save_html_report` sigue exactamente el mismo patrón ya usado por
`investmentops.reports.markdown.save_markdown_report`:

1. **Resolución de la ruta de destino**, en este orden de prioridad:
   - `output_dir` recibido explícitamente (útil sobre todo para pruebas).
   - `[output].output_dir` en la configuración ya cargada (`config`) o,
     si tampoco se indica, en `investmentops.config.load_config()`.
   - `DEFAULT_OUTPUT_DIR` (``"reports/"``, reutilizado desde
     `investmentops.reports.markdown`) si ninguna de las anteriores
     aplica.
2. **Creación del directorio** si no existe
   (`Path.mkdir(parents=True, exist_ok=True)`).
3. **Nombre del archivo:** `<TICKER>.html`, con el ticker normalizado a
   mayúsculas, consistente con `<TICKER>.md` (Markdown) y `<TICKER>.json`
   (caché de datos normalizados).
4. **Escritura del archivo** en UTF-8, sobrescribiendo por completo
   cualquier contenido previo del mismo ticker.

Cualquier fallo (ticker vacío, fallo de E/S al crear el directorio o al
escribir el archivo) se señala mediante `ReportError` — la misma
excepción ya definida en `investmentops.reports.markdown`, reutilizada
aquí en vez de definir un duplicado (`HtmlReportError` u otro nombre):
ambos generadores comparten el mismo tipo de fallo de guardado
(infraestructura de E/S, no de renderizado), y quien invoque cualquiera
de los dos `save_*_report` puede capturar `ReportError` de forma
uniforme.

Fuera de alcance de este módulo:
- La sección de "Fallos parciales": no forma parte del mapeo de esta
  tarea (ver docstring de `render_html`, ya documentado en versiones
  anteriores de este módulo).
- Conectar `save_html_report` con el orquestador o con la CLI para que
  se invoque automáticamente tras ensamblar el resultado de
  investigación: ya conectado desde Fase 2 (ver
  `investmentops.core.orchestrator.generate_reports`).
- Conectar el motor de comparables (`run_comparables_engine`) con
  `investigate()`: mismo alcance ya documentado para la tarea
  equivalente de Markdown.
- Gráficos o visualizaciones de la serie o de noticias: fuera de alcance
  del MVP.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Sequence

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.config import load_config
from investmentops.core.research_result import ResearchResult
from investmentops.reports.markdown import DEFAULT_OUTPUT_DIR, ReportError

#: Identificador del agente de salud financiera, el mismo usado en
#: `investmentops.analysis_engines.financial_health.AGENT_ID`. No se
#: importa directamente desde ese módulo (ver docstring del módulo,
#: "no se importa nada de investmentops.reports.markdown" aplica al
#: renderizado: basta con el identificador de texto, ya estable como
#: parte de `AnalysisResult.analysis_id`).
FINANCIAL_HEALTH_AGENT_ID = "financial_health"

#: Identificador del agente de valoración, mismo criterio que
#: `FINANCIAL_HEALTH_AGENT_ID`.
VALUATION_AGENT_ID = "valuation"

#: Identificador del motor de evolución de ingresos y beneficios, el
#: mismo usado en `investmentops.analysis_engines.trends.AGENT_ID` (y
#: propagado tal cual por
#: `investmentops.core.orchestrator._trend_analysis_result_to_analysis_result`
#: al convertir su resultado a `AnalysisResult`). Mismo criterio que los
#: dos identificadores anteriores: no se importa desde el módulo del
#: motor para no acoplar este generador a su implementación concreta.
TREND_ANALYSIS_AGENT_ID = "trend_analysis"

#: Identificador del motor de noticias relevantes, el mismo usado en
#: `investmentops.analysis_engines.news_relevance.AGENT_ID` (y propagado
#: tal cual por
#: `investmentops.core.orchestrator._news_relevance_result_to_analysis_result`
#: al convertir su resultado a `AnalysisResult`). Mismo criterio que los
#: identificadores anteriores: no se importa desde el módulo del motor
#: para no acoplar este generador a su implementación concreta.
NEWS_RELEVANCE_AGENT_ID = "news_relevance"

#: Identificador del motor de posicionamiento relativo, el mismo usado
#: en `investmentops.analysis_engines.comparables.AGENT_ID` (y propagado
#: tal cual por
#: `investmentops.core.orchestrator._comparables_analysis_result_to_analysis_result`
#: al convertir su resultado a `AnalysisResult`). Mismo criterio que los
#: identificadores anteriores: no se importa desde el módulo del motor
#: para no acoplar este generador a su implementación concreta.
COMPARABLES_AGENT_ID = "comparables"

#: Bloque `<style>` mínimo embebido, tal como lo fija `HTML_TEMPLATE.md`:
#: tipografía de sistema, ancho máximo legible, espaciado básico. Sin
#: hoja de estilos externa ni framework CSS.
_EMBEDDED_STYLE = (
    "body { font-family: system-ui, sans-serif; max-width: 800px; "
    "margin: 2rem auto; padding: 0 1rem; }\n"
    "    h1, h2 { border-bottom: 1px solid #ccc; padding-bottom: 0.25rem; }"
)


def _find_analysis(
    result: ResearchResult, analysis_id: str
) -> AnalysisResult | None:
    """Busca, dentro de `result.analysis_results`, el análisis con `analysis_id`.

    Devuelve ``None`` si ese agente no completó su análisis (no aparece
    en la lista), en cuyo caso la sección correspondiente del reporte
    conserva solo su encabezado vacío. Misma semántica que la función
    equivalente en `investmentops.reports.markdown`, duplicada aquí por
    independencia entre generadores (ver docstring del módulo). Funciona
    igual para cualquier `analysis_id` (``"financial_health"``,
    ``"valuation"``, ``"trend_analysis"``, ``"news_relevance"``,
    ``"comparables"``), sin acoplarse a ninguno.
    """
    return next(
        (analysis for analysis in result.analysis_results if analysis.analysis_id == analysis_id),
        None,
    )


def _render_analysis_body_html(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas HTML de hallazgos, métricas, limitaciones y
    procedencia de IA de un análisis.

    Orden fijado en `REPORT_SECTIONS.md`/`HTML_TEMPLATE.md`: hallazgos →
    métricas de soporte → limitaciones → procedencia de la interpretación
    de IA. Reutilizada tanto para "Salud financiera" como para
    "Valoración" (no depende del `analysis_id` concreto). No se usa para
    "Evolución de ingresos y beneficios", "Noticias recientes
    relevantes" ni "Comparables del sector": esas secciones reemplazan el
    volcado plano de `supporting_metrics` por una tabla o una lista (ver
    `_render_trend_analysis_body_html`,
    `_render_news_relevance_body_html`,
    `_render_comparables_body_html`). Todo el contenido dinámico se
    escapa con `html.escape` antes de insertarse.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(f"<p>{escape(finding)}</p>")

    if analysis.supporting_metrics:
        lines.append("<h3>Métricas de soporte</h3>")
        lines.append("<ul>")
        for key, value in analysis.supporting_metrics.items():
            lines.append(f"<li>{escape(str(key))}: {escape(str(value))}</li>")
        lines.append("</ul>")

    if analysis.limitations:
        lines.append("<h3>Limitaciones</h3>")
        lines.append("<ul>")
        for limitation in analysis.limitations:
            lines.append(f"<li>{escape(limitation)}</li>")
        lines.append("</ul>")

    provenance = analysis.provenance
    lines.append(
        "<p><em>Generado por: "
        f"{escape(provenance.ai_provider)} ({escape(provenance.ai_model)}) "
        f"el {escape(provenance.generated_at.isoformat())}</em></p>"
    )

    return lines


def _format_growth_percentage_html(value: Any) -> str:
    """Formatea una variación relativa (ej. ``0.083``) como porcentaje con signo.

    Equivalente HTML de
    `investmentops.reports.markdown._format_growth_percentage` (misma
    lógica, duplicada aquí por independencia entre generadores, ver
    docstring del módulo). Devuelve ``"—"`` si `value` es ``None``
    (periodo base en cero, ver `TREND_METRICS.md`), conforme a
    `TREND_PRESENTATION.md`, "Formato del valor".
    """
    if value is None:
        return "—"
    return f"{value * 100:+.1f}%"


def _render_trend_analysis_body_html(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas HTML de la sección "Evolución de ingresos y beneficios".

    Orden fijado en `TREND_PRESENTATION.md`: hallazgos → tabla `<table>`
    de variación periodo a periodo (omitida si no hay datos) →
    limitaciones → procedencia de IA (centinela). A diferencia de
    `_render_analysis_body_html`, `supporting_metrics` no se vuelca como
    lista `<ul>`: las claves `revenue_growth_by_period`/
    `net_income_growth_by_period` (mapeos con un elemento por periodo) se
    combinan en una única tabla, una fila por periodo. Las claves
    `revenue_trend`/`net_income_trend` (tendencia agregada) no se repiten
    aparte: ya están incluidas en el texto de `findings` (ver
    `investmentops.analysis_engines.trends._describe_trend`). Todo el
    contenido dinámico se escapa con `html.escape` antes de insertarse.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(f"<p>{escape(finding)}</p>")

    revenue_by_period: dict[str, Any] = analysis.supporting_metrics.get(
        "revenue_growth_by_period", {}
    )
    net_income_by_period: dict[str, Any] = analysis.supporting_metrics.get(
        "net_income_growth_by_period", {}
    )

    if revenue_by_period or net_income_by_period:
        lines.append("<table>")
        lines.append(
            "<tr><th>Periodo</th><th>Ingresos (var.)</th>"
            "<th>Beneficios (var.)</th></tr>"
        )
        for period_end in revenue_by_period:
            revenue_growth = revenue_by_period.get(period_end)
            net_income_growth = net_income_by_period.get(period_end)
            lines.append(
                f"<tr><td>{escape(str(period_end))}</td>"
                f"<td>{escape(_format_growth_percentage_html(revenue_growth))}</td>"
                f"<td>{escape(_format_growth_percentage_html(net_income_growth))}</td></tr>"
            )
        lines.append("</table>")

    if analysis.limitations:
        lines.append("<h3>Limitaciones</h3>")
        lines.append("<ul>")
        for limitation in analysis.limitations:
            lines.append(f"<li>{escape(limitation)}</li>")
        lines.append("</ul>")

    provenance = analysis.provenance
    lines.append(
        "<p><em>Generado por: "
        f"{escape(provenance.ai_provider)} ({escape(provenance.ai_model)}) "
        f"el {escape(provenance.generated_at.isoformat())}</em></p>"
    )

    return lines


def _render_news_relevance_body_html(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas HTML de la sección "Noticias recientes relevantes".

    Orden: hallazgos → lista `<ul>` de noticias relevantes (omitida si no
    hay ninguna) → limitaciones → procedencia de IA (centinela). Mismo
    criterio que `_render_trend_analysis_body_html`: `supporting_metrics`
    no se vuelca como lista plana `clave: valor`, ya que la clave
    `relevant_news` es una lista de dicts (título, resumen, fuente,
    fecha, URL por noticia), no un escalar ni un mapeo por periodo. Cada
    noticia relevante se vuelca como un ítem `<li>`, equivalente HTML de
    la línea Markdown ya implementada en
    `investmentops.reports.markdown._render_news_relevance_body`. Todo el
    contenido dinámico (título, fuente, fecha, resumen, url) se escapa
    con `html.escape` antes de insertarse.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(f"<p>{escape(finding)}</p>")

    relevant_news: list[dict[str, Any]] = analysis.supporting_metrics.get(
        "relevant_news", []
    )

    if relevant_news:
        lines.append("<ul>")
        for item in relevant_news:
            title = str(item.get("title", ""))
            source = str(item.get("source", ""))
            published_at = str(item.get("published_at", ""))
            summary = str(item.get("summary", ""))
            url = str(item.get("url", ""))
            lines.append(
                f"<li><strong>{escape(title)}</strong> "
                f"({escape(source)}, {escape(published_at)}): "
                f"{escape(summary)} "
                f'(<a href="{escape(url)}">Leer más</a>)</li>'
            )
        lines.append("</ul>")

    if analysis.limitations:
        lines.append("<h3>Limitaciones</h3>")
        lines.append("<ul>")
        for limitation in analysis.limitations:
            lines.append(f"<li>{escape(limitation)}</li>")
        lines.append("</ul>")

    provenance = analysis.provenance
    lines.append(
        "<p><em>Generado por: "
        f"{escape(provenance.ai_provider)} ({escape(provenance.ai_model)}) "
        f"el {escape(provenance.generated_at.isoformat())}</em></p>"
    )

    return lines


def _format_comparable_value_html(value: Any) -> str:
    """Formatea el valor de una métrica en la tabla comparativa.

    Equivalente HTML de
    `investmentops.reports.markdown._format_comparable_value` (misma
    lógica, duplicada aquí por independencia entre generadores, ver
    docstring del módulo). Devuelve ``"—"`` si `value` es ``None``
    (métrica no calculable para la empresa o el par, ver
    `investmentops.analysis_engines.comparables.calculate_entity_metrics`).
    No convierte a porcentaje: las cuatro métricas comparadas tienen
    unidades distintas (ratios, múltiplos), mismo criterio ya usado por
    el volcado plano de `supporting_metrics` en
    `_render_analysis_body_html`.
    """
    if value is None:
        return "—"
    return str(value)


def _format_comparable_position_html(position: Any) -> str:
    """Formatea la posición relativa de una comparación en la tabla.

    Equivalente HTML de
    `investmentops.reports.markdown._format_comparable_position`.
    Devuelve ``"—"`` si `position` es ``None`` (comparación no posible
    por falta de datos, ver
    `investmentops.analysis_engines.comparables.compare_metric`).
    """
    if position is None:
        return "—"
    return str(position)


def _render_comparables_body_html(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas HTML de la sección "Comparables del sector".

    Orden: hallazgos → métricas propias de la empresa investigada
    (`<ul><li>clave: valor</li></ul>`, igual criterio que "Salud
    financiera"/"Valoración") → tabla `<table>` comparativa por métrica y
    par (omitida si no hay ningún par) → limitaciones → procedencia de IA
    (centinela). Equivalente elemento a elemento a
    `investmentops.reports.markdown._render_comparables_body`. Todo el
    contenido dinámico se escapa con `html.escape` antes de insertarse.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(f"<p>{escape(finding)}</p>")

    company_metrics: dict[str, Any] = analysis.supporting_metrics.get("company", {})
    company_metric_items = [
        (key, value) for key, value in company_metrics.items() if key != "ticker"
    ]
    if company_metric_items:
        lines.append("<h3>Métricas de la empresa</h3>")
        lines.append("<ul>")
        for key, value in company_metric_items:
            lines.append(f"<li>{escape(str(key))}: {escape(str(value))}</li>")
        lines.append("</ul>")

    comparisons: dict[str, list[dict[str, Any]]] = analysis.supporting_metrics.get(
        "comparisons", {}
    )
    has_any_comparison = any(comparisons.get(name) for name in comparisons)

    if has_any_comparison:
        lines.append("<table>")
        lines.append(
            "<tr><th>Métrica</th><th>Par</th><th>Valor empresa</th>"
            "<th>Valor par</th><th>Posición</th></tr>"
        )
        for metric_name, entries in comparisons.items():
            for entry in entries:
                lines.append(
                    f"<tr><td>{escape(str(metric_name))}</td>"
                    f"<td>{escape(str(entry.get('peer_ticker', '')))}</td>"
                    "<td>"
                    f"{escape(_format_comparable_value_html(entry.get('company_value')))}"
                    "</td>"
                    "<td>"
                    f"{escape(_format_comparable_value_html(entry.get('peer_value')))}"
                    "</td>"
                    "<td>"
                    f"{escape(_format_comparable_position_html(entry.get('position')))}"
                    "</td></tr>"
                )
        lines.append("</table>")

    if analysis.limitations:
        lines.append("<h3>Limitaciones</h3>")
        lines.append("<ul>")
        for limitation in analysis.limitations:
            lines.append(f"<li>{escape(limitation)}</li>")
        lines.append("</ul>")

    provenance = analysis.provenance
    lines.append(
        "<p><em>Generado por: "
        f"{escape(provenance.ai_provider)} ({escape(provenance.ai_model)}) "
        f"el {escape(provenance.generated_at.isoformat())}</em></p>"
    )

    return lines


def _render_result_body_lines(result: ResearchResult) -> list[str]:
    """Construye las líneas HTML del cuerpo (sin envoltura de documento)
    para un único `ResearchResult`: título, identidad, fecha, y las cinco
    secciones de análisis, en el mismo orden que usa `render_html`.

    Extraída como pieza reutilizable (ver "Reporte de comparación" en el
    docstring del módulo) para que `render_html` y
    `render_html_comparison` compartan exactamente la misma lógica de
    volcado de cada sección, sin duplicarla.
    """
    ticker = escape(result.company.ticker)

    lines: list[str] = []
    lines.append(f"<h1>Investigación: {ticker}</h1>")

    identity_details = [
        detail
        for detail in (result.company.name, result.company.sector, result.company.market)
        if detail
    ]
    if identity_details:
        lines.append(f"<p>{escape(' · '.join(identity_details))}</p>")

    lines.append(f"<p>Generado: {escape(result.generated_at.isoformat())}</p>")

    lines.append("<h2>Salud financiera</h2>")
    financial_health_result = _find_analysis(result, FINANCIAL_HEALTH_AGENT_ID)
    if financial_health_result is not None:
        lines.extend(_render_analysis_body_html(financial_health_result))

    lines.append("<h2>Valoración</h2>")
    valuation_result = _find_analysis(result, VALUATION_AGENT_ID)
    if valuation_result is not None:
        lines.extend(_render_analysis_body_html(valuation_result))

    lines.append("<h2>Evolución de ingresos y beneficios</h2>")
    trend_analysis_result = _find_analysis(result, TREND_ANALYSIS_AGENT_ID)
    if trend_analysis_result is not None:
        lines.extend(_render_trend_analysis_body_html(trend_analysis_result))

    lines.append("<h2>Noticias recientes relevantes</h2>")
    news_relevance_result = _find_analysis(result, NEWS_RELEVANCE_AGENT_ID)
    if news_relevance_result is not None:
        lines.extend(_render_news_relevance_body_html(news_relevance_result))

    lines.append("<h2>Comparables del sector</h2>")
    comparables_result = _find_analysis(result, COMPARABLES_AGENT_ID)
    if comparables_result is not None:
        lines.extend(_render_comparables_body_html(comparables_result))

    return lines


def render_html(result: ResearchResult) -> str:
    """Renderiza un `ResearchResult` como reporte HTML.

    Construye el documento HTML5 completo (según el esqueleto ya fijado
    en `HTML_TEMPLATE.md`): encabezado con identidad de la empresa
    investigada y fecha de ensamblado, más las secciones "Salud
    financiera", "Valoración", "Evolución de ingresos y beneficios",
    "Noticias recientes relevantes" y "Comparables del sector", en el
    mismo orden y con el mismo contenido que
    `investmentops.reports.markdown.render_markdown` (construidos vía
    `_render_result_body_lines`, ver docstring del módulo).

    "Salud financiera" y "Valoración" vuelcan su contenido completo
    cuando el `AnalysisResult` correspondiente está presente: hallazgos,
    métricas de soporte, limitaciones y procedencia de la interpretación
    de IA (proveedor, modelo, fecha). "Evolución de ingresos y
    beneficios" vuelca hallazgos, una tabla de variación periodo a
    periodo, limitaciones y procedencia (centinela). "Noticias recientes
    relevantes" vuelca hallazgos, una lista `<ul>` de noticias relevantes
    (una por ítem), limitaciones y procedencia (centinela). "Comparables
    del sector" vuelca hallazgos, las métricas propias de la empresa, una
    tabla comparativa por métrica y par, limitaciones y procedencia
    (centinela). Si el agente/motor correspondiente no completó su
    análisis, la sección conserva solo su encabezado (`<h2>`) vacío.
    Todavía no se incluye la sección condicional de "Fallos parciales"
    (fuera de alcance de esta tarea, ver docstring del módulo).

    Parameters
    ----------
    result:
        El `ResearchResult` ya ensamblado (ver
        `investmentops.core.orchestrator.investigate`).

    Returns
    -------
    str
        Documento HTML5 completo (`<!DOCTYPE html>` ... `</html>`),
        terminado en un único salto de línea final.
    """
    ticker = escape(result.company.ticker)
    body_lines = _render_result_body_lines(result)
    body = "\n  ".join(body_lines)

    html_document = (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>Investigación: {ticker}</title>\n"
        "  <style>\n"
        f"    {_EMBEDDED_STYLE}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  {body}\n"
        "</body>\n"
        "</html>\n"
    )

    return html_document


def _shift_html_headings(html_fragment: str) -> str:
    """Desplaza un nivel cada encabezado HTML `<h1>`/`<h2>` de un fragmento
    ya renderizado.

    Equivalente HTML de
    `investmentops.reports.markdown._shift_markdown_headings`, usada por
    `render_html_comparison` para anidar el reporte individual completo
    de cada empresa (ya renderizado por `_render_result_body_lines`, que
    solo usa `<h1>` para el título y `<h2>` para las secciones de nivel
    superior) bajo el encabezado de nivel superior del documento de
    comparación (`<h1>Comparación: ...</h1>`).

    Transforma primero `<h2>`/`</h2>` en `<h3>`/`</h3>`, y luego
    `<h1>`/`</h1>` en `<h2>`/`</h2>` (en ese orden, para no desplazar dos
    veces el mismo encabezado). Los `<h3>` ya presentes en el fragmento
    (ej. "Métricas de soporte", "Limitaciones") no se tocan, mismo
    criterio que la versión Markdown (que solo desplaza nivel 1 y 2).

    Parameters
    ----------
    html_fragment:
        Fragmento HTML ya renderizado (típicamente la salida de
        `_render_result_body_lines`, unida en un único texto).

    Returns
    -------
    str
        El mismo fragmento, con cada `<h1>`/`<h2>` desplazado un nivel
        hacia abajo.
    """
    shifted = html_fragment.replace("<h2>", "<h3>").replace("</h2>", "</h3>")
    shifted = shifted.replace("<h1>", "<h2>").replace("</h1>", "</h2>")
    return shifted


def render_html_comparison(
    tickers: Sequence[str], results: Sequence[ResearchResult]
) -> str:
    """Renderiza un reporte de comparación (varias empresas) en HTML.

    Ver "Reporte de comparación (varias empresas, esta tarea)" en el
    docstring del módulo para la decisión de formato completa
    (equivalente HTML de
    `investmentops.reports.markdown.render_markdown_comparison`):
    reutiliza `_render_result_body_lines` para el reporte individual
    completo de cada empresa, anidándolos bajo un único documento HTML5
    de comparación (`<h1>Comparación: <tickers></h1>`), con los
    encabezados de cada reporte individual desplazados un nivel (vía
    `_shift_html_headings`) para que la jerarquía del documento quede
    correcta:

        <h1>Comparación: AAPL, MSFT</h1>
        <h2>Investigación: AAPL</h2>
        <h3>Salud financiera</h3>
        ...
        <h2>Investigación: MSFT</h2>
        <h3>Salud financiera</h3>
        ...

    Parameters
    ----------
    tickers:
        Los tickers solicitados para la comparación, en el mismo orden
        recibido (ej. `ComparisonResult.tickers`), usados únicamente
        para el título del documento (`<title>`/`<h1>`).
    results:
        Un `ResearchResult` por empresa, en el mismo orden (ej.
        `ComparisonResult.results`), cada uno renderizado íntegramente
        vía `_render_result_body_lines` y anidado bajo su propio
        subtítulo (`<h2>Investigación: <ticker></h2>`, desplazado desde
        el `<h1>` que produce esa función).

    Returns
    -------
    str
        Documento HTML5 completo (`<!DOCTYPE html>` ... `</html>`),
        terminado en un único salto de línea final. Si `results` está
        vacío, el documento contiene únicamente el título de
        comparación.
    """
    title = escape(", ".join(tickers))

    body_lines: list[str] = [f"<h1>Comparación: {title}</h1>"]

    for result in results:
        individual_fragment = "\n  ".join(_render_result_body_lines(result))
        body_lines.append(_shift_html_headings(individual_fragment))

    body = "\n  ".join(body_lines)

    html_document = (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>Comparación: {title}</title>\n"
        "  <style>\n"
        f"    {_EMBEDDED_STYLE}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  {body}\n"
        "</body>\n"
        "</html>\n"
    )

    return html_document


def _resolve_output_dir(
    output_dir: str | Path | None, config: dict[str, Any] | None
) -> Path:
    """Resuelve el directorio de salida a usar para guardar reportes HTML.

    Mismo criterio que `investmentops.reports.markdown._resolve_output_dir`:
    prioriza `output_dir` si se indica explícitamente; en caso contrario,
    lee `[output].output_dir` desde la configuración ya cargada (`config`)
    o, si tampoco se indica, desde `investmentops.config.load_config()`.
    Si la configuración no define una ruta, cae de vuelta a
    `DEFAULT_OUTPUT_DIR` (reutilizado desde `investmentops.reports.markdown`,
    misma carpeta de salida que el generador Markdown).
    """
    if output_dir is not None:
        return Path(output_dir)

    cfg = config if config is not None else load_config()
    configured_path = cfg.get("output", {}).get("output_dir")
    return Path(configured_path or DEFAULT_OUTPUT_DIR)


def save_html_report(
    ticker: str,
    content: str,
    *,
    output_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Guarda el texto HTML ya renderizado (`render_html`) en disco.

    Sigue exactamente el mismo patrón ya usado por
    `investmentops.reports.markdown.save_markdown_report` (ver
    "Guardado del archivo HTML generado" en el docstring del módulo).

    Parameters
    ----------
    ticker:
        Identificador de la empresa investigada (ej. ``"AAPL"``). Se
        normaliza a mayúsculas para el nombre del archivo, mismo criterio
        ya usado por `save_markdown_report` y por la caché de datos
        normalizados (ver `investmentops.data_layer.cache`).
    content:
        El texto HTML ya generado (típicamente la salida de
        `render_html(result)`), escrito tal cual, sin modificarlo.
    output_dir:
        Ruta al directorio donde guardar el reporte. Si no se indica, se
        resuelve desde `config.local.toml` (sección `[output]`, clave
        `output_dir`, ver CONFIGURATION.md) — la misma carpeta que usa
        `save_markdown_report`, ya que ambos formatos comparten
        `[output].output_dir`.
    config:
        Configuración ya cargada, útil para pruebas sin depender de un
        `config.local.toml` real en disco (ver `investmentops.config`).

    Returns
    -------
    Path
        La ruta del archivo `<TICKER>.html` escrito.

    Raises
    ------
    ReportError
        Si el ticker está vacío (o son solo espacios), o si ocurre un
        fallo de E/S al crear el directorio de salida o al escribir el
        archivo. Es la misma excepción ya usada por
        `save_markdown_report` (definida en
        `investmentops.reports.markdown`), reutilizada aquí en vez de
        duplicarse (ver docstring del módulo).
    ConfigError
        Si `output_dir` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    if not ticker or not ticker.strip():
        raise ReportError("El ticker no puede estar vacío.")

    resolved_dir = _resolve_output_dir(output_dir, config)

    try:
        resolved_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportError(
            f"No se pudo crear el directorio de reportes '{resolved_dir}': {exc}"
        ) from exc

    file_path = resolved_dir / f"{ticker.strip().upper()}.html"

    try:
        file_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ReportError(
            f"No se pudo escribir el archivo de reporte '{file_path}': {exc}"
        ) from exc

    return file_path