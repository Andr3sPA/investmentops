"""Fábrica de instancias concretas de `AIProvider` a partir de su nombre.

`investmentops.ai_providers.selection.resolve_agent_provider` resuelve
*qué nombre* de proveedor (ej. ``"anthropic"``) le corresponde a un
agente según `config.local.toml`, pero -tal como deja documentado
`investmentops/ai_providers/EXTENDING.md`, sección "Quién decide qué
clase concreta instanciar"- no existía todavía un mecanismo genérico
que tradujera ese nombre a la clase `AIProvider` concreta a instanciar
(`AnthropicAIProvider`, y las que se sumen a futuro). Este módulo cubre
esa pieza, necesaria para poder invocar realmente al proveedor de IA
configurado (ver TASKS.md, "Agente de análisis: salud financiera" >
"Implementar la invocación al proveedor de IA configurado con esas
métricas + el prompt").

Se implementa como un mapeo explícito `{nombre: fábrica}` en vez de un
registro dinámico o un mecanismo de plugins: hoy solo existe una
integración concreta (`AnthropicAIProvider`, ver
`investmentops/ai_providers/anthropic_provider.py`), y un registro más
elaborado sería sobre-diseño antes de tener más de un proveedor real que
lo justifique (mismo criterio ya aplicado en otros módulos del proyecto,
ver por ejemplo `investmentops/data_layer/market_data.py`).

Fuera de alcance de este módulo:
- Implementar integraciones nuevas (Gemini, OpenAI, Ollama): siguen
  documentadas como pendientes en `EXTENDING.md`. Sumar una implica
  añadir una entrada a `_PROVIDER_FACTORIES` en este módulo, sin tocar
  `contracts.py` ni `selection.py` (ver `EXTENDING.md`, paso 5).
- Resolver *qué* proveedor le corresponde a un agente: eso ya lo hace
  `investmentops.ai_providers.selection.resolve_agent_provider`; este
  módulo solo instancia la clase concreta a partir de ese resultado.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from investmentops.ai_providers.anthropic_provider import AnthropicAIProvider
from investmentops.ai_providers.contracts import AIProvider, AIProviderError

#: Mapeo de nombre de proveedor (tal como lo devuelve
#: `resolve_agent_provider`, y tal como se configura en
#: `config.local.toml` bajo `[ai_providers.<nombre>]`) a la clase
#: concreta que implementa `AIProvider` para ese proveedor. Sumar un
#: proveedor nuevo (ver `investmentops/ai_providers/EXTENDING.md`) es
#: añadir una entrada aquí, un cambio puramente aditivo.
_PROVIDER_FACTORIES: Mapping[str, Callable[..., AIProvider]] = {
    "anthropic": AnthropicAIProvider,
}


def build_ai_provider(
    provider_name: str,
    *,
    config: dict[str, Any] | None = None,
) -> AIProvider:
    """Construye la instancia concreta de `AIProvider` para `provider_name`.

    Parameters
    ----------
    provider_name:
        Nombre del proveedor de IA a instanciar (ej. ``"anthropic"``),
        típicamente el `provider` devuelto por
        `investmentops.ai_providers.selection.resolve_agent_provider`.
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), que la implementación
        concreta usará para resolver sus propias credenciales (ej.
        `[ai_providers.anthropic].api_key`). Si no se indica, cada
        implementación concreta decide cómo resolverlo (típicamente
        llamando a `load_config()` internamente).

    Returns
    -------
    AIProvider
        Una instancia lista para invocar mediante `.complete(...)`.

    Raises
    ------
    AIProviderError
        Si `provider_name` no tiene una integración concreta
        implementada todavía (ver `_PROVIDER_FACTORIES` y
        `investmentops/ai_providers/EXTENDING.md`), o si la propia
        construcción de la instancia falla (ej. falta una credencial
        imprescindible; cada implementación concreta señala esto
        levantando `AIProviderError` en su propio constructor).
    """
    factory = _PROVIDER_FACTORIES.get(provider_name)
    if factory is None:
        supported = ", ".join(sorted(_PROVIDER_FACTORIES)) or "ninguno todavía"
        raise AIProviderError(
            "No hay una integración concreta implementada para el "
            f"proveedor de IA '{provider_name}'. Proveedores soportados "
            f"actualmente: {supported}. Ver "
            "investmentops/ai_providers/EXTENDING.md para el "
            "procedimiento para sumar uno nuevo."
        )

    return factory(config=config)
