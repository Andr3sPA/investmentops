# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Interfaz de proveedores de IA → *"Definir el mecanismo de selección de proveedor/modelo por agente vía configuración local."*

Antes de implementar, se verificó que esta tarea no estuviera ya satisfecha por trabajo previo: `AnthropicAIProvider` (ver entrada anterior de este archivo) ya resuelve su propia `api_key`/`base_url`/`model` desde `config.local.toml`, pero esa resolución está acoplada a un único proveedor concreto — no existía ningún mecanismo genérico que, dado un identificador de agente (ej. `"financial_health"`), decidiera **qué proveedor** de `[ai_providers.*]` le corresponde, mirando `[agents]` con fallback a `[ai_providers.default]`, tal como exige `CONFIGURATION.md`. Se confirmó que requería trabajo nuevo y se implementó.

## Qué se implementó

**`investmentops/ai_providers/selection.py`** — nuevo módulo con:

- `AgentProviderSelection` (dataclass inmutable): resultado de la resolución — `agent_id`, `provider` (nombre de la subsección `[ai_providers.<nombre>]` a usar) y `model` (o `None` si no hay uno configurado).
- `AgentProviderSelectionError` (subclase de `RuntimeError`): señala que no pudo resolverse ningún proveedor para un agente dado.
- `resolve_agent_provider(agent_id, config) -> AgentProviderSelection`: función pura que implementa la regla de resolución documentada en `CONFIGURATION.md`:
  1. Si `[agents].<agent_id>` existe y no es literalmente `"default"`, ese valor es el proveedor a usar.
  2. En cualquier otro caso (agente ausente de `[agents]`, o mapeado explícitamente a `"default"` como en los ejemplos comentados de `config.example.toml`), se usa `[ai_providers.default].provider`.
  3. El `model` se resuelve siempre desde `[ai_providers.default].model` (mismo criterio ya usado por `AnthropicAIProvider`, ya que hoy no existe un campo `model` por proveedor en la configuración).
  4. Si no puede resolverse ningún proveedor, se levanta `AgentProviderSelectionError` en vez de adivinar uno.

Esta función **no** instancia ninguna implementación concreta de `AIProvider` (ej. `AnthropicAIProvider`): solo decide qué proveedor/modelo usar. Instanciar la implementación concreta correspondiente queda para quien construya cada agente (tarea posterior, ver "Agente de análisis: salud financiera" y "Agente de análisis: valoración" en `TASKS.md`).

**`investmentops/tests/test_ai_providers_selection.py`** — pruebas cubriendo: agente mapeado explícitamente a un proveedor, agente ausente de `[agents]` con fallback a `[ai_providers.default]`, agente mapeado literalmente a `"default"`, sección `[agents]` ausente por completo, modelo ausente (resuelve a `None`), error cuando no hay ningún proveedor resoluble (ni por agente ni por default), error cuando el agente apunta a `"default"` pero `[ai_providers.default]` no tiene `provider`, que `AgentProviderSelectionError` es un `RuntimeError`, e inmutabilidad de `AgentProviderSelection`.

**`investmentops/ai_providers/__init__.py`** — actualizado para re-exportar `resolve_agent_provider`, `AgentProviderSelection` y `AgentProviderSelectionError`, siguiendo el mismo patrón ya usado para el contrato `AIProvider`/`AIProviderResponse`/`AIProviderError`.

## Decisiones tomadas

- **La resolución de `model` no depende de `provider`.** Como `config.example.toml` solo define `model` en `[ai_providers.default]` (no una por cada subsección de proveedor), este mecanismo replica ese mismo criterio en vez de adelantar una estructura de configuración que aún no existe (ej. un `model` por proveedor). Si en el futuro se necesita, es una extensión explícita y posterior, no algo a anticipar aquí.
- **`"default"` como valor literal en `[agents]` se trata igual que la ausencia del agente en `[agents]`.** Esto es consistente con los ejemplos ya comentados en `config.example.toml` (`financial_health = "default"`) y con la redacción de `CONFIGURATION.md` ("Si un agente no aparece aquí, se asume `[ai_providers.default]`"): un valor explícito `"default"` es la forma de decir lo mismo de forma explícita en el archivo, no un proveedor real llamado `"default"`.
- **No se instancia ningún `AIProvider` concreto desde este módulo.** Mantener la resolución de "qué proveedor/modelo" separada de "cómo construir ese proveedor" evita acoplar `investmentops.ai_providers.selection` a las implementaciones concretas (`AnthropicAIProvider` y las que se agreguen después), preservando la independencia de proveedor exigida por `ARCHITECTURE.md`.
- **No se resolvieron credenciales (`api_key`, `base_url`).** Esta tarea es específicamente sobre selección de proveedor/modelo por agente; la resolución de credenciales ya vive en cada implementación concreta de `AIProvider` (ver `AnthropicAIProvider.__init__`) y no se dupdujo aquí.

## Archivos creados o modificados

Creados:
- `investmentops/ai_providers/selection.py`
- `investmentops/tests/test_ai_providers_selection.py`

Modificados:
- `investmentops/ai_providers/__init__.py` (re-exporta `resolve_agent_provider`, `AgentProviderSelection`, `AgentProviderSelectionError`)
- `TASKS.md` (tarea "Definir el mecanismo de selección de proveedor/modelo por agente vía configuración local" marcada como completada, con referencia inline a esta implementación)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `.python-version`, `pyproject.toml`, `investmentops/ai_providers/contracts.py`, `investmentops/ai_providers/anthropic_provider.py`, y el resto de `investmentops/` (código y tests) no mencionado arriba.

## Problemas encontrados

Ninguno. El contrato y la configuración ya existentes (`AIProvider`, `config.example.toml`, `CONFIGURATION.md`) ya dejaban suficientemente clara la regla de resolución; no hubo ambigüedad que resolver de forma nueva.

## Próxima tarea recomendada

Con el mecanismo de selección definido, queda una única tarea pendiente en `TASKS.md`, sección "Interfaz de proveedores de IA":

1. *"Dejar documentado (sin implementar aún si no es necesario para el MVP) cómo se sumarían las integraciones restantes (Gemini, Claude, OpenAI, Ollama) sin modificar la interfaz ni los agentes."* — es una tarea puramente de documentación (probablemente una sección nueva o ampliada en `ARCHITECTURE.md` o un documento dedicado), no de código.

Nota para la próxima conversación:
- Con esa tarea completa, la sección "Interfaz de proveedores de IA" quedaría cerrada por completo, dejando el proyecto listo para empezar "Normalización y almacenamiento" (la siguiente sección sin marcar en `TASKS.md`).
