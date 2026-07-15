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

El mecanismo de selección de proveedor/modelo por agente vía
configuración local ya está definido en
`investmentops.ai_providers.selection` (ver TASKS.md, "Interfaz de
proveedores de IA" > "Definir el mecanismo de selección de
proveedor/modelo por agente vía configuración local") y también se
re-exporta aquí:

- `resolve_agent_provider`: dado un identificador de agente y la
  configuración cargada, resuelve qué proveedor y modelo le corresponden
  (mirando `[agents]` y cayendo de vuelta a `[ai_providers.default]`).
- `AgentProviderSelection`: resultado de esa resolución (agente,
  proveedor, modelo).
- `AgentProviderSelectionError`: excepción para cuando no puede resolverse
  ningún proveedor para un agente dado.

Implementaciones concretas:
- `investmentops.ai_providers.anthropic_provider.AnthropicAIProvider`:
  primera integración concreta (Anthropic), ver TASKS.md.

La construcción de la instancia concreta correspondiente al proveedor
resuelto por `resolve_agent_provider` (ej. traducir el texto
``"anthropic"`` a una instancia de `AnthropicAIProvider`) ya está
definida en `investmentops.ai_providers.factory` (ver TASKS.md, "Agente
de análisis: salud financiera" > "Implementar la invocación al proveedor
de IA configurado con esas métricas + el prompt") y también se re-exporta
aquí:

- `build_ai_provider`: dado un nombre de proveedor (ej. ``"anthropic"``)
  y la configuración cargada, devuelve la instancia concreta de
  `AIProvider` lista para invocar.

Aún sin implementación: las integraciones restantes (Gemini, OpenAI,
Ollama). Ver TASKS.md, sección "Interfaz de proveedores de IA" de la Fase
1, para las tareas siguientes:
- Dejar documentado (sin implementar aún si no es necesario para el MVP)
  cómo se sumarían las integraciones restantes sin modificar la interfaz
  ni los agentes. — Ya cubierto en
  `investmentops/ai_providers/EXTENDING.md`.
"""

from investmentops.ai_providers.contracts import (
    AIProvider,
    AIProviderError,
    AIProviderResponse,
)
from investmentops.ai_providers.factory import build_ai_provider
from investmentops.ai_providers.selection import (
    AgentProviderSelection,
    AgentProviderSelectionError,
    resolve_agent_provider,
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIProviderResponse",
    "AgentProviderSelection",
    "AgentProviderSelectionError",
    "build_ai_provider",
    "resolve_agent_provider",
]
