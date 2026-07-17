"""Generadores de reportes (Report Generators).

Responsabilidad (ver ARCHITECTURE.md, componente 6):
- Tomar el resultado ensamblado de la investigación (salida del
  orquestador, investmentops.core, ya con todos los análisis resueltos) y
  renderizarlo en distintos formatos: Markdown (principal), HTML
  (navegable) y JSON (consumo programático futuro).
- Los generadores consumen el mismo modelo de resultado; la lógica de
  análisis no vive en esta capa.
- La redacción narrativa final puede delegarse a un agente de reporte
  (apoyado en investmentops.ai_providers y un prompt externo) cuya única
  función es componer texto legible a partir de resultados ya producidos
  por los agentes de análisis, sin agregar hallazgos nuevos ni veredictos.
- Agregar un nuevo formato de salida implica añadir un generador nuevo, no
  tocar los existentes.

La estructura de entrada que consumen todos los generadores ya está
decidida en `investmentops/reports/REPORT_MODEL.md`: `ResearchResult`
tal cual (investmentops.core.research_result), sin un tipo intermedio
nuevo. El orden y contenido de las secciones del reporte ya está fijado
en `investmentops/reports/REPORT_SECTIONS.md`.

El primer generador concreto (Markdown) ya tiene su plantilla completa
implementada en `investmentops.reports.markdown` (ver TASKS.md, Fase 2,
"Generador Markdown") y se re-exporta aquí:

- `render_markdown`: construye el reporte completo (encabezado, salud
  financiera, valoración, incluyendo hallazgos, métricas de soporte,
  limitaciones y procedencia de la interpretación de IA por sección).
- `save_markdown_report`: guarda el texto ya renderizado por
  `render_markdown` en un archivo `<TICKER>.md`, en una ruta local
  configurable (`config.local.toml`, sección `[output].output_dir`).
- `ReportError`: excepción común para señalar fallos al guardar un
  reporte en disco (ticker vacío, fallo de E/S).

El generador HTML (ver TASKS.md, Fase 2, "Generador HTML") ya tiene su
volcado de secciones implementado en `investmentops.reports.html` y se
re-exporta aquí:

- `render_html`: construye el documento HTML5 completo (encabezado, salud
  financiera, valoración), reutilizando el mismo `ResearchResult` y el
  mismo orden de secciones ya fijado para Markdown (ver
  `investmentops/reports/HTML_TEMPLATE.md` y `REPORT_SECTIONS.md`).

Aún sin implementación: el guardado del archivo HTML generado en una
ruta local configurable (tarea separada y posterior, ver TASKS.md, Fase
2, "Generador HTML").
"""

from investmentops.reports.html import render_html
from investmentops.reports.markdown import (
    ReportError,
    render_markdown,
    save_markdown_report,
)

__all__ = [
    "ReportError",
    "render_html",
    "render_markdown",
    "save_markdown_report",
]
