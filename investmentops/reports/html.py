"""Generador de reportes en HTML.

Cubre, hasta ahora, dos tareas de TASKS.md, Fase 2, "Generador HTML":

- "Implementar el volcado de las mismas secciones que en Markdown (salud
  financiera, valoración, fuentes)." (ya completada, ver PROGRESS.md).
- "Implementar el guardado del archivo HTML generado en una ruta local
  configurable." (esta tarea).

Sobre la base de diseño ya fijada en `investmentops/reports/HTML_TEMPLATE.md`:
HTML5 mínimo, sin CSS elaborado, sin JavaScript, sin motor de templating
externo, con las mismas secciones y el mismo orden ya usados por el
generador Markdown (`investmentops/reports/markdown.py`), consumiendo
directamente `ResearchResult` sin ningún tipo intermedio nuevo (ver
`investmentops/reports/REPORT_MODEL.md` y `REPORT_SECTIONS.md`).

Este módulo no importa nada de `investmentops.reports.markdown` para la
parte de **renderizado** (`render_html`): aunque el contenido y el orden
de las secciones son los mismos, cada generador de formato es
independiente (ver ARCHITECTURE.md, "Extensibilidad sin reescritura" —
"Agregar un nuevo formato de salida implica añadir un generador nuevo,
no tocar los existentes"), por lo que las constantes de identificador de
agente (`FINANCIAL_HEALTH_AGENT_ID`, `VALUATION_AGENT_ID`) y el helper de
búsqueda (`_find_analysis`) se duplican aquí en vez de importarse, mismo
criterio ya documentado en versiones anteriores de este módulo.

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
  investigación: tarea separada y posterior (ver TASKS.md, "Orquestador
  y CLI" de la Fase 2).
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

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
