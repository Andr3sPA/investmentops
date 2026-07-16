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

El primer generador concreto (Markdown) ya tiene su plantilla base
implementada en `investmentops.reports.markdown` (ver TASKS.md, Fase 2,
"Generador Markdown" > "Implementar la plantilla base de reporte en
Markdown (encabezados, secciones vacías)") y se re-exporta aquí:

- `render_markdown`: construye el encabezado de la empresa y los
  encabezados vacíos de "Salud financiera"/"Valoración". Todavía no
  vuelca hallazgos, métricas, limitaciones, procedencia ni guarda nada
  en disco: esas son tareas separadas y posteriores de la misma sección.

Aún sin implementación: el generador HTML (ver TASKS.md, Fase 2,
"Generador HTML").
"""

from investmentops.reports.markdown import render_markdown

__all__ = [
    "render_markdown",
]
