"""Generador de reportes en Markdown.

Cubre, hasta ahora, cuatro tareas de TASKS.md, Fase 2, "Generador Markdown":

- "Implementar la plantilla base de reporte en Markdown (encabezados,
  secciones vacías)." (ya completada, ver PROGRESS.md).
- "Implementar el volcado de los hallazgos de salud financiera en la
  sección correspondiente." (ya completada, ver PROGRESS.md).
- "Implementar el volcado de los hallazgos de valoración en la sección
  correspondiente." (ya completada, ver PROGRESS.md).
- "Implementar la sección de fuentes/procedencia (qué proveedor, qué
  fecha) al final del reporte." (esta tarea).

## Dónde vive la procedencia de IA

`investmentops/reports/REPORT_SECTIONS.md` ya fija, para cada sección de
análisis ("Salud financiera", "Valoración"), un orden de cuatro partes:
hallazgos → métricas de soporte → limitaciones → **procedencia de la
interpretación de IA** (`provenance`: proveedor y modelo). Esta tarea
implementa exactamente esa cuarta parte, dentro de `_render_analysis_body`
(reutilizada, sin cambios de firma, por ambas secciones), en vez de
introducir una sección nueva y separada al final del documento: el título
de la tarea en `TASKS.md` ("al final del reporte") se satisface en el
sentido de "al final de cada bloque de análisis", que es el diseño ya
documentado y más específico de `REPORT_SECTIONS.md`.

Además del proveedor y modelo (`ai_provider`, `ai_model`), se incluye la
fecha de generación (`generated_at`), conforme a lo que pide literalmente
la tarea en `TASKS.md` ("qué proveedor, qué fecha"): `AnalysisProvenance`
ya expone ese dato y no hay razón para omitirlo del reporte.

Si el agente correspondiente no completó su análisis, la sección sigue
sin ningún contenido (ni hallazgos, ni métricas, ni procedencia): mismo
comportamiento ya usado en las tareas anteriores.

Fuera de alcance de este módulo (aún):
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

#: Identificador del agente de valoración, el mismo usado en
#: `investmentops.analysis_engines.valuation.AGENT_ID`. Mismo criterio
#: que `FINANCIAL_HEALTH_AGENT_ID`: no se importa desde el módulo del
#: agente para no acoplar este generador a su implementación concreta.
VALUATION_AGENT_ID = "valuation"


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
    """Construye las líneas de hallazgos, métricas, limitaciones y
    procedencia de IA de un análisis.

    Orden fijado en `REPORT_SECTIONS.md`: hallazgos → métricas de
    soporte → limitaciones → procedencia de la interpretación de IA
    (proveedor, modelo y fecha de generación). Reutilizada tanto para
    "Salud financiera" como para "Valoración" (no depende del
    `analysis_id` concreto).
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

    provenance = analysis.provenance
    lines.append(
        f"**Generado por:** {provenance.ai_provider} ({provenance.ai_model}) "
        f"el {provenance.generated_at.isoformat()}"
    )
    lines.append("")

    return lines


def render_markdown(result: ResearchResult) -> str:
    """Renderiza un `ResearchResult` como reporte Markdown.

    Construye el encabezado (identidad de la empresa investigada y fecha
    de ensamblado) y las secciones "Salud financiera" y "Valoración",
    conforme al orden fijado en `investmentops/reports/REPORT_SECTIONS.md`.

    Ambas secciones ya vuelcan su contenido completo cuando el
    `AnalysisResult` correspondiente está presente: hallazgos, métricas
    de soporte, limitaciones y procedencia de la interpretación de IA
    (proveedor, modelo, fecha). Todavía no se incluye la sección
    condicional de "Fallos parciales" (tarea separada, fuera del alcance
    definido para "Generador Markdown" en `TASKS.md`; ya cubierta en
    texto plano de consola por `investmentops.cli.format_research_result`,
    Fase 1).

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
    valuation_result = _find_analysis(result, VALUATION_AGENT_ID)
    if valuation_result is not None:
        lines.extend(_render_analysis_body(valuation_result))

    return "\n".join(lines).rstrip("\n") + "\n"
