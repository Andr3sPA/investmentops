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

El contrato mencionado arriba ya está definido en
`investmentops.ai_providers.contracts` (ver TASKS.md, "Contratos e
interfaces" > "Definir el contrato de 'AI provider'") y se re-exporta
aquí para que el resto del sistema lo importe directamente desde
`investmentops.ai_providers`:

- `AIProvider`: protocolo que debe cumplir toda integración de proveedor
  de IA (método `complete(prompt, data=None) -> AIProviderResponse`).
- `AIProviderResponse`: respuesta estructurada (contenido, proveedor,
  modelo, fecha de generación).
- `AIProviderError`: excepción común para señalar fallos del proveedor.

Aún sin implementación: ninguna integración concreta (Anthropic, Gemini,
OpenAI, Ollama). Ver TASKS.md, sección "Interfaz de proveedores de IA" de
la Fase 1, para las tareas siguientes:
- Implementar al menos una integración concreta que cumpla la interfaz.
- Definir el mecanismo de selección de proveedor/modelo por agente vía
  configuración local (`config.local.toml`, sección `[agents]`).
- Documentar cómo se sumarían las integraciones restantes sin modificar
  la interfaz ni los agentes.
- Implementar manejo de error básico cuando el proveedor no responde o
  devuelve un formato inesperado.
"""

from investmentops.ai_providers.contracts import (
    AIProvider,
    AIProviderError,
    AIProviderResponse,
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIProviderResponse",
]
