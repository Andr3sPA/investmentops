"""Generador de reportes en HTML.

Cubre la tarea "Implementar el volcado de las mismas secciones que en
Markdown (salud financiera, valoración, fuentes)" (TASKS.md, Fase 2,
"Generador HTML"), sobre la base de diseño ya fijada en
`investmentops/reports/HTML_TEMPLATE.md`: HTML5 mínimo, sin CSS
elaborado, sin JavaScript, sin motor de templating externo, con las
mismas secciones y el mismo orden ya usados por el generador Markdown
(`investmentops/reports/markdown.py`), consumiendo directamente
`ResearchResult` sin ningún tipo intermedio nuevo (ver
`investmentops/reports/REPORT_MODEL.md` y `REPORT_SECTIONS.md`).

Este módulo no importa nada de `investmentops.reports.markdown`: aunque
el contenido y el orden de las secciones son los mismos, cada generador
de formato es independiente (ver ARCHITECTURE.md, "Extensibilidad sin
reescritura" — "Agregar un nuevo formato de salida implica añadir un
generador nuevo, no tocar los existentes"), por lo que las constantes de
identificador de agente (`FINANCIAL_HEALTH_AGENT_ID`, `VALUATION_AGENT_ID`)
y el helper de búsqueda (`_find_analysis`) se duplican aquí en vez de
importarse, mismo criterio ya documentado en el módulo Markdown.

## Escapado de caracteres especiales HTML

`HTML_TEMPLATE.md` deja explícitamente el escapado de `<`, `>` y `&` en
el contenido dinámico (hallazgos generados por el modelo de IA, nombre de
la empresa, etc.) como una decisión de esta tarea de implementación, no
de la tarea de diseño de la estructura. Este módulo escapa **todo**
contenido dinámico insertado en el HTML mediante `html.escape` (título,
identidad de la empresa, fecha, hallazgos, claves/valores de métricas,
limitaciones, y procedencia de IA), ya que el texto de `findings` proviene
de un modelo de lenguaje y no debe interpretarse como marcado HTML.

## Volcado de secciones (mapeo con `HTML_TEMPLATE.md`)

Reutiliza el mismo mapeo elemento-a-elemento ya documentado en
`HTML_TEMPLATE.md`:

- `<h1>Investigación: {ticker}</h1>` + línea de identidad (`name · sector
  · market`, omitida si los tres campos están vacíos) + `<p>Generado:
  {fecha}</p>`.
- `<h2>Salud financiera</h2>` / `<h2>Valoración</h2>`: encabezados
  **siempre** presentes, estén o no disponibles sus respectivos
  `AnalysisResult` (mismo comportamiento que la plantilla base Markdown:
  una sección sin agente disponible conserva solo su encabezado vacío).
- Por cada análisis disponible, en este orden: hallazgos (un `<p>` por
  elemento de `findings`) → métricas de soporte (`<h3>Métricas de
  soporte</h3>` + `<ul><li>clave: valor</li>...</ul>`, omitida si
  `supporting_metrics` está vacío) → limitaciones (`<h3>Limitaciones</h3>`
  + `<ul>...</ul>`, omitida si `limitations` está vacío) → procedencia de
  la interpretación de IA (`<p><em>Generado por: proveedor (modelo) el
  fecha</em></p>`).

Fuera de alcance de este módulo (ver TASKS.md, "Generador HTML", tarea
siguiente):
- El guardado del archivo HTML generado en disco (tarea separada y
  posterior, seguirá el mismo patrón ya usado por
  `investmentops.reports.markdown.save_markdown_report`).
- La sección de "Fallos parciales": no forma parte del mapeo de esta
  tarea (`HTML_TEMPLATE.md` la documenta como parte de la plantilla
  general, pero el generador Markdown tampoco la implementa todavía, ver
  `investmentops/reports/markdown.py`, docstring de `render_markdown`);
  se mantiene fuera de alcance en ambos generadores por consistencia.
"""

from __future__ import annotations

from html import escape

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.core.research_result import ResearchResult

#: Identificador del agente de salud financiera, el mismo usado en
#: `investmentops.analysis_engines.financial_health.AGENT_ID`. No se
#: importa directamente desde ese módulo (ver docstring del módulo,
#: "no se importa nada de investmentops.reports.markdown" aplica también
#: aquí: basta con el identificador de texto, ya estable como parte de
#: `AnalysisResult.analysis_id`).
FINANCIAL_HEALTH_AGENT_ID = "financial_health"

#: Identificador del agente de valoración, mismo criterio que
#: `FINANCIAL_HEALTH_AGENT_ID`.
VALUATION_AGENT_ID = "valuation"

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
    independencia entre generadores (ver docstring del módulo).
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
    "Valoración" (no depende del `analysis_id` concreto). Todo el
    contenido dinámico se escapa con `html.escape` antes de insertarse.
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


def render_html(result: ResearchResult) -> str:
    """Renderiza un `ResearchResult` como reporte HTML.

    Construye el documento HTML5 completo (según el esqueleto ya fijado
    en `HTML_TEMPLATE.md`): encabezado con identidad de la empresa
    investigada y fecha de ensamblado, más las secciones "Salud
    financiera" y "Valoración", en el mismo orden y con el mismo
    contenido que `investmentops.reports.markdown.render_markdown`.

    Ambas secciones vuelcan su contenido completo cuando el
    `AnalysisResult` correspondiente está presente: hallazgos, métricas
    de soporte, limitaciones y procedencia de la interpretación de IA
    (proveedor, modelo, fecha). Si el agente no completó su análisis, la
    sección conserva solo su encabezado (`<h2>`) vacío. Todavía no se
    incluye la sección condicional de "Fallos parciales" (fuera de
    alcance de esta tarea, ver docstring del módulo).

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

    body_lines: list[str] = []
    body_lines.append(f"<h1>Investigación: {ticker}</h1>")

    identity_details = [
        detail
        for detail in (result.company.name, result.company.sector, result.company.market)
        if detail
    ]
    if identity_details:
        body_lines.append(f"<p>{escape(' · '.join(identity_details))}</p>")

    body_lines.append(f"<p>Generado: {escape(result.generated_at.isoformat())}</p>")

    body_lines.append("<h2>Salud financiera</h2>")
    financial_health_result = _find_analysis(result, FINANCIAL_HEALTH_AGENT_ID)
    if financial_health_result is not None:
        body_lines.extend(_render_analysis_body_html(financial_health_result))

    body_lines.append("<h2>Valoración</h2>")
    valuation_result = _find_analysis(result, VALUATION_AGENT_ID)
    if valuation_result is not None:
        body_lines.extend(_render_analysis_body_html(valuation_result))

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
