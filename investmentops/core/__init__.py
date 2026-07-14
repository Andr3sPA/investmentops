"""Orquestador (core).

Responsabilidad (ver ARCHITECTURE.md, componente 2):
- Recibir una solicitud de investigación (ej. "investiga la empresa X").
- Determinar qué fuentes de datos (investmentops.data_providers) deben
  consultarse según el análisis solicitado.
- Ejecutar las fuentes de datos con manejo de fallos (si una falla, el
  sistema continúa con las demás y lo deja explícito en el resultado).
- Pasar los datos normalizados (investmentops.data_layer) a los motores de
  análisis correspondientes (investmentops.analysis_engines).
- Ensamblar los resultados de todos los análisis en un "Resultado de
  investigación" único.
- Entregar ese resultado a la capa de reportes (investmentops.reports).

El orquestador conoce interfaces, no implementaciones concretas: esto es lo
que permite registrar nuevas fuentes, análisis o proveedores de IA sin
modificar este módulo.

La estructura de "Resultado de investigación" ya está definida en
`investmentops.core.research_result` (ver TASKS.md, "Contratos e
interfaces" > "Definir la estructura de 'Resultado de investigación'") y
se re-exporta aquí para que el resto del sistema la importe directamente
desde `investmentops.core`:

- `ResearchResult`: agregación de los `AnalysisResult` de una empresa
  (empresa investigada, resultados de análisis, fallos parciales, fecha
  de ensamblado).
- `ResearchFailure`: registro explícito de un fallo parcial (fuente de
  datos o motor de análisis) ocurrido durante una investigación.

Aún sin implementación: la lógica que efectivamente ensambla un
`ResearchResult` invocando fuentes de datos y motores de análisis (ver
TASKS.md, sección "Orquestador mínimo" de la Fase 1).
"""

from investmentops.core.research_result import ResearchFailure, ResearchResult

__all__ = [
    "ResearchFailure",
    "ResearchResult",
]
