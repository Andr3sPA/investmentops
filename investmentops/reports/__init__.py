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

Aún sin implementación (llega en la Fase 2, ver ROADMAP.md y TASKS.md).
"""
