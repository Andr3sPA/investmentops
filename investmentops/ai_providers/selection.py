"""Selección de proveedor/modelo de IA por agente (config-driven).

Cubre la tarea "Definir el mecanismo de selección de proveedor/modelo por
agente vía configuración local" (TASKS.md, Fase 1, "Interfaz de
proveedores de IA"). Ver CONFIGURATION.md, sección "Estructura del
archivo": *"[agents] — mapeo explícito de qué proveedor de IA usa cada
agente de análisis... Si un agente no aparece aquí, se asume
[ai_providers.default]."*

Este módulo NO invoca ningún proveedor de IA ni construye instancias de
`AIProvider` concretas (ej. `AnthropicAIProvider`): solo resuelve, a
partir de la configuración ya cargada (`investmentops.config.load_config`)
y un identificador de agente, **qué** proveedor y modelo le corresponden.
Es la pieza que le permite a quien construye/registra un agente (tarea
posterior, ver TASKS.md "Agente de análisis: salud financiera" y
"Agente de análisis: valoración") elegir la implementación concreta de
`AIProvider` a instanciar sin acoplar esa decisión al código del agente
(ver ARCHITECTURE.md, "Independencia del proveedor de IA").

Regla de resolución (ver CONFIGURATION.md):

- Si `[agents].<agent_id>` existe y tiene un valor distinto de
  ``"default"``, ese valor es el nombre del proveedor a usar (debe
  coincidir con una subsección `[ai_providers.<nombre>]`, ej.
  ``"anthropic"``).
- Si `[agents].<agent_id>` no existe, o su valor es literalmente
  ``"default"`` (como en los ejemplos comentados de
  `config.example.toml`: ``financial_health = "default"``), se usa el
  proveedor indicado en `[ai_providers.default].provider`.
- El modelo (`model`) se resuelve, en esta fase, siempre desde
  `[ai_providers.default].model`: hoy no existe un campo `model` por
  proveedor en `config.example.toml` (solo en `[ai_providers.default]`),
  el mismo criterio ya usado por `AnthropicAIProvider` (ver
  `investmentops/ai_providers/anthropic_provider.py` y PROGRESS.md). Si en
  el futuro se necesita un modelo distinto por proveedor o por agente,
  eso es una extensión posterior y explícita de este mecanismo, no algo
  que deba adelantarse aquí.
- Si no puede resolverse ningún proveedor (ni `[agents]` ni
  `[ai_providers.default].provider` lo indican), se señala mediante
  `AgentProviderSelectionError`, nunca devolviendo un proveedor inventado
  o adivinado.

Fuera de alcance de este módulo:
- Instanciar la implementación concreta de `AIProvider` correspondiente al
  proveedor resuelto (ej. crear un `AnthropicAIProvider` con las
  credenciales de `[ai_providers.<nombre>]`): eso es responsabilidad de
  quien construye el agente, usando esta selección como entrada.
- Validar que la subsección `[ai_providers.<nombre>]` resuelta realmente
  tenga las credenciales necesarias (ej. `api_key`): esa validación ya la
  hace cada implementación concreta de `AIProvider` (ver
  `AnthropicAIProvider.__init__`, que levanta `AIProviderError` si falta
  la API key).
- Documentar cómo se sumarían las integraciones restantes (Gemini,
  OpenAI, Ollama): tarea separada en TASKS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_PROVIDER_KEY = "default"


class AgentProviderSelectionError(RuntimeError):
    """Error al resolver el proveedor/modelo de IA configurado para un agente.

    Cubre el caso en que ni `[agents].<agent_id>` ni
    `[ai_providers.default].provider` indican qué proveedor usar: la
    configuración local (`config.local.toml`) está incompleta para ese
    agente. Quien invoca esta resolución (típicamente el código que
    construye/registra un agente concreto) debe tratar esto como un error
    de configuración a corregir, no como algo que deba resolverse
    adivinando un proveedor por defecto adicional.
    """


@dataclass(frozen=True)
class AgentProviderSelection:
    """Resultado de resolver qué proveedor/modelo de IA usa un agente.

    Attributes
    ----------
    agent_id:
        Identificador del agente para el que se resolvió esta selección
        (ej. ``"financial_health"``), el mismo usado en `[agents]` y para
        localizar su archivo de prompt (ver `prompts/README.md`).
    provider:
        Nombre del proveedor de IA resuelto (ej. ``"anthropic"``), tal
        como se usa para localizar su subsección
        `[ai_providers.<nombre>]` en `config.local.toml` (ver
        CONFIGURATION.md). Es el valor que quien construye el agente debe
        usar para decidir qué implementación concreta de `AIProvider`
        instanciar.
    model:
        Identificador del modelo a usar dentro de ese proveedor (ej.
        ``"claude-sonnet-5"``), o ``None`` si la configuración no define
        ninguno (en cuyo caso la implementación concreta de `AIProvider`
        aplica su propio valor por defecto, ej.
        `AnthropicAIProvider.DEFAULT_MODEL`).
    """

    agent_id: str
    provider: str
    model: str | None


def resolve_agent_provider(
    agent_id: str,
    config: Mapping[str, Any],
) -> AgentProviderSelection:
    """Resuelve qué proveedor y modelo de IA le corresponden a un agente.

    Parameters
    ----------
    agent_id:
        Identificador del agente de análisis (ej. ``"financial_health"``,
        ``"valuation"``), el mismo que usa `[agents]` en
        `config.local.toml` y el que localiza el archivo de prompt del
        agente (ver `prompts/README.md`).
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), o cualquier mapeo con la
        misma forma (útil para pruebas sin depender de un
        `config.local.toml` real en disco).

    Returns
    -------
    AgentProviderSelection
        El proveedor y modelo resueltos para este agente.

    Raises
    ------
    AgentProviderSelectionError
        Si no puede resolverse ningún proveedor para este agente: ni
        `[agents].<agent_id>` lo indica (o su valor es ``"default"``), ni
        `[ai_providers.default].provider` está configurado.
    """
    agents_cfg = config.get("agents", {}) or {}
    ai_providers_cfg = config.get("ai_providers", {}) or {}
    default_cfg = ai_providers_cfg.get(DEFAULT_PROVIDER_KEY, {}) or {}

    provider = agents_cfg.get(agent_id)
    if not provider or provider == DEFAULT_PROVIDER_KEY:
        provider = default_cfg.get("provider")

    if not provider:
        raise AgentProviderSelectionError(
            f"No se pudo resolver un proveedor de IA para el agente "
            f"'{agent_id}': no está mapeado explícitamente en [agents] y "
            f"tampoco hay un proveedor definido en "
            f"[ai_providers.default].provider (ver CONFIGURATION.md)."
        )

    model = default_cfg.get("model")

    return AgentProviderSelection(agent_id=agent_id, provider=provider, model=model)
