"""Generador de reportes en Markdown.

Cubre, hasta ahora, dos tareas de TASKS.md, Fase 2, "Generador Markdown":

- "Implementar la plantilla base de reporte en Markdown (encabezados,
  secciones vacías)." (ya completada, ver PROGRESS.md).
- "Implementar el volcado de los hallazgos de salud financiera en la
  sección correspondiente." (esta tarea).

Conforme al orden ya fijado en `investmentops/reports/REPORT_SECTIONS.md`
para la sección "Salud financiera" (hallazgos → métricas de soporte →
limitaciones → procedencia de IA), esta tarea rellena las **tres
primeras** subsecciones a partir del `AnalysisResult` con
`analysis_id == "financial_health"`, si está presente en
`ResearchResult.analysis_results`. La procedencia de IA (`provenance`)
se deja deliberadamente fuera: es el contenido de la tarea siguiente en
la misma sección de `TASKS.md` ("Implementar la sección de
fuentes/procedencia... al final del reporte"), consistente con cómo se
desglosó esa tarea por separado.

Si el agente de salud financiera no aparece en `analysis_results` (por
ejemplo, porque falló y quedó registrado en `ResearchResult.failures`),
la sección conserva su encabezado vacío (mismo comportamiento ya cubierto
por la plantilla base): esta tarea no toca la sección "Fallos parciales"
(tarea separada y posterior, ver `render_markdown` y
`investmentops.cli.format_research_result` para el criterio ya usado en
la Fase 1).

Fuera de alcance de este módulo (aún):
- El volcado de los hallazgos de valoración: tarea separada y siguiente
  en la misma sección de `TASKS.md`.
- La sección de fuentes/procedencia (proveedor y modelo de IA) al final
  del reporte: tarea separada y siguiente.
- Guardar el Markdown generado en disco: tarea separada y posterior.
- El generador HTML: sección separada de `TASKS.md`.
"""

from __future__ import annotations

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.core.research_result import ResearchResult

#: Identificador del agente de salud financiera, el mismo usado en
#: `investmentops.analysis_engines.financial_health.AGENT_ID`. No se
#: importa directamente desde ese módulo para no acoplar este generador
#: a la implementación concreta del agente (basta con el identificador
#: de texto, ya estable como parte de `AnalysisResult.analysis_id`).
FINANCIAL_HEALTH_AGENT_ID = "financial_health"


def _find_analysis(
    result: ResearchResult, analysis_id: str
) -> AnalysisResult | None:
    """Busca, dentro de `result.analysis_results`, el análisis con `analysis_id`.

    Devuelve ``None`` si ese agente no completó su análisis (no aparece
    en la lista), en cuyo caso la sección correspondiente del reporte
    conserva solo su encabezado vacío.
    """
    return next(
        (analysis for analysis in result.analysis_results if analysis.analysis_id == analysis_id),
        None,
    )


def _render_analysis_body(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas de hallazgos, métricas y limitaciones de un análisis.

    Orden fijado en `REPORT_SECTIONS.md` (sin la procedencia de IA,
    fuera de alcance de esta tarea): hallazgos → métricas de soporte →
    limitaciones.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(finding)
    lines.append("")

    if analysis.supporting_metrics:
        lines.append("**Métricas de soporte:**")
        lines.append("")
        for key, value in analysis.supporting_metrics.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    if analysis.limitations:
        lines.append("**Limitaciones:**")
        lines.append("")
        for limitation in analysis.limitations:
            lines.append(f"- {limitation}")
        lines.append("")

    return lines


def render_markdown(result: ResearchResult) -> str:
    """Renderiza un `ResearchResult` como reporte Markdown.

    Construye el encabezado (identidad de la empresa investigada y fecha
    de ensamblado) y las secciones "Salud financiera" y "Valoración",
    conforme al orden fijado en `investmentops/reports/REPORT_SECTIONS.md`.

    "Salud financiera" ya vuelca su contenido (hallazgos, métricas de
    soporte, limitaciones) cuando el `AnalysisResult` correspondiente
    está presente; "Valoración" mantiene por ahora solo su encabezado
    vacío (tarea separada y posterior). Tampoco se incluye todavía la
    procedencia de IA de ningún análisis, ni la sección condicional de
    "Fallos parciales" (ver docstring del módulo).

    Parameters
    ----------
    result:
        El `ResearchResult` ya ensamblado (ver
        `investmentops.core.orchestrator.investigate`).

    Returns
    -------
    str
        Texto Markdown del reporte, terminado en un único salto de línea
        final.
    """
    lines: list[str] = []

    lines.append(f"# Investigación: {result.company.ticker}")
    lines.append("")

    identity_details = [
        detail
        for detail in (result.company.name, result.company.sector, result.company.market)
        if detail
    ]
    if identity_details:
        lines.append(" · ".join(identity_details))
        lines.append("")

    lines.append(f"Generado: {result.generated_at.isoformat()}")
    lines.append("")

    lines.append("## Salud financiera")
    lines.append("")
    financial_health_result = _find_analysis(result, FINANCIAL_HEALTH_AGENT_ID)
    if financial_health_result is not None:
        lines.extend(_render_analysis_body(financial_health_result))

    lines.append("## Valoración")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"
