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

Aún sin implementación (ver TASKS.md, sección "Orquestador mínimo" de la
Fase 1).
"""
