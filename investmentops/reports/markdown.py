"""Generador de reportes en Markdown — plantilla base (encabezados, secciones vacías).

Cubre la tarea "Implementar la plantilla base de reporte en Markdown
(encabezados, secciones vacías)" (TASKS.md, Fase 2, "Generador
Markdown"), la primera tarea de código de esa sección.

Este módulo construye únicamente el **andamiaje** del reporte: los
encabezados de las secciones ya fijadas en
`investmentops/reports/REPORT_SECTIONS.md` (encabezado de la empresa,
"Salud financiera", "Valoración"), sin volcar todavía el contenido de
cada sección. El volcado de contenido real es alcance de tareas
separadas y posteriores, ya desglosadas en TASKS.md, "Generador
Markdown":

- "Implementar el volcado de los hallazgos de salud financiera en la
  sección correspondiente." (pendiente)
- "Implementar el volcado de los hallazgos de valoración en la sección
  correspondiente." (pendiente)
- "Implementar la sección de fuentes/procedencia (qué proveedor, qué
  fecha) al final del reporte." (pendiente)
- "Implementar el guardado del archivo Markdown generado en una ruta
  local configurable." (pendiente)

Por qué esta plantilla base ya incluye los encabezados de ambas
secciones de análisis, en vez de omitirlos hasta que exista contenido:
`REPORT_SECTIONS.md` fija el orden completo del reporte (encabezado →
salud financiera → valoración → fallos parciales); dejar ya ese
andamiaje construido es lo que permite que las tareas siguientes solo
tengan que *rellenar* cada sección, sin tener que rediseñar la
estructura del documento.

La sección "Fallos parciales" (`REPORT_SECTIONS.md`, sección 4) **no**
se incluye todavía en esta plantilla base: es una sección condicional
(solo aparece si `ResearchResult.failures` no está vacío), y volcar su
contenido real depende de datos que esta tarea de plantilla no procesa
todavía. Se deja para cuando se implemente el volcado de contenido de
las demás secciones, siguiendo el mismo criterio ya usado en
`investmentops.cli.format_research_result` (Fase 1), que sí construye
esa sección condicionalmente.

Fuera de alcance de este módulo (aún):
- Volcar `AnalysisResult.findings`/`supporting_metrics`/`limitations`
  dentro de las secciones "Salud financiera"/"Valoración": tareas
  separadas y posteriores (ver arriba).
- La sección de fuentes/procedencia al final del reporte: tarea
  separada y posterior.
- Guardar el Markdown generado en disco: tarea separada y posterior.
- El generador HTML: sección separada de TASKS.md.
"""

from __future__ import annotations

from investmentops.core.research_result import ResearchResult


def render_markdown(result: ResearchResult) -> str:
    """Construye la plantilla base en Markdown de un `ResearchResult`.

    Genera únicamente el encabezado (identidad de la empresa investigada
    y fecha de ensamblado) y los encabezados vacíos de las secciones
    "Salud financiera" y "Valoración", conforme al orden fijado en
    `investmentops/reports/REPORT_SECTIONS.md`. No vuelca todavía
    ningún hallazgo, métrica, limitación ni procedencia: ver el
    docstring del módulo para las tareas que completan cada sección.

    Parameters
    ----------
    result:
        El `ResearchResult` ya ensamblado (ver
        `investmentops.core.orchestrator.investigate`), del que esta
        plantilla base solo toma `company` y `generated_at`.

    Returns
    -------
    str
        Texto Markdown con el encabezado de la empresa y los
        encabezados vacíos de "Salud financiera" y "Valoración",
        terminado en un único salto de línea final.
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

    lines.append("## Valoración")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"
