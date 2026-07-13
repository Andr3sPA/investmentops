"""Interfaz de proveedores de IA (AI Provider Interface).

Componente transversal (ver ARCHITECTURE.md, componente 5bis), usado por
investmentops.analysis_engines y, opcionalmente, por un futuro agente de
reporte en investmentops.reports.

Responsabilidad:
- Definir un contrato común para invocar un modelo de lenguaje: entrada
  (prompt + datos estructurados + parámetros básicos) y salida
  (texto/estructura de respuesta + metadatos: proveedor, modelo, fecha de
  la llamada).
- Proveer una implementación concreta por proveedor soportado: Gemini,
  Claude (Anthropic), OpenAI y Ollama (modelos locales).
- Permitir seleccionar el proveedor (y el modelo) a usar mediante
  configuración local, sin que el agente que lo invoca conozca los
  detalles de la API específica de cada proveedor.

Ningún agente de análisis debe llamar directamente al SDK o API de un
proveedor de IA; siempre debe pasar por esta interfaz.

Aún sin implementación (ver TASKS.md, sección "Interfaz de proveedores de
IA" de la Fase 1).
"""
